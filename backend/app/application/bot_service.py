from __future__ import annotations

from fastapi import HTTPException

from ..config import settings
from ..db import fetch_all, fetch_one
from ..performance import clamp_limit, clamp_offset
from ..platform import diff_configs, record_bot_build, validate_bot_config
from ..repositories import (
    create_audit_log,
    create_bot,
    create_or_update_knowledge_items,
    get_bot,
    list_bot_versions,
    publish_version,
    rollback_version,
)
from ..security import ensure_bot_access, ensure_org_access
from ..serializers import serialize_bot_details
from ..utils import from_json, new_id, to_json, utcnow_iso
from ..application.vertical_service import vertical_service
from ..domains.language import upsert_language_config
from .support import org_filter_sql, require_permission
from .uow import UnitOfWork


class BotService:
    def list(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, status: str | None, limit: int, offset: int) -> list[dict]:
        conn = uow.conn
        where_sql, params = org_filter_sql(user, organization_id, "b.organization_id")
        if status:
            connector = "WHERE" if not where_sql else "AND"
            where_sql += f" {connector} b.status = ? "
            params.append(status)
        query = (
            f"""
            SELECT b.*, w.phone_number, w.connection_status, w.phone_number_id
            FROM bots b
            LEFT JOIN whatsapp_numbers w ON w.bot_id = b.id
            {where_sql}
            AND b.deleted_at IS NULL
            ORDER BY b.created_at DESC
            LIMIT ? OFFSET ?
            """
            if where_sql
            else """
            SELECT b.*, w.phone_number, w.connection_status, w.phone_number_id
            FROM bots b
            LEFT JOIN whatsapp_numbers w ON w.bot_id = b.id
            WHERE b.deleted_at IS NULL
            ORDER BY b.created_at DESC
            LIMIT ? OFFSET ?
            """
        )
        return fetch_all(conn, query, params + [clamp_limit(limit), clamp_offset(offset)])

    def create(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        conn = uow.conn
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "bot.manage")
        bot = create_bot(
            conn,
            organization_id=payload.organization_id,
            business_name=payload.business_name,
            vertical=payload.vertical,
            bot_name=payload.bot_name,
            primary_objective=payload.primary_objective,
            tone=payload.tone,
            language=payload.language,
            timezone=payload.timezone,
            services=payload.services,
            hours=payload.hours,
            faqs=[item.model_dump() for item in payload.faqs],
            whatsapp_number=payload.whatsapp_number,
            publish_now=payload.publish_now,
            created_by=user,
        )
        config = from_json(bot["config_draft_json"], {})
        create_or_update_knowledge_items(conn, organization_id=payload.organization_id, bot_id=bot["id"], config=config)
        vertical_service.apply(conn, user=user, organization_id=payload.organization_id, bot_id=bot["id"], vertical=payload.vertical, business_name=payload.business_name, bot_name=payload.bot_name, tone=payload.tone, language=payload.language, timezone=payload.timezone, primary_objective=payload.primary_objective, services=payload.services, faqs=[item.model_dump() for item in payload.faqs], hours=payload.hours, whatsapp_number=payload.whatsapp_number)
        upsert_language_config(conn, organization_id=payload.organization_id, bot_id=bot["id"], default_language=payload.language, supported_languages=[payload.language, "en" if payload.language != "en" else "es"], handoff_respect_language=True)
        if payload.publish_now and bot.get("published_version_id"):
            version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ?", (bot["published_version_id"],))
            record_bot_build(
                conn,
                organization_id=payload.organization_id,
                bot_id=bot["id"],
                version_id=version["id"],
                validation=validate_bot_config(config),
                diff_summary=diff_configs({}, config),
                config=config,
            )
        return serialize_bot_details(conn, bot)

    def _seed_vertical_assets(self, conn, *, user: dict, organization_id: str, bot_id: str, vertical: str, business_name: str, bot_name: str, tone: str, language: str, timezone: str, primary_objective: str, services: list[str], faqs: list[dict], hours: str, whatsapp_number: str, replace_templates: bool = False) -> None:
        vertical_service.apply(conn, user=user, organization_id=organization_id, bot_id=bot_id, vertical=vertical, business_name=business_name, bot_name=bot_name, tone=tone, language=language, timezone=timezone, primary_objective=primary_objective, services=services, faqs=faqs, hours=hours, whatsapp_number=whatsapp_number, replace_templates=replace_templates)

    def get(self, uow: UnitOfWork, *, user: dict, bot_id: str) -> dict:
        conn = uow.conn
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        return serialize_bot_details(conn, bot)

    def update(self, uow: UnitOfWork, *, user: dict, bot_id: str, payload) -> dict:
        conn = uow.conn
        bot = self._get_accessible_bot(conn, user, bot_id)
        require_permission(user, bot["organization_id"], "bot.manage")
        name = payload.name or bot["name"]
        status = payload.status or bot["status"]
        ai_paused = int(payload.ai_paused) if payload.ai_paused is not None else bot["ai_paused"]
        vertical = payload.vertical if payload.vertical is not None else bot.get("vertical")
        apply_vertical_defaults = bool(payload.apply_vertical_defaults)
        existing_config = from_json(bot["config_draft_json"], {})
        config = existing_config if payload.config_draft is None else payload.config_draft
        config_changed = payload.config_draft is not None

        if payload.vertical is not None:
            setup = vertical_service.build_setup(
                vertical,
                business_name=(config.get("identity", {}) or {}).get("business_name") or bot.get("business_name") or name,
                bot_name=name,
                tone=(config.get("personality", {}) or {}).get("tone") or "amable",
                language=(config.get("identity", {}) or {}).get("language") or bot.get("language") or settings.default_language,
                timezone=(config.get("identity", {}) or {}).get("timezone") or bot.get("timezone") or settings.default_timezone,
                primary_objective=(config.get("objective", {}) or {}).get("primary") or "agendar",
                services=(config.get("business_knowledge", {}) or {}).get("services") or [],
                faqs=(config.get("business_knowledge", {}) or {}).get("faqs") or [],
                hours=(config.get("business_knowledge", {}) or {}).get("hours") or "",
                whatsapp_number=(config.get("integrations", {}).get("whatsapp", {}) or {}).get("phone_number") or "",
            )
            config.setdefault("identity", {})["vertical"] = vertical
            config["vertical_context"] = setup.get("vertical_context", {})
            if apply_vertical_defaults:
                config["rules"] = setup.get("rules", {})
                config["agenda"] = setup.get("agenda", {})
                config["followups"] = setup.get("followups", {})
                config["handoff"] = setup.get("handoff", {})
                config["personality"] = setup.get("personality", {})
                config["objective"] = setup.get("objective", {})
                knowledge = config.setdefault("business_knowledge", {})
                knowledge["services"] = setup.get("services", [])
                knowledge["faqs"] = setup.get("faqs", [])
                knowledge["hours"] = setup.get("business_knowledge", {}).get("hours", knowledge.get("hours", ""))
                knowledge["policies"] = setup.get("business_knowledge", {}).get("policies", [])
                config["integrations"] = {**config.get("integrations", {}), **setup.get("integrations", {})}
                config["v7_modules"] = setup.get("v7_modules", {})
            config_changed = True

        config_draft_json = to_json(config) if config_changed else bot["config_draft_json"]
        conn.execute(
            """
            UPDATE bots
            SET name = ?, vertical = ?, status = ?, ai_paused = ?, config_draft_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, vertical, status, ai_paused, config_draft_json, utcnow_iso(), bot_id),
        )
        if config_changed:
            create_or_update_knowledge_items(conn, organization_id=bot["organization_id"], bot_id=bot_id, config=config)
        if payload.vertical is not None and apply_vertical_defaults:
            self._seed_vertical_assets(
                conn,
                user=user,
                organization_id=bot["organization_id"],
                bot_id=bot_id,
                vertical=vertical or "",
                business_name=(config.get("identity", {}) or {}).get("business_name") or bot.get("business_name") or name,
                bot_name=name,
                tone=(config.get("personality", {}) or {}).get("tone") or "amable",
                language=(config.get("identity", {}) or {}).get("language") or bot.get("language") or settings.default_language,
                timezone=(config.get("identity", {}) or {}).get("timezone") or bot.get("timezone") or settings.default_timezone,
                primary_objective=(config.get("objective", {}) or {}).get("primary") or "agendar",
                services=(config.get("business_knowledge", {}) or {}).get("services") or [],
                faqs=(config.get("business_knowledge", {}) or {}).get("faqs") or [],
                hours=(config.get("business_knowledge", {}) or {}).get("hours") or "",
                whatsapp_number=(config.get("integrations", {}).get("whatsapp", {}) or {}).get("phone_number") or "",
                replace_templates=True,
            )
        create_audit_log(conn, organization_id=bot["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="bot", entity_id=bot_id, action="bot.updated", metadata={"name": name, "status": status, "ai_paused": ai_paused, "vertical": vertical, "apply_vertical_defaults": apply_vertical_defaults})
        return serialize_bot_details(conn, get_bot(conn, bot_id))

    def publish(self, uow: UnitOfWork, *, user: dict, bot_id: str, payload) -> dict:
        conn = uow.conn
        bot = self._get_accessible_bot(conn, user, bot_id)
        require_permission(user, bot["organization_id"], "release.request")
        config = from_json(bot["config_draft_json"], {})
        validation = validate_bot_config(config)
        if not validation["ok"]:
            raise HTTPException(status_code=400, detail={"message": "Draft validation failed", "validation": validation})
        previous_version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ?", (bot.get("published_version_id"),)) if bot.get("published_version_id") else None
        version = publish_version(conn, bot_id=bot_id, actor_user=user, notes=payload.notes)
        diff_summary = diff_configs(from_json(previous_version["config_json"], {}) if previous_version else {}, config)
        build = record_bot_build(
            conn,
            organization_id=bot["organization_id"],
            bot_id=bot_id,
            version_id=version["id"],
            validation=validation,
            diff_summary=diff_summary,
            config=config,
        )
        return {
            "version": version,
            "build": {
                **build,
                "validation": from_json(build["validation_json"], {}),
                "diff_summary": from_json(build["diff_summary_json"], {}),
                "artifact": from_json(build["artifact_json"], {}),
            },
            "bot": serialize_bot_details(conn, get_bot(conn, bot_id)),
        }

    def versions(self, uow: UnitOfWork, *, user: dict, bot_id: str) -> list[dict]:
        conn = uow.conn
        self._get_accessible_bot(conn, user, bot_id)
        return list_bot_versions(conn, bot_id)

    def rollback(self, uow: UnitOfWork, *, user: dict, bot_id: str, version_id: str) -> dict:
        conn = uow.conn
        self._get_accessible_bot(conn, user, bot_id)
        rollback_version(conn, bot_id=bot_id, version_id=version_id, actor_user=user)
        return serialize_bot_details(conn, get_bot(conn, bot_id))

    def pause(self, uow: UnitOfWork, *, user: dict, bot_id: str) -> dict:
        return self._set_pause_state(uow, user=user, bot_id=bot_id, ai_paused=1, action="bot.paused")

    def resume(self, uow: UnitOfWork, *, user: dict, bot_id: str) -> dict:
        return self._set_pause_state(uow, user=user, bot_id=bot_id, ai_paused=0, action="bot.resumed")

    def clone(self, uow: UnitOfWork, *, user: dict, bot_id: str, payload) -> dict:
        conn = uow.conn
        source = self._get_accessible_bot(conn, user, bot_id)
        target_org = payload.target_organization_id or source["organization_id"]
        ensure_org_access(user, target_org)
        config = from_json(source["config_draft_json"], {})
        identity = config.get("identity", {})
        clone_name = payload.new_name or f"{source['name']} Copy"
        clone_id = new_id("bot")
        now = utcnow_iso()
        config.setdefault("identity", {})["bot_name"] = clone_name
        conn.execute(
            """
            INSERT INTO bots
            (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, published_version_id, config_draft_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'inactive', 0, 'draft', NULL, ?, ?, ?)
            """,
            (
                clone_id,
                target_org,
                clone_name,
                identity.get("business_name", source["business_name"]),
                identity.get("vertical", source.get("vertical")),
                identity.get("language", source["language"]),
                identity.get("timezone", source["timezone"]),
                to_json(config),
                now,
                now,
            ),
        )
        create_or_update_knowledge_items(conn, organization_id=target_org, bot_id=clone_id, config=config)
        create_audit_log(conn, organization_id=target_org, actor_user_id=user["id"], actor_type="user", entity_type="bot", entity_id=clone_id, action="bot.cloned", metadata={"source_bot_id": bot_id, "number_cloned": False})
        return serialize_bot_details(conn, get_bot(conn, clone_id))

    def delete(self, uow: UnitOfWork, *, user: dict, bot_id: str) -> dict:
        conn = uow.conn
        bot = self._get_accessible_bot(conn, user, bot_id)
        conn.execute("UPDATE bots SET deleted_at = ?, status = 'inactive', updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), bot_id))
        create_audit_log(conn, organization_id=bot["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="bot", entity_id=bot_id, action="bot.deleted", metadata={})
        return {"ok": True}

    def _set_pause_state(self, uow: UnitOfWork, *, user: dict, bot_id: str, ai_paused: int, action: str) -> dict:
        conn = uow.conn
        bot = self._get_accessible_bot(conn, user, bot_id)
        require_permission(user, bot["organization_id"], "bot.manage")
        conn.execute("UPDATE bots SET ai_paused = ?, updated_at = ? WHERE id = ?", (ai_paused, utcnow_iso(), bot_id))
        create_audit_log(conn, organization_id=bot["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="bot", entity_id=bot_id, action=action, metadata={})
        return serialize_bot_details(conn, get_bot(conn, bot_id))

    def _get_accessible_bot(self, conn, user: dict, bot_id: str) -> dict:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        return bot
