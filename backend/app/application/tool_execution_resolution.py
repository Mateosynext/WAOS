from __future__ import annotations

import hashlib
import hmac
from typing import Any

from fastapi import HTTPException

from ..agent_policy_runtime import evaluate_specialist_policy, get_policy_profile_for_specialist, persist_agent_policy_evaluation
from ..config import settings
from ..db import execute, fetch_all, fetch_one
from ..job_idempotency import begin_job_execution, get_job_execution, mark_job_completed, mark_job_failed
from ..multi_agent_runtime import build_shared_memory_context
from ..repositories import create_audit_log, get_bot
from ..security import ensure_bot_access, ensure_org_access
from ..utils import canonical_hash, from_json, hash_value, new_id, sign_payload, to_json, utcnow, utcnow_iso, verify_signed_payload
from .outcomes_service import outcomes_service
from .tool_execution_adapters import (
    ActionPolicy,
    BaseAdapter,
    GoogleCalendarAdapter,
    StripePaymentsAdapter,
    WaosCalendarAdapter,
    WaosCrmAdapter,
)
from .tool_execution_policy import resolve_action_policy
from .tool_execution_presenters import serialize_tool_execution_run


def _table_exists(conn, table: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "sqlite":
        row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
        return bool(row)
    row = conn.execute(
        """
        SELECT 1 AS present
        FROM information_schema.tables
        WHERE table_schema = current_schema() AND table_name = ?
        LIMIT 1
        """,
        (table,),
    ).fetchone()
    return bool(row)

class ToolExecutionResolutionMixin:
    def _resolve_preview_run(self, conn, *, payload, user: dict, normalized: dict[str, Any], policy: ActionPolicy) -> dict[str, Any] | None:
        if not policy.requires_confirmation:
            return None
        if not payload.confirm:
            raise HTTPException(status_code=409, detail="tool_execution_requires_explicit_confirm")
        if not payload.preview_execution_id:
            raise HTTPException(status_code=409, detail="tool_execution_requires_preview_execution_id")
        if not payload.confirmation_token:
            raise HTTPException(status_code=409, detail="tool_execution_requires_confirmation_token")

        preview = fetch_one(conn, "SELECT * FROM tool_execution_runs WHERE id = ?", (payload.preview_execution_id,))
        if not preview:
            raise HTTPException(status_code=404, detail="tool_execution_preview_not_found")
        ensure_org_access(user, preview["organization_id"])
        if preview["organization_id"] != payload.organization_id or preview["action"] != payload.action:
            raise HTTPException(status_code=409, detail="tool_execution_preview_scope_mismatch")
        if preview.get("execution_mode") != "preview" or preview.get("status") != "preview_ready":
            raise HTTPException(status_code=409, detail="tool_execution_preview_not_ready")
        if not preview.get("requires_confirmation"):
            raise HTTPException(status_code=409, detail="tool_execution_preview_confirmation_not_required")

        expected = preview.get("confirmation_token_hash")
        provided_hash = self._hash_confirmation_token(payload.confirmation_token)
        if not expected or not hmac.compare_digest(provided_hash, expected):
            raise HTTPException(status_code=409, detail="tool_execution_confirmation_token_invalid")
        self._verify_confirmation_token(payload.confirmation_token, preview=preview, normalized_payload=normalized)
        if from_json(preview.get("normalized_payload_json"), {}) != normalized:
            raise HTTPException(status_code=409, detail="tool_execution_preview_payload_mismatch")
        now = utcnow_iso()
        execute(conn, "UPDATE tool_execution_runs SET confirmed_by = ?, confirmed_at = ?, updated_at = ? WHERE id = ?", (user["id"], now, now, preview["id"]))
        return preview

    def _ensure_preview_idempotency_scope(self, conn, *, preview_run_id: str | None, idempotency_key: str) -> None:
        if not preview_run_id:
            return
        prior = fetch_one(
            conn,
            """
            SELECT id, idempotency_key, status
            FROM tool_execution_runs
            WHERE preview_run_id = ?
              AND execution_mode = 'execute'
              AND status IN ('running', 'completed')
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (preview_run_id,),
        )
        if prior and prior.get("idempotency_key") != idempotency_key:
            raise HTTPException(status_code=409, detail="tool_execution_preview_already_consumed")

    def _idempotency_target_id(self, action: str, normalized_payload: dict[str, Any]) -> str:
        if action == "reschedule":
            value = normalized_payload.get("appointment_id")
        elif action == "send_receipt":
            value = normalized_payload.get("payment_id")
        elif action == "create_payment_link":
            value = normalized_payload.get("appointment_id") or normalized_payload.get("contact_id") or normalized_payload.get("conversation_id")
        elif action == "book_appointment":
            value = normalized_payload.get("conversation_id") or normalized_payload.get("contact_id") or normalized_payload.get("bot_id")
        elif action == "update_contact_stage":
            value = normalized_payload.get("contact_id")
        else:
            value = normalized_payload.get("target_id")
        target_id = str(value or "").strip()
        if not target_id:
            raise HTTPException(status_code=400, detail="tool_execution_requires_target_id")
        return target_id

    def _client_request_id(self, payload) -> str:
        value = getattr(payload, "client_request_id", None) or payload.idempotency_key or (payload.metadata or {}).get("client_request_id")
        client_request_id = str(value or "").strip()
        if not client_request_id:
            raise HTTPException(status_code=400, detail="tool_execution_requires_client_request_id")
        if len(client_request_id) < 8 or len(client_request_id) > 180:
            raise HTTPException(status_code=400, detail="tool_execution_invalid_client_request_id")
        return client_request_id

    def _resolve_idempotency_key(self, action: str, organization_id: str, normalized_payload: dict[str, Any], payload) -> tuple[str, str, str]:
        target_id = self._idempotency_target_id(action, normalized_payload)
        client_request_id = self._client_request_id(payload)
        key_material = {
            "organization_id": organization_id,
            "action_type": action,
            "target_id": target_id,
            "client_request_id": client_request_id,
        }
        return f"tool-exec:v2:{canonical_hash(key_material)}", target_id, client_request_id

    def _normalize_payload(self, conn, *, payload) -> dict[str, Any]:
        raw = dict(payload.payload or {})
        if payload.bot_id and "bot_id" not in raw:
            raw["bot_id"] = payload.bot_id
        raw.setdefault("organization_id", payload.organization_id)
        if payload.action == "book_appointment":
            if not raw.get("bot_id"):
                raise HTTPException(status_code=400, detail="book_appointment_requires_bot_id")
            if not raw.get("scheduled_for"):
                raise HTTPException(status_code=400, detail="book_appointment_requires_scheduled_for")
            if not raw.get("conversation_id") and not raw.get("contact_id"):
                raise HTTPException(status_code=400, detail="book_appointment_requires_contact_or_conversation")
            return {
                "organization_id": payload.organization_id,
                "bot_id": raw["bot_id"],
                "conversation_id": raw.get("conversation_id"),
                "contact_id": raw.get("contact_id"),
                "scheduled_for": raw["scheduled_for"],
                "status": raw.get("status") or "scheduled",
                "duration_minutes": int(raw.get("duration_minutes") or 30),
                "timezone": raw.get("timezone") or "America/Mexico_City",
                "notes": raw.get("notes") or "",
            }
        if payload.action == "reschedule":
            appointment = fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", (raw.get("appointment_id"),)) if raw.get("appointment_id") else None
            if not appointment:
                raise HTTPException(status_code=404, detail="appointment_not_found")
            if appointment["organization_id"] != payload.organization_id:
                raise HTTPException(status_code=403, detail="appointment_scope_mismatch")
            if not raw.get("scheduled_for"):
                raise HTTPException(status_code=400, detail="reschedule_requires_scheduled_for")
            return {
                "organization_id": payload.organization_id,
                "bot_id": appointment.get("bot_id"),
                "appointment_id": raw["appointment_id"],
                "scheduled_for": raw["scheduled_for"],
                "conversation_id": appointment.get("conversation_id"),
                "contact_id": appointment.get("contact_id"),
            }
        if payload.action == "create_payment_link":
            required = ["bot_id", "conversation_id", "contact_id", "title"]
            missing = [item for item in required if not raw.get(item)]
            if missing:
                raise HTTPException(status_code=400, detail=f"create_payment_link_missing:{','.join(missing)}")
            amount = float(raw.get("amount") or 0)
            if amount <= 0:
                raise HTTPException(status_code=400, detail="create_payment_link_requires_positive_amount")
            return {
                "organization_id": payload.organization_id,
                "bot_id": raw["bot_id"],
                "conversation_id": raw["conversation_id"],
                "contact_id": raw["contact_id"],
                "appointment_id": raw.get("appointment_id"),
                "title": raw["title"],
                "amount": amount,
                "currency": raw.get("currency") or "MXN",
                "reminder_minutes": int(raw.get("reminder_minutes") or 60),
                "send_receipt_on_confirm": bool(raw.get("send_receipt_on_confirm", True)),
                "metadata": {**(raw.get("metadata") or {}), **({"appointment_id": raw["appointment_id"]} if raw.get("appointment_id") else {})},
            }
        if payload.action == "update_contact_stage":
            required = ["bot_id", "contact_id", "stage"]
            missing = [item for item in required if not raw.get(item)]
            if missing:
                raise HTTPException(status_code=400, detail=f"update_contact_stage_missing:{','.join(missing)}")
            return {
                "organization_id": payload.organization_id,
                "bot_id": raw["bot_id"],
                "contact_id": raw["contact_id"],
                "conversation_id": raw.get("conversation_id"),
                "stage": str(raw["stage"]),
                "estimated_amount": float(raw.get("estimated_amount") or 0),
                "owner_user_id": raw.get("owner_user_id"),
                "next_action": raw.get("next_action") or "Calificar lead",
                "followup_at": raw.get("followup_at"),
                "tags": list(raw.get("tags") or []),
                "notes": raw.get("notes") or "",
                "lost_reason": raw.get("lost_reason"),
                "language": raw.get("language") or "es",
                "source_channel": raw.get("source_channel") or "whatsapp",
                "source_campaign": raw.get("source_campaign") or "orgánico",
            }
        if payload.action == "send_receipt":
            payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (raw.get("payment_id"),)) if raw.get("payment_id") else None
            if not payment:
                raise HTTPException(status_code=404, detail="payment_not_found")
            if payment["organization_id"] != payload.organization_id:
                raise HTTPException(status_code=403, detail="payment_scope_mismatch")
            return {
                "organization_id": payload.organization_id,
                "bot_id": payment.get("bot_id"),
                "payment_id": raw["payment_id"],
                "conversation_id": payment.get("conversation_id"),
                "contact_id": payment.get("contact_id"),
                "allow_unpaid_receipt": bool(raw.get("allow_unpaid_receipt", False)),
                "receipt_body": raw.get("receipt_body"),
            }
        raise HTTPException(status_code=400, detail="unsupported_tool_action")

    def _resolve_adapter(self, conn, *, action: str, organization_id: str, bot_id: str | None) -> tuple[BaseAdapter, dict[str, Any]]:
        integration = None
        if action in {"book_appointment", "reschedule"}:
            integration = self._latest_integration(conn, organization_id=organization_id, bot_id=bot_id, integration_type="calendar", provider="google_calendar")
            if integration:
                return GoogleCalendarAdapter(), {"integration": integration}
            return WaosCalendarAdapter(), {"integration": None}
        if action in {"create_payment_link", "send_receipt"}:
            integration = self._latest_integration(conn, organization_id=organization_id, bot_id=bot_id, integration_type="payments", provider="stripe") or self._latest_integration(conn, organization_id=organization_id, bot_id=bot_id, integration_type="commerce", provider="stripe")
            return StripePaymentsAdapter(), {"integration": integration}
        if action == "update_contact_stage":
            return WaosCrmAdapter(), {"integration": None}
        raise HTTPException(status_code=400, detail="unsupported_tool_action")

    def _latest_integration(self, conn, *, organization_id: str, bot_id: str | None, integration_type: str, provider: str | None = None) -> dict[str, Any] | None:
        where = ["organization_id = ?", "integration_type = ?", "status IN ('active','configured','connected')"]
        params: list[Any] = [organization_id, integration_type]
        if provider:
            where.append("provider = ?")
            params.append(provider)
        if bot_id:
            row = fetch_one(
                conn,
                f"SELECT * FROM integration_connections WHERE {' AND '.join(where)} AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY updated_at DESC LIMIT 1",
                tuple([*params, bot_id]),
            )
            if row:
                return row
        return fetch_one(
            conn,
            f"SELECT * FROM integration_connections WHERE {' AND '.join(where)} AND bot_id IS NULL ORDER BY updated_at DESC LIMIT 1",
            tuple(params),
        )

    def _default_idempotency_key(self, action: str, organization_id: str, normalized_payload: dict[str, Any]) -> str:
        # Legacy helper kept only for backwards internal callers; execute paths must use _resolve_idempotency_key.
        return f"tool-exec:legacy:{organization_id}:{action}:{canonical_hash(normalized_payload)}"

    def _confirmation_token_secret(self) -> str:
        return f"{settings.app_secret}:tool-execution-confirmation:v1"

    def _build_confirmation_token(self, *, run_id: str, normalized_payload: dict[str, Any]) -> str:
        exp = int(utcnow().timestamp()) + 15 * 60
        return sign_payload(
            {
                "purpose": "tool_execution_confirmation",
                "preview_execution_id": run_id,
                "payload_hash": canonical_hash(normalized_payload),
                "exp": exp,
            },
            self._confirmation_token_secret(),
        )

    def _verify_confirmation_token(self, token: str, *, preview: dict[str, Any], normalized_payload: dict[str, Any]) -> None:
        claims = verify_signed_payload(token, self._confirmation_token_secret())
        if not claims:
            raise HTTPException(status_code=409, detail="tool_execution_confirmation_token_invalid")
        expected_payload_hash = canonical_hash(normalized_payload)
        if claims.get("purpose") != "tool_execution_confirmation":
            raise HTTPException(status_code=409, detail="tool_execution_confirmation_token_invalid")
        if claims.get("preview_execution_id") != preview.get("id"):
            raise HTTPException(status_code=409, detail="tool_execution_confirmation_token_scope_mismatch")
        if claims.get("payload_hash") != expected_payload_hash:
            raise HTTPException(status_code=409, detail="tool_execution_confirmation_token_payload_mismatch")

    def _hash_confirmation_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest() if token else ""
