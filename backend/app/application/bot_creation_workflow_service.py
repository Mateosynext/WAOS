from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from ..config import settings
from ..db import fetch_all, fetch_one, has_column
from ..platform import diff_configs, record_bot_build, validate_bot_config
from ..repositories import create_audit_log, create_bot, create_or_update_knowledge_items, get_bot
from ..security import ensure_bot_access, ensure_org_access
from ..serializers import serialize_bot_details
from ..utils import from_json, new_id, to_json, utcnow_iso
from ..verticals import build_organization_settings
from ..application.vertical_service import vertical_service
from ..domains.language import upsert_language_config
from ..whatsapp_connection_state import WHATSAPP_STATUS_NUMBER_ENTERED, update_whatsapp_metadata
from .support import require_permission
from .uow import UnitOfWork

BOT_CREATION_PHASE_BOT_CREATED = "bot_created"
BOT_CREATION_PHASE_VERTICAL_SYNCED = "vertical_synced"
BOT_CREATION_PHASE_SUBVERTICAL_PACK_APPLIED = "subvertical_pack_applied"
BOT_CREATION_PHASE_WHATSAPP_PENDING = "whatsapp_pending"
BOT_CREATION_PHASE_READY = "ready"
BOT_CREATION_PHASE_FAILED_RECOVERABLE = "failed_recoverable"

BOT_CREATION_WORKFLOW_PHASES = (
    BOT_CREATION_PHASE_BOT_CREATED,
    BOT_CREATION_PHASE_VERTICAL_SYNCED,
    BOT_CREATION_PHASE_SUBVERTICAL_PACK_APPLIED,
    BOT_CREATION_PHASE_WHATSAPP_PENDING,
    BOT_CREATION_PHASE_READY,
    BOT_CREATION_PHASE_FAILED_RECOVERABLE,
)
BOT_CREATION_TERMINAL_PHASES = (BOT_CREATION_PHASE_READY,)
BOT_CREATION_RECOVERABLE_PHASES = (
    BOT_CREATION_PHASE_VERTICAL_SYNCED,
    BOT_CREATION_PHASE_SUBVERTICAL_PACK_APPLIED,
    BOT_CREATION_PHASE_WHATSAPP_PENDING,
    BOT_CREATION_PHASE_READY,
)
BOT_CREATION_LEASE_SECONDS = 300
BOT_CREATION_MAX_ATTEMPTS = 8

_NEXT_PHASE = {
    BOT_CREATION_PHASE_BOT_CREATED: BOT_CREATION_PHASE_VERTICAL_SYNCED,
    BOT_CREATION_PHASE_VERTICAL_SYNCED: BOT_CREATION_PHASE_SUBVERTICAL_PACK_APPLIED,
    BOT_CREATION_PHASE_SUBVERTICAL_PACK_APPLIED: BOT_CREATION_PHASE_WHATSAPP_PENDING,
    BOT_CREATION_PHASE_WHATSAPP_PENDING: BOT_CREATION_PHASE_READY,
}


def _short_error(exc: BaseException) -> str:
    text = str(exc) or exc.__class__.__name__
    return text[:1200]


def _future_iso(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class BotCreationWorkflowService:
    """Durable, retryable workflow for bot creation side effects.

    A bot row may be created before vertical sync, subvertical pack or channel setup
    complete.  This service persists that progress explicitly so retries can resume
    from the failed phase instead of leaving an apparently successful but incomplete
    bot behind.
    """

    def _ensure_column(self, conn, table: str, column: str, definition: str) -> None:
        if has_column(conn, table, column):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _ensure_schema(self, conn) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS bot_creation_workflows (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                bot_id TEXT,
                client_request_id TEXT NOT NULL,
                status TEXT NOT NULL,
                failed_phase TEXT,
                vertical TEXT NOT NULL,
                subvertical TEXT,
                publish_now INTEGER NOT NULL DEFAULT 1,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 8,
                phase_attempts_json TEXT NOT NULL DEFAULT '{}',
                last_error TEXT,
                payload_json TEXT NOT NULL DEFAULT '{}',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                locked_by TEXT,
                locked_until TEXT,
                last_phase_started_at TEXT,
                version INTEGER NOT NULL DEFAULT 0,
                created_by_user_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (bot_id) REFERENCES bots(id)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS ux_bot_creation_workflows_org_request
              ON bot_creation_workflows(organization_id, client_request_id);
            CREATE INDEX IF NOT EXISTS idx_bot_creation_workflows_status
              ON bot_creation_workflows(status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_bot_creation_workflows_bot
              ON bot_creation_workflows(bot_id, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_bot_creation_workflows_lease
              ON bot_creation_workflows(locked_until, status);
            """
        )
        for column, definition in [
            ("client_request_id", "TEXT"),
        ]:
            self._ensure_column(conn, "bots", column, definition)
        conn.executescript(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_bots_org_client_request
              ON bots(organization_id, client_request_id) WHERE client_request_id IS NOT NULL;
            """
        )
        for column, definition in [
            ("max_attempts", "INTEGER NOT NULL DEFAULT 8"),
            ("phase_attempts_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("locked_by", "TEXT"),
            ("locked_until", "TEXT"),
            ("last_phase_started_at", "TEXT"),
            ("version", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            self._ensure_column(conn, "bot_creation_workflows", column, definition)

    def _client_request_id(self, payload_data: dict[str, Any]) -> str:
        explicit = str(payload_data.get("client_request_id") or "").strip()
        if explicit:
            return explicit[:160]
        seed = {
            "organization_id": payload_data.get("organization_id"),
            "business_name": payload_data.get("business_name"),
            "vertical": payload_data.get("vertical"),
            "subvertical": payload_data.get("subvertical"),
            "bot_name": payload_data.get("bot_name"),
            "primary_objective": payload_data.get("primary_objective"),
            "tone": payload_data.get("tone"),
            "language": payload_data.get("language"),
            "timezone": payload_data.get("timezone"),
            "services": payload_data.get("services") or [],
            "hours": payload_data.get("hours") or "",
            "faqs": payload_data.get("faqs") or [],
            "whatsapp_number": payload_data.get("whatsapp_number") or "",
            "publish_now": bool(payload_data.get("publish_now", True)),
        }
        encoded = json.dumps(seed, sort_keys=True, ensure_ascii=False, default=str)
        return "botcreatewf_" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:48]

    def _get_workflow(self, conn, workflow_id: str) -> dict | None:
        return fetch_one(conn, "SELECT * FROM bot_creation_workflows WHERE id = ?", (workflow_id,))

    def _get_workflow_by_request(self, conn, *, organization_id: str, client_request_id: str) -> dict | None:
        return fetch_one(
            conn,
            """
            SELECT * FROM bot_creation_workflows
            WHERE organization_id = ? AND client_request_id = ?
            ORDER BY updated_at DESC LIMIT 1
            """,
            (organization_id, client_request_id),
        )

    def _get_bot_by_client_request_id(self, conn, *, organization_id: str, client_request_id: str) -> dict | None:
        if not client_request_id:
            return None
        try:
            return fetch_one(
                conn,
                """
                SELECT * FROM bots
                WHERE organization_id = ? AND client_request_id = ? AND deleted_at IS NULL
                ORDER BY created_at DESC LIMIT 1
                """,
                (organization_id, client_request_id),
            )
        except Exception:
            return None

    def _insert_workflow(self, conn, *, bot: dict, payload_data: dict[str, Any], client_request_id: str, user: dict) -> dict:
        now = utcnow_iso()
        workflow_id = new_id("bcwf")
        conn.execute(
            """
            INSERT INTO bot_creation_workflows
            (id, organization_id, bot_id, client_request_id, status, failed_phase, vertical, subvertical,
             publish_now, attempts, max_attempts, phase_attempts_json, last_error, payload_json, metadata_json,
             locked_by, locked_until, last_phase_started_at, version, created_by_user_id, created_at, updated_at, completed_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, 0, ?, '{}', NULL, ?, '{}', NULL, NULL, NULL, 0, ?, ?, ?, NULL)
            """,
            (
                workflow_id,
                payload_data["organization_id"],
                bot["id"],
                client_request_id,
                BOT_CREATION_PHASE_BOT_CREATED,
                payload_data["vertical"],
                payload_data.get("subvertical") or None,
                1 if payload_data.get("publish_now", True) else 0,
                BOT_CREATION_MAX_ATTEMPTS,
                to_json(payload_data),
                user.get("id"),
                now,
                now,
            ),
        )
        create_audit_log(
            conn,
            organization_id=payload_data["organization_id"],
            actor_user_id=user.get("id"),
            actor_type="user",
            entity_type="bot_creation_workflow",
            entity_id=workflow_id,
            action="bot_creation_workflow.bot_created",
            metadata={"bot_id": bot["id"], "client_request_id": client_request_id},
        )
        return self._get_workflow(conn, workflow_id) or {}

    def _phase_attempts(self, workflow: dict, failed_phase: str | None, *, increment: bool) -> dict[str, int]:
        attempts = from_json(workflow.get("phase_attempts_json"), {})
        if not isinstance(attempts, dict):
            attempts = {}
        normalized = {str(k): int(v or 0) for k, v in attempts.items() if str(k) in BOT_CREATION_RECOVERABLE_PHASES}
        if increment and failed_phase:
            normalized[failed_phase] = normalized.get(failed_phase, 0) + 1
        return normalized

    def _assert_valid_transition(self, workflow: dict, next_status: str, failed_phase: str | None = None) -> None:
        current = workflow.get("status")
        if current not in BOT_CREATION_WORKFLOW_PHASES:
            raise HTTPException(status_code=500, detail={"code": "invalid_bot_creation_workflow_status", "status": current})
        if next_status not in BOT_CREATION_WORKFLOW_PHASES:
            raise HTTPException(status_code=500, detail={"code": "invalid_bot_creation_workflow_next_status", "status": next_status})
        if current == next_status:
            return
        if next_status == BOT_CREATION_PHASE_FAILED_RECOVERABLE:
            if failed_phase not in BOT_CREATION_RECOVERABLE_PHASES:
                raise HTTPException(status_code=500, detail={"code": "invalid_bot_creation_failed_phase", "phase": failed_phase})
            return
        if current == BOT_CREATION_PHASE_FAILED_RECOVERABLE:
            expected = workflow.get("failed_phase") or BOT_CREATION_PHASE_VERTICAL_SYNCED
            if next_status == expected:
                return
            raise HTTPException(
                status_code=409,
                detail={"code": "bot_creation_retry_phase_mismatch", "expected_phase": expected, "next_status": next_status},
            )
        if _NEXT_PHASE.get(current) == next_status:
            return
        raise HTTPException(status_code=409, detail={"code": "invalid_bot_creation_workflow_transition", "from": current, "to": next_status})

    def _assert_retry_budget(self, workflow: dict) -> None:
        if workflow.get("status") != BOT_CREATION_PHASE_FAILED_RECOVERABLE:
            return
        attempts = int(workflow.get("attempts") or 0)
        max_attempts = int(workflow.get("max_attempts") or BOT_CREATION_MAX_ATTEMPTS)
        if attempts >= max_attempts:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "bot_creation_retry_exhausted",
                    "workflow_id": workflow.get("id"),
                    "attempts": attempts,
                    "max_attempts": max_attempts,
                    "failed_phase": workflow.get("failed_phase"),
                },
            )

    def _lease_owner(self, user: dict) -> str:
        return str(user.get("id") or user.get("email") or "system")[:160]

    def _acquire_workflow_lease(self, conn, workflow: dict, *, user: dict) -> dict:
        if workflow.get("status") in BOT_CREATION_TERMINAL_PHASES:
            return workflow
        self._assert_retry_budget(workflow)
        owner = self._lease_owner(user)
        now = utcnow_iso()
        locked_until = _future_iso(BOT_CREATION_LEASE_SECONDS)
        cursor = conn.execute(
            """
            UPDATE bot_creation_workflows
            SET locked_by = ?, locked_until = ?, last_phase_started_at = ?, updated_at = ?, version = COALESCE(version, 0) + 1
            WHERE id = ?
              AND status <> ?
              AND (locked_until IS NULL OR locked_until <= ? OR locked_by = ?)
            """,
            (owner, locked_until, now, now, workflow["id"], BOT_CREATION_PHASE_READY, now, owner),
        )
        if getattr(cursor, "rowcount", 0) == 0:
            latest = self._get_workflow(conn, workflow["id"]) or workflow
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "bot_creation_workflow_locked",
                    "workflow_id": workflow.get("id"),
                    "locked_until": latest.get("locked_until"),
                    "status": latest.get("status"),
                },
            )
        return self._get_workflow(conn, workflow["id"]) or workflow

    def _release_workflow_lease(self, conn, *, workflow_id: str, user: dict) -> None:
        owner = self._lease_owner(user)
        conn.execute(
            """
            UPDATE bot_creation_workflows
            SET locked_by = NULL, locked_until = NULL, updated_at = ?
            WHERE id = ? AND locked_by = ?
            """,
            (utcnow_iso(), workflow_id, owner),
        )

    def _update_workflow(
        self,
        conn,
        workflow: dict,
        *,
        status: str,
        failed_phase: str | None = None,
        last_error: str | None = None,
        metadata: dict[str, Any] | None = None,
        increment_attempts: bool = False,
    ) -> dict:
        self._assert_valid_transition(workflow, status, failed_phase)
        current_metadata = from_json(workflow.get("metadata_json"), {})
        if metadata:
            current_metadata = {**current_metadata, **metadata}
        phase_attempts = self._phase_attempts(workflow, failed_phase, increment=increment_attempts)
        completed_at = utcnow_iso() if status == BOT_CREATION_PHASE_READY else workflow.get("completed_at")
        conn.execute(
            """
            UPDATE bot_creation_workflows
            SET status = ?, failed_phase = ?,
                attempts = CASE WHEN ? THEN COALESCE(attempts, 0) + 1 ELSE COALESCE(attempts, 0) END,
                phase_attempts_json = ?, last_error = ?, metadata_json = ?, updated_at = ?, completed_at = ?,
                version = COALESCE(version, 0) + 1
            WHERE id = ?
            """,
            (
                status,
                failed_phase,
                1 if increment_attempts else 0,
                to_json(phase_attempts),
                last_error,
                to_json(current_metadata),
                utcnow_iso(),
                completed_at,
                workflow["id"],
            ),
        )
        action_status = status if status != BOT_CREATION_PHASE_FAILED_RECOVERABLE else f"failed.{failed_phase or 'unknown'}"
        create_audit_log(
            conn,
            organization_id=workflow["organization_id"],
            actor_user_id=workflow.get("created_by_user_id"),
            actor_type="user",
            entity_type="bot_creation_workflow",
            entity_id=workflow["id"],
            action=f"bot_creation_workflow.{action_status}",
            metadata={"bot_id": workflow.get("bot_id"), "last_error": last_error, "phase_attempts": phase_attempts, **(metadata or {})},
            severity="warning" if status == BOT_CREATION_PHASE_FAILED_RECOVERABLE else "info",
        )
        return self._get_workflow(conn, workflow["id"]) or workflow

    def _assert_created_bot_contract(self, conn, *, bot: dict | None, organization_id: str, publish_now: bool) -> dict:
        if not bot or not bot.get("id"):
            raise HTTPException(status_code=500, detail={"code": "bot_create_failed", "message": "Bot creation did not return a persisted bot"})
        if bot.get("organization_id") != organization_id:
            raise HTTPException(status_code=500, detail={"code": "bot_scope_mismatch", "message": "Created bot organization mismatch"})
        config = from_json(bot.get("config_draft_json"), {})
        if not isinstance(config, dict) or not config:
            raise HTTPException(status_code=500, detail={"code": "bot_config_invalid", "message": "Created bot has invalid config draft"})
        if publish_now:
            version_id = bot.get("published_version_id")
            version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ? AND bot_id = ?", (version_id, bot["id"])) if version_id else None
            if not version:
                raise HTTPException(status_code=500, detail={"code": "bot_initial_publish_missing", "message": "Initial published version was not created"})
        return config

    def _sync_organization_vertical(self, conn, *, workflow: dict, payload_data: dict[str, Any], user: dict) -> None:
        org = fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (workflow["organization_id"],))
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        current_settings = from_json(org.get("settings_json"), {})
        base_settings = build_organization_settings(payload_data["vertical"], organization_name=org.get("name") or payload_data["business_name"])
        merged_settings = {**base_settings, **current_settings}
        subvertical = payload_data.get("subvertical") or current_settings.get("subvertical") or current_settings.get("active_subvertical")
        if subvertical:
            merged_settings["subvertical"] = subvertical
            merged_settings["active_subvertical"] = subvertical
        conn.execute(
            """
            UPDATE organizations
            SET vertical = ?, settings_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (payload_data["vertical"], to_json(merged_settings), utcnow_iso(), workflow["organization_id"]),
        )
        create_audit_log(
            conn,
            organization_id=workflow["organization_id"],
            actor_user_id=user.get("id"),
            actor_type="user",
            entity_type="organization",
            entity_id=workflow["organization_id"],
            action="organization.vertical_synced_from_bot_creation",
            metadata={"bot_id": workflow.get("bot_id"), "vertical": payload_data["vertical"], "subvertical": subvertical},
        )

    def _run_vertical_synced_phase(self, conn, *, workflow: dict, payload_data: dict[str, Any], user: dict) -> dict[str, Any]:
        bot = get_bot(conn, workflow["bot_id"])
        config = self._assert_created_bot_contract(conn, bot=bot, organization_id=workflow["organization_id"], publish_now=bool(payload_data.get("publish_now", True)))
        self._sync_organization_vertical(conn, workflow=workflow, payload_data=payload_data, user=user)
        create_or_update_knowledge_items(conn, organization_id=workflow["organization_id"], bot_id=workflow["bot_id"], config=config)
        vertical_service.apply(
            conn,
            user=user,
            organization_id=workflow["organization_id"],
            bot_id=workflow["bot_id"],
            vertical=payload_data["vertical"],
            business_name=payload_data["business_name"],
            bot_name=payload_data["bot_name"],
            tone=payload_data.get("tone") or "amable",
            language=payload_data.get("language") or settings.default_language,
            timezone=payload_data.get("timezone") or settings.default_timezone,
            primary_objective=payload_data.get("primary_objective") or "agendar",
            services=payload_data.get("services") or [],
            faqs=payload_data.get("faqs") or [],
            hours=payload_data.get("hours") or "",
            whatsapp_number=payload_data.get("whatsapp_number") or "",
        )
        upsert_language_config(
            conn,
            organization_id=workflow["organization_id"],
            bot_id=workflow["bot_id"],
            default_language=payload_data.get("language") or settings.default_language,
            supported_languages=[payload_data.get("language") or settings.default_language, "en" if (payload_data.get("language") or settings.default_language) != "en" else "es"],
            handoff_respect_language=True,
        )
        return {"vertical": payload_data["vertical"], "subvertical": payload_data.get("subvertical")}

    def _persist_subvertical_fallback(self, conn, *, workflow: dict, payload_data: dict[str, Any], user: dict) -> dict[str, Any]:
        subvertical = payload_data.get("subvertical")
        if not subvertical:
            return {"subvertical": None, "skipped": True}
        bot = get_bot(conn, workflow["bot_id"])
        config = from_json((bot or {}).get("config_draft_json"), {})
        config["selected_subvertical"] = subvertical
        config["subvertical"] = subvertical
        identity = config.setdefault("identity", {})
        if isinstance(identity, dict):
            identity["subvertical"] = subvertical
            identity["vertical"] = payload_data.get("vertical")
        conn.execute(
            "UPDATE bots SET config_draft_json = ?, updated_at = ? WHERE id = ?",
            (to_json(config), utcnow_iso(), workflow["bot_id"]),
        )
        create_audit_log(
            conn,
            organization_id=workflow["organization_id"],
            actor_user_id=user.get("id"),
            actor_type="user",
            entity_type="bot",
            entity_id=workflow["bot_id"],
            action="bot.subvertical_pack_fallback_applied",
            metadata={"subvertical": subvertical, "vertical": payload_data.get("vertical")},
        )
        return {"subvertical": subvertical, "fallback": True}

    def _run_subvertical_phase(self, conn, *, workflow: dict, payload_data: dict[str, Any], user: dict) -> dict[str, Any]:
        subvertical = payload_data.get("subvertical")
        if not subvertical:
            return {"subvertical": None, "skipped": True}
        try:
            from ..vertical_10x import apply_subvertical_pack, get_vertical_profile  # type: ignore
        except ImportError as exc:
            if "vertical_10x" not in str(exc):
                raise
            return self._persist_subvertical_fallback(conn, workflow=workflow, payload_data=payload_data, user=user)
        profile = get_vertical_profile(payload_data["vertical"])
        result = apply_subvertical_pack(
            conn,
            profile=profile,
            organization_id=workflow["organization_id"],
            bot_id=workflow["bot_id"],
            subvertical=subvertical,
            actor_user=user,
        )
        return {"subvertical": subvertical, "pack_result": result}

    def _run_whatsapp_pending_phase(self, conn, *, workflow: dict, payload_data: dict[str, Any]) -> dict[str, Any]:
        whatsapp_number = str(payload_data.get("whatsapp_number") or "").strip()
        if not whatsapp_number:
            return {"whatsapp_required": False}
        existing = fetch_one(
            conn,
            """
            SELECT * FROM whatsapp_numbers
            WHERE organization_id = ? AND bot_id = ? AND phone_number = ?
            ORDER BY updated_at DESC LIMIT 1
            """,
            (workflow["organization_id"], workflow["bot_id"], whatsapp_number),
        )
        if existing:
            return {"whatsapp_required": True, "connection_status": existing.get("connection_status")}
        connection_status, metadata_json = update_whatsapp_metadata(
            {},
            phone_number=whatsapp_number,
            phone_number_id=None,
            waba_id=None,
            access_token_present=False,
            webhook_verified=False,
            source="bot_creation_workflow",
        )
        conn.execute(
            """
            INSERT INTO whatsapp_numbers
            (id, organization_id, bot_id, provider, phone_number, phone_number_id, waba_id, connection_status,
             webhook_verify_token, access_token_masked, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, 'meta_cloud_api', ?, NULL, NULL, ?, NULL, NULL, ?, ?, ?)
            """,
            (
                new_id("wan"),
                workflow["organization_id"],
                workflow["bot_id"],
                whatsapp_number,
                connection_status or WHATSAPP_STATUS_NUMBER_ENTERED,
                metadata_json,
                utcnow_iso(),
                utcnow_iso(),
            ),
        )
        return {"whatsapp_required": True, "connection_status": connection_status or WHATSAPP_STATUS_NUMBER_ENTERED}

    def _run_ready_phase(self, conn, *, workflow: dict, payload_data: dict[str, Any]) -> dict[str, Any]:
        bot = get_bot(conn, workflow["bot_id"])
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        config = from_json(bot.get("config_draft_json"), {})
        version_id = bot.get("published_version_id")
        build_recorded = False
        if payload_data.get("publish_now", True) and version_id:
            version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ? AND bot_id = ?", (version_id, workflow["bot_id"]))
            if not version:
                raise HTTPException(status_code=500, detail={"code": "bot_initial_publish_missing", "message": "Initial published version was not created"})
            existing_build = fetch_one(conn, "SELECT * FROM bot_builds WHERE bot_id = ? AND version_id = ? ORDER BY created_at DESC LIMIT 1", (workflow["bot_id"], version_id))
            if not existing_build:
                record_bot_build(
                    conn,
                    organization_id=workflow["organization_id"],
                    bot_id=workflow["bot_id"],
                    version_id=version_id,
                    validation=validate_bot_config(config),
                    diff_summary=diff_configs({}, config),
                    config=config,
                )
                build_recorded = True
        return {"build_recorded": build_recorded, "published_version_id": version_id}

    def _payload_data(self, workflow: dict) -> dict[str, Any]:
        data = from_json(workflow.get("payload_json"), {})
        if not isinstance(data, dict):
            data = {}
        data.setdefault("organization_id", workflow.get("organization_id"))
        data.setdefault("vertical", workflow.get("vertical"))
        data.setdefault("subvertical", workflow.get("subvertical"))
        data.setdefault("publish_now", bool(workflow.get("publish_now", 1)))
        return data

    def _phase_to_run(self, workflow: dict) -> str | None:
        status = workflow.get("status")
        if status not in BOT_CREATION_WORKFLOW_PHASES:
            raise HTTPException(status_code=500, detail={"code": "invalid_bot_creation_workflow_status", "status": status})
        if status == BOT_CREATION_PHASE_READY:
            return None
        if status == BOT_CREATION_PHASE_FAILED_RECOVERABLE:
            failed_phase = workflow.get("failed_phase") or BOT_CREATION_PHASE_VERTICAL_SYNCED
            if failed_phase not in BOT_CREATION_RECOVERABLE_PHASES:
                raise HTTPException(status_code=500, detail={"code": "invalid_bot_creation_failed_phase", "phase": failed_phase})
            return failed_phase
        next_phase = _NEXT_PHASE.get(status)
        if not next_phase:
            raise HTTPException(status_code=500, detail={"code": "bot_creation_workflow_has_no_next_phase", "status": status})
        return next_phase

    def _run_phase(self, conn, *, phase: str, workflow: dict, payload_data: dict[str, Any], user: dict) -> dict[str, Any]:
        if phase == BOT_CREATION_PHASE_VERTICAL_SYNCED:
            return self._run_vertical_synced_phase(conn, workflow=workflow, payload_data=payload_data, user=user)
        if phase == BOT_CREATION_PHASE_SUBVERTICAL_PACK_APPLIED:
            return self._run_subvertical_phase(conn, workflow=workflow, payload_data=payload_data, user=user)
        if phase == BOT_CREATION_PHASE_WHATSAPP_PENDING:
            return self._run_whatsapp_pending_phase(conn, workflow=workflow, payload_data=payload_data)
        if phase == BOT_CREATION_PHASE_READY:
            return self._run_ready_phase(conn, workflow=workflow, payload_data=payload_data)
        raise HTTPException(status_code=500, detail={"code": "unknown_bot_creation_phase", "phase": phase})

    def _advance(self, conn, *, workflow: dict, user: dict) -> dict:
        if workflow.get("status") in BOT_CREATION_TERMINAL_PHASES:
            return workflow
        workflow = self._acquire_workflow_lease(conn, workflow, user=user)
        result = workflow
        try:
            while True:
                phase = self._phase_to_run(result)
                if not phase:
                    return result
                payload_data = self._payload_data(result)
                try:
                    metadata = self._run_phase(conn, phase=phase, workflow=result, payload_data=payload_data, user=user)
                except Exception as exc:
                    result = self._update_workflow(
                        conn,
                        result,
                        status=BOT_CREATION_PHASE_FAILED_RECOVERABLE,
                        failed_phase=phase,
                        last_error=_short_error(exc),
                        metadata={"recoverable": True},
                        increment_attempts=True,
                    )
                    return result
                result = self._update_workflow(conn, result, status=phase, failed_phase=None, last_error=None, metadata=metadata)
        finally:
            self._release_workflow_lease(conn, workflow_id=workflow["id"], user=user)

    def _serialize_result(self, conn, workflow: dict) -> dict:
        bot = get_bot(conn, workflow.get("bot_id")) if workflow.get("bot_id") else None
        serialized_bot = serialize_bot_details(conn, bot) if bot else None
        return {
            "id": (serialized_bot or {}).get("id") or workflow.get("bot_id"),
            "bot_id": workflow.get("bot_id"),
            "organization_id": workflow.get("organization_id"),
            "workflow_id": workflow.get("id"),
            "workflow_status": workflow.get("status"),
            "failed_phase": workflow.get("failed_phase"),
            "recoverable": workflow.get("status") == BOT_CREATION_PHASE_FAILED_RECOVERABLE,
            "attempts": int(workflow.get("attempts") or 0),
            "max_attempts": int(workflow.get("max_attempts") or BOT_CREATION_MAX_ATTEMPTS),
            "locked_until": workflow.get("locked_until"),
            "publish_now": bool(workflow.get("publish_now", 1)),
            "bot": serialized_bot,
            "workflow": workflow,
        }

    def create(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        conn = uow.conn
        payload_data = payload.model_dump()
        ensure_org_access(user, payload_data["organization_id"])
        require_permission(user, payload_data["organization_id"], "bot.manage")
        self._ensure_schema(conn)
        client_request_id = self._client_request_id(payload_data)
        workflow = self._get_workflow_by_request(conn, organization_id=payload_data["organization_id"], client_request_id=client_request_id)
        if not workflow:
            bot = self._get_bot_by_client_request_id(conn, organization_id=payload_data["organization_id"], client_request_id=client_request_id)
            if not bot:
                try:
                    bot = create_bot(
                        conn,
                        organization_id=payload_data["organization_id"],
                    business_name=payload_data["business_name"],
                    vertical=payload_data["vertical"],
                    bot_name=payload_data["bot_name"],
                    primary_objective=payload_data.get("primary_objective") or "agendar",
                    tone=payload_data.get("tone") or "amable",
                    language=payload_data.get("language") or settings.default_language,
                    timezone=payload_data.get("timezone") or settings.default_timezone,
                    services=payload_data.get("services") or [],
                    hours=payload_data.get("hours") or "",
                    faqs=payload_data.get("faqs") or [],
                    whatsapp_number=payload_data.get("whatsapp_number") or "",
                    publish_now=bool(payload_data.get("publish_now", True)),
                    created_by=user,
                        client_request_id=client_request_id,
                    )
                except Exception:
                    bot = self._get_bot_by_client_request_id(conn, organization_id=payload_data["organization_id"], client_request_id=client_request_id)
                    if not bot:
                        raise
            workflow = self._insert_workflow(conn, bot=bot, payload_data=payload_data, client_request_id=client_request_id, user=user)
        if workflow.get("bot_id"):
            bot = get_bot(conn, workflow["bot_id"])
            if bot:
                ensure_bot_access(user, bot)
        workflow = self._advance(conn, workflow=workflow, user=user)
        return self._serialize_result(conn, workflow)

    def retry(self, uow: UnitOfWork, *, user: dict, workflow_id: str) -> dict:
        conn = uow.conn
        self._ensure_schema(conn)
        workflow = self._get_workflow(conn, workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Bot creation workflow not found")
        ensure_org_access(user, workflow["organization_id"])
        require_permission(user, workflow["organization_id"], "bot.manage")
        if workflow.get("bot_id"):
            bot = get_bot(conn, workflow["bot_id"])
            if bot:
                ensure_bot_access(user, bot)
        workflow = self._advance(conn, workflow=workflow, user=user)
        return self._serialize_result(conn, workflow)

    def get(self, uow: UnitOfWork, *, user: dict, workflow_id: str) -> dict:
        conn = uow.conn
        self._ensure_schema(conn)
        workflow = self._get_workflow(conn, workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Bot creation workflow not found")
        ensure_org_access(user, workflow["organization_id"])
        return self._serialize_result(conn, workflow)
