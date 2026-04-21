from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ..contracts import ok
from ..db import execute, fetch_all, fetch_one, table_exists
from ..repositories import create_audit_log, get_bot, get_org
from ..vertical_onboarding_runtime import (
    build_guided_onboarding_blueprint,
    get_guided_onboarding_wizard,
    latest_guided_onboarding_wizard,
    list_guided_onboarding_verticals,
    apply_guided_onboarding_wizard,
    dry_run_guided_onboarding_wizard,
    refresh_guided_onboarding_validation_snapshot,
    reconcile_guided_onboarding_wizard_integrity,
    start_guided_onboarding_wizard,
    update_guided_onboarding_step,
)
from ..security import ensure_bot_access, ensure_org_access
from ..utils import new_id, slugify, to_json, utcnow_iso
from .support import require_permission
from .uow import UnitOfWork


GO_LIVE_CHECKLISTS: dict[str, list[dict[str, Any]]] = {
    "fitness": [
        {"key": "vertical", "label": "Vertical fitness definida", "required": True},
        {"key": "catalog", "label": "Servicios o membresias visibles", "required": True},
        {"key": "channel", "label": "Canal principal conectado", "required": True},
        {"key": "bot", "label": "Bot listo para responder", "required": True},
        {"key": "agenda", "label": "Agenda o reglas de booking listas", "required": True},
    ],
    "dental": [
        {"key": "vertical", "label": "Vertical dental definida", "required": True},
        {"key": "catalog", "label": "Tratamientos o valoraciones cargados", "required": True},
        {"key": "channel", "label": "Canal principal conectado", "required": True},
        {"key": "bot", "label": "Bot listo para triage y agenda", "required": True},
        {"key": "agenda", "label": "Agenda con tiempos y disponibilidad", "required": True},
    ],
    "veterinary": [
        {"key": "vertical", "label": "Vertical veterinaria definida", "required": True},
        {"key": "catalog", "label": "Servicios o vacunas visibles", "required": True},
        {"key": "channel", "label": "Canal principal conectado", "required": True},
        {"key": "bot", "label": "Bot listo para intake y agenda", "required": True},
        {"key": "agenda", "label": "Agenda o reglas de atención listas", "required": True},
    ],
    "aesthetic": [
        {"key": "vertical", "label": "Vertical estética definida", "required": True},
        {"key": "catalog", "label": "Servicios o paquetes visibles", "required": True},
        {"key": "channel", "label": "Canal principal conectado", "required": True},
        {"key": "bot", "label": "Bot con tono y respuestas listas", "required": True},
        {"key": "agenda", "label": "Agenda y rebook listos", "required": True},
    ],
}


def _vertical_key(value: str | None) -> str:
    normalized = str(value or "general").strip().lower()
    aliases = {
        "gym": "fitness",
        "clinica": "dental",
        "clinic": "dental",
        "veterinaria": "veterinary",
        "vet": "veterinary",
        "estetica": "aesthetic",
        "estética": "aesthetic",
    }
    return aliases.get(normalized, normalized)


class OnboardingService:
    def _resolve_scope(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
        conn = uow.conn
        resolved_org_id = organization_id
        resolved_bot = None
        if bot_id:
            resolved_bot = get_bot(conn, bot_id)
            if not resolved_bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            ensure_bot_access(user, resolved_bot)
            resolved_org_id = resolved_org_id or resolved_bot["organization_id"]
        if not resolved_org_id:
            memberships = user.get("memberships") or []
            resolved_org_id = memberships[0]["organization_id"] if memberships else None
        if not resolved_org_id:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, resolved_org_id)
        org = get_org(conn, resolved_org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        if resolved_bot and resolved_bot["organization_id"] != org["id"]:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        return org, resolved_bot

    def _count(self, conn, sql: str, params: tuple[Any, ...]) -> int:
        row = fetch_one(conn, sql, params)
        return int((row or {}).get("value") or 0)

    def _current_flags(self, conn, organization_id: str, bot_id: str | None) -> dict[str, bool]:
        if not table_exists(conn, "feature_flag_overrides"):
            return {}
        rows = fetch_all(
            conn,
            """
            SELECT feature_key, is_enabled, bot_id
            FROM feature_flag_overrides
            WHERE organization_id = ? AND (bot_id IS NULL OR bot_id = ?)
            ORDER BY CASE WHEN bot_id IS NULL THEN 1 ELSE 0 END, updated_at DESC
            """,
            (organization_id, bot_id),
        )
        flags: dict[str, bool] = {}
        for row in rows:
            key = str(row.get("feature_key") or "").strip()
            if key and key not in flags:
                flags[key] = bool(row.get("is_enabled"))
        return flags

    def _compute_summary(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None) -> dict[str, Any]:
        conn = uow.conn
        org = get_org(conn, organization_id)
        bot = get_bot(conn, bot_id) if bot_id else fetch_one(conn, "SELECT * FROM bots WHERE organization_id = ? ORDER BY updated_at DESC LIMIT 1", (organization_id,))
        if bot_id and not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        vertical = bot.get("vertical") if bot else None
        vertical = vertical or org.get("vertical")
        vertical_key = _vertical_key(vertical)

        channels_ready = self._count(conn, "SELECT COUNT(*) AS value FROM integration_connections WHERE organization_id = ? AND status IN ('active','configured','connected')", (organization_id,))
        bot_ready = self._count(conn, "SELECT COUNT(*) AS value FROM bots WHERE organization_id = ? AND deleted_at IS NULL", (organization_id,))
        catalog_products = self._count(conn, "SELECT COUNT(*) AS value FROM catalog_products WHERE organization_id = ? AND status = 'active'", (organization_id,)) if table_exists(conn, "catalog_products") else 0
        catalog_services = self._count(conn, "SELECT COUNT(*) AS value FROM catalog_services WHERE organization_id = ? AND status = 'active'", (organization_id,)) if table_exists(conn, "catalog_services") else 0
        promotions = self._count(conn, "SELECT COUNT(*) AS value FROM catalog_promotions WHERE organization_id = ? AND status IN ('active','scheduled')", (organization_id,)) if table_exists(conn, "catalog_promotions") else 0
        appointments = self._count(conn, "SELECT COUNT(*) AS value FROM appointments WHERE organization_id = ?", (organization_id,)) if table_exists(conn, "appointments") else 0
        messages = self._count(conn, "SELECT COUNT(*) AS value FROM messages WHERE organization_id = ?", (organization_id,))
        conversations = self._count(conn, "SELECT COUNT(*) AS value FROM conversations WHERE organization_id = ?", (organization_id,))
        payments = self._count(conn, "SELECT COUNT(*) AS value FROM commerce_payments WHERE organization_id = ? AND status IN ('paid','succeeded')", (organization_id,)) if table_exists(conn, "commerce_payments") else 0

        tenant_mode = str(org.get("tenant_mode") or "sandbox")
        catalog_items = catalog_products + catalog_services + promotions
        agenda_ready = 1 if appointments > 0 or catalog_services > 0 or channels_ready > 0 else 0

        created_at = org.get("created_at")
        first_value_candidates = [
            fetch_one(conn, "SELECT MIN(created_at) AS first_at FROM conversations WHERE organization_id = ?", (organization_id,)),
            fetch_one(conn, "SELECT MIN(created_at) AS first_at FROM appointments WHERE organization_id = ?", (organization_id,)) if table_exists(conn, "appointments") else None,
            fetch_one(conn, "SELECT MIN(created_at) AS first_at FROM commerce_payments WHERE organization_id = ? AND status IN ('paid','succeeded')", (organization_id,)) if table_exists(conn, "commerce_payments") else None,
            fetch_one(conn, "SELECT MIN(created_at) AS first_at FROM product_events WHERE organization_id = ? AND event_name = 'tenant.first_value_reached'", (organization_id,)) if table_exists(conn, "product_events") else None,
        ]
        first_value_at = next((row.get("first_at") for row in first_value_candidates if row and row.get("first_at")), None)

        readiness_parts = {
            "channel": 100 if channels_ready > 0 else 0,
            "bot": 100 if bot_ready > 0 else 0,
            "catalog": min(100, catalog_items * 25),
            "agenda": 100 if agenda_ready else 0,
            "vertical": 100 if vertical else 0,
        }
        readiness_score = round(sum(readiness_parts.values()) / len(readiness_parts))

        blockers: list[dict[str, Any]] = []
        if not vertical:
            blockers.append({"key": "vertical", "severity": "high", "message": "Todavía falta definir la vertical del tenant o del bot."})
        if bot_ready == 0:
            blockers.append({"key": "bot", "severity": "high", "message": "Todavía no existe un bot listo para operar."})
        if channels_ready == 0:
            blockers.append({"key": "channel", "severity": "high", "message": "No hay canal principal conectado."})
        if catalog_items == 0:
            blockers.append({"key": "catalog", "severity": "medium", "message": "No hay oferta visible para orientar o vender."})
        if agenda_ready == 0:
            blockers.append({"key": "agenda", "severity": "medium", "message": "La agenda o capacidad todavía no está lista para operar."})

        if not vertical:
            next_step = {"key": "define_vertical", "label": "Define la vertical", "href": "/organizations", "reason": "Esto desbloquea lenguaje, checklist y defaults."}
        elif bot_ready == 0:
            next_step = {"key": "create_bot", "label": "Configura el bot operativo", "href": "/bot-studio?mode=create", "reason": "El setup real del bot vive ahora en Bot Studio y persiste por wizard_id."}
        elif channels_ready == 0:
            next_step = {"key": "connect_channel", "label": "Conecta el canal principal", "href": "/integrations", "reason": "Sin canal el onboarding sigue siendo teórico."}
        elif catalog_items == 0:
            next_step = {"key": "publish_offer", "label": "Carga oferta mínima", "href": "/business-hub", "reason": "El bot necesita algo real que vender o explicar."}
        elif tenant_mode == "sandbox":
            next_step = {"key": "run_test", "label": "Haz prueba end to end", "href": "/releases", "reason": "Ya tienes base para probar antes de salir a vivo."}
        else:
            next_step = {"key": "optimize", "label": "Optimiza operación", "href": "/inbox", "reason": "La cuenta ya puede operar; ahora toca priorizar y medir."}

        checklist_source = GO_LIVE_CHECKLISTS.get(vertical_key) or [
            {"key": "vertical", "label": "Vertical definida", "required": True},
            {"key": "catalog", "label": "Oferta mínima visible", "required": True},
            {"key": "channel", "label": "Canal principal conectado", "required": True},
            {"key": "bot", "label": "Bot listo para responder", "required": True},
            {"key": "agenda", "label": "Agenda o reglas mínimas listas", "required": False},
        ]
        checklist = []
        checks = {
            "vertical": bool(vertical),
            "catalog": catalog_items > 0,
            "channel": channels_ready > 0,
            "bot": bot_ready > 0,
            "agenda": bool(agenda_ready),
        }
        for item in checklist_source:
            checklist.append({**item, "completed": checks.get(item["key"], False)})

        if table_exists(conn, "activation_progress"):
            existing = fetch_one(conn, "SELECT id FROM activation_progress WHERE organization_id = ?", (organization_id,))
            payload = (
                existing.get("id") if existing else new_id("actp"),
                organization_id,
                bot.get("id") if bot else None,
                vertical_key or None,
                tenant_mode,
                channels_ready,
                bot_ready,
                catalog_items,
                agenda_ready,
                readiness_score,
                first_value_at,
                None,
                next_step["key"],
                to_json(blockers),
                to_json(checklist),
                utcnow_iso(),
            )
            if existing:
                execute(conn, """
                    UPDATE activation_progress
                    SET bot_id = ?, vertical = ?, tenant_mode = ?, activated_channels_count = ?, bots_ready_count = ?,
                        catalog_items_count = ?, agenda_ready = ?, readiness_score = ?, first_value_at = ?, ttfv_hours = ?,
                        recommended_next_step = ?, blockers_json = ?, checklist_json = ?, updated_at = ?
                    WHERE organization_id = ?
                """, (bot.get("id") if bot else None, vertical_key or None, tenant_mode, channels_ready, bot_ready, catalog_items, agenda_ready, readiness_score, first_value_at, None, next_step["key"], to_json(blockers), to_json(checklist), utcnow_iso(), organization_id))
            else:
                execute(conn, """
                    INSERT INTO activation_progress (
                        id, organization_id, bot_id, vertical, tenant_mode, activated_channels_count, bots_ready_count, catalog_items_count,
                        agenda_ready, readiness_score, first_value_at, ttfv_hours, recommended_next_step, blockers_json, checklist_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, payload)

        return {
            "organization_id": organization_id,
            "bot_id": bot.get("id") if bot else None,
            "tenant_mode": tenant_mode,
            "vertical": vertical_key or vertical,
            "counts": {
                "channels": channels_ready,
                "bots": bot_ready,
                "catalog_items": catalog_items,
                "appointments": appointments,
                "conversations": conversations,
                "messages": messages,
                "payments": payments,
            },
            "progress": readiness_parts,
            "readiness_score": readiness_score,
            "blockers": blockers,
            "checklist": checklist,
            "next_step": next_step,
            "first_value_at": first_value_at,
            "created_at": created_at,
            "feature_flags": self._current_flags(conn, organization_id, bot.get("id") if bot else None),
            "guided_wizard": latest_guided_onboarding_wizard(conn, organization_id=organization_id, bot_id=bot.get("id") if bot else None),
        }

    def list_guided_verticals(self, uow: UnitOfWork, *, user: dict) -> dict[str, Any]:
        memberships = user.get("memberships") or []
        organization_id = memberships[0]["organization_id"] if memberships else None
        if organization_id:
            ensure_org_access(user, organization_id)
            require_permission(user, organization_id, "operations.read")
        return ok({"items": list_guided_onboarding_verticals(), "count": len(list_guided_onboarding_verticals())})

    def wizard_blueprint(self, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, vertical_id: str | None, subvertical: str | None, primary_objective: str | None, user: dict) -> dict[str, Any]:
        org, bot = self._resolve_scope(uow, user=user, organization_id=organization_id, bot_id=bot_id)
        require_permission(user, org["id"], "operations.read")
        blueprint = build_guided_onboarding_blueprint(
            vertical_id=vertical_id or (bot.get("vertical") if bot else None) or org.get("vertical"),
            subvertical=subvertical,
            business_name=(bot.get("business_name") if bot else None) or org.get("name") or "",
            bot_name=(bot.get("name") if bot else None) or "",
            tone="",
            language=(bot.get("language") if bot else None) or "es",
            timezone=(bot.get("timezone") if bot else None) or org.get("timezone") or "America/Mexico_City",
            primary_objective=primary_objective or "agendar",
            bot_id=bot.get("id") if bot else None,
        )
        return ok(blueprint)

    def start_wizard(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        org, bot = self._resolve_scope(uow, user=user, organization_id=payload.organization_id, bot_id=payload.bot_id)
        require_permission(user, org["id"], "activation.manage")
        wizard = start_guided_onboarding_wizard(
            uow.conn,
            organization_id=org["id"],
            bot_id=bot["id"] if bot else None,
            actor_user_id=user.get("id"),
            vertical_id=payload.vertical_id or (bot.get("vertical") if bot else None) or org.get("vertical"),
            subvertical=payload.subvertical,
            business_name=payload.business_name or (bot.get("business_name") if bot else None) or org.get("name") or "",
            bot_name=payload.bot_name or (bot.get("name") if bot else None) or "",
            tone=payload.tone or "",
            language=payload.language or ((bot.get("language") if bot else None) or "es"),
            timezone=payload.timezone or ((bot.get("timezone") if bot else None) or org.get("timezone") or "America/Mexico_City"),
            primary_objective=payload.primary_objective or "agendar",
            hours=payload.hours or "",
            whatsapp_number=payload.whatsapp_number or "",
            answers=payload.answers,
        )
        uow.commit()
        return ok(wizard)

    def get_wizard(self, uow: UnitOfWork, *, wizard_id: str, user: dict) -> dict[str, Any]:
        wizard = get_guided_onboarding_wizard(uow.conn, wizard_id)
        if not wizard:
            raise HTTPException(status_code=404, detail="Wizard not found")
        ensure_org_access(user, wizard["organization_id"])
        require_permission(user, wizard["organization_id"], "operations.read")
        if wizard.get("bot_id"):
            bot = get_bot(uow.conn, wizard["bot_id"])
            if bot:
                ensure_bot_access(user, bot)
        diagnostics = (wizard.get("diagnostics") or {}) if isinstance(wizard.get("diagnostics"), dict) else {}
        if diagnostics.get("integrity_mismatch"):
            try:
                if uow.mode == "write":
                    wizard = reconcile_guided_onboarding_wizard_integrity(uow.conn, wizard_id=wizard_id, source="get_wizard")
                    uow.commit()
                else:
                    with UnitOfWork(mode="write") as write_uow:
                        wizard = reconcile_guided_onboarding_wizard_integrity(write_uow.conn, wizard_id=wizard_id, source="get_wizard")
                        write_uow.commit()
            except ValueError:
                wizard = wizard
        recompute_state = (wizard.get("recompute_state") or {}) if isinstance(wizard.get("recompute_state"), dict) else {}
        should_refresh_snapshot = bool(
            wizard.get("validation_snapshot")
            or wizard.get("applied_at")
            or ((wizard.get("answers") or {}).get("dry_run_validation"))
            or recompute_state.get("validation_snapshot_pending")
            or (wizard.get("bot_id") and wizard.get("status") == "applied")
        )
        if should_refresh_snapshot:
            try:
                if uow.mode == "write":
                    wizard = refresh_guided_onboarding_validation_snapshot(uow.conn, wizard_id=wizard_id, source="refresh")
                    uow.commit()
                else:
                    with UnitOfWork(mode="write") as write_uow:
                        wizard = refresh_guided_onboarding_validation_snapshot(write_uow.conn, wizard_id=wizard_id, source="refresh")
                        write_uow.commit()
            except ValueError:
                wizard = wizard
        return ok(wizard)

    def update_wizard_step(self, uow: UnitOfWork, *, wizard_id: str, step_key: str, payload, user: dict) -> dict[str, Any]:
        wizard = get_guided_onboarding_wizard(uow.conn, wizard_id)
        if not wizard:
            raise HTTPException(status_code=404, detail="Wizard not found")
        ensure_org_access(user, wizard["organization_id"])
        require_permission(user, wizard["organization_id"], "activation.manage")
        if wizard.get("bot_id"):
            bot = get_bot(uow.conn, wizard["bot_id"])
            if bot:
                ensure_bot_access(user, bot)
        diagnostics = (wizard.get("diagnostics") or {}) if isinstance(wizard.get("diagnostics"), dict) else {}
        if diagnostics.get("integrity_mismatch"):
            wizard = reconcile_guided_onboarding_wizard_integrity(uow.conn, wizard_id=wizard_id, source="before_update")
        try:
            updated = update_guided_onboarding_step(
                uow.conn,
                wizard_id=wizard_id,
                step_key=step_key,
                payload=payload.payload,
                expected_revision=payload.expected_revision,
            )
        except ValueError as exc:
            detail = str(exc)
            if detail == "wizard_revision_conflict":
                raise HTTPException(status_code=409, detail="wizard_revision_conflict")
            if detail == "invalid_step_key":
                raise HTTPException(status_code=400, detail="invalid_step_key")
            if detail == "wizard_step_out_of_sequence":
                raise HTTPException(status_code=409, detail="wizard_step_out_of_sequence")
            if detail == "wizard_not_found":
                raise HTTPException(status_code=404, detail="Wizard not found")
            raise HTTPException(status_code=400, detail=detail)
        uow.commit()
        return ok(updated)

    def dry_run_wizard(self, uow: UnitOfWork, *, wizard_id: str, user: dict) -> dict[str, Any]:
        wizard = get_guided_onboarding_wizard(uow.conn, wizard_id)
        if not wizard:
            raise HTTPException(status_code=404, detail="Wizard not found")
        ensure_org_access(user, wizard["organization_id"])
        require_permission(user, wizard["organization_id"], "activation.manage")
        if wizard.get("bot_id"):
            bot = get_bot(uow.conn, wizard["bot_id"])
            if bot:
                ensure_bot_access(user, bot)
        diagnostics = (wizard.get("diagnostics") or {}) if isinstance(wizard.get("diagnostics"), dict) else {}
        if diagnostics.get("integrity_mismatch"):
            wizard = reconcile_guided_onboarding_wizard_integrity(uow.conn, wizard_id=wizard_id, source="before_dry_run")
        try:
            result = dry_run_guided_onboarding_wizard(uow.conn, wizard_id=wizard_id)
        except ValueError as exc:
            detail = str(exc)
            if detail == "wizard_not_found":
                raise HTTPException(status_code=404, detail="Wizard not found")
            raise HTTPException(status_code=400, detail=detail)
        uow.commit()
        return ok(result)

    def apply_wizard(self, uow: UnitOfWork, *, wizard_id: str, user: dict) -> dict[str, Any]:
        wizard = get_guided_onboarding_wizard(uow.conn, wizard_id)
        if not wizard:
            raise HTTPException(status_code=404, detail="Wizard not found")
        ensure_org_access(user, wizard["organization_id"])
        require_permission(user, wizard["organization_id"], "activation.manage")
        if wizard.get("bot_id"):
            bot = get_bot(uow.conn, wizard["bot_id"])
            if bot:
                ensure_bot_access(user, bot)
        diagnostics = (wizard.get("diagnostics") or {}) if isinstance(wizard.get("diagnostics"), dict) else {}
        if diagnostics.get("integrity_mismatch"):
            wizard = reconcile_guided_onboarding_wizard_integrity(uow.conn, wizard_id=wizard_id, source="before_apply")
        try:
            result = apply_guided_onboarding_wizard(uow.conn, wizard_id=wizard_id, actor_user=user)
        except ValueError as exc:
            detail = str(exc)
            if detail == "wizard_requires_bot":
                raise HTTPException(status_code=400, detail="Wizard requires a bot before apply")
            if detail == "bot_not_found":
                raise HTTPException(status_code=404, detail="Bot not found")
            if detail == "dry_run_required":
                raise HTTPException(status_code=400, detail="dry_run_required")
            if detail == "dry_run_blocked":
                raise HTTPException(status_code=400, detail="dry_run_blocked")
            raise HTTPException(status_code=400, detail=detail)
        uow.commit()
        return ok(result)

    def summary(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None) -> dict[str, Any]:
        org, bot = self._resolve_scope(uow, user=user, organization_id=organization_id, bot_id=bot_id)
        require_permission(user, org["id"], "operations.read")
        return ok(self._compute_summary(uow, organization_id=org["id"], bot_id=bot["id"] if bot else None))

    def set_tenant_mode(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        conn = uow.conn
        org, _ = self._resolve_scope(uow, user=user, organization_id=payload.organization_id, bot_id=None)
        require_permission(user, org["id"], "activation.manage")
        execute(conn, "UPDATE organizations SET tenant_mode = ?, updated_at = ? WHERE id = ?", (payload.tenant_mode, utcnow_iso(), org["id"]))
        if table_exists(conn, "product_events"):
            execute(conn, "INSERT INTO product_events (id, organization_id, bot_id, actor_user_id, event_name, entity_type, entity_id, value_numeric, value_json, created_at) VALUES (?, ?, NULL, ?, ?, 'organization', ?, NULL, ?, ?)", (new_id('pevt'), org['id'], user['id'], 'tenant.mode_changed', org['id'], to_json({'tenant_mode': payload.tenant_mode}), utcnow_iso()))
        create_audit_log(conn, organization_id=org["id"], actor_user_id=user["id"], actor_type="user", entity_type="organization", entity_id=org["id"], action="organization.tenant_mode_updated", metadata={"tenant_mode": payload.tenant_mode})
        uow.commit()
        return self.summary(uow, user=user, organization_id=org["id"], bot_id=None)

    def list_saved_views(self, uow: UnitOfWork, *, organization_id: str, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "conversation.manage")
        rows = fetch_all(uow.conn, "SELECT * FROM inbox_saved_views WHERE organization_id = ? AND user_id = ? ORDER BY is_default DESC, updated_at DESC, created_at DESC", (organization_id, user["id"])) if table_exists(uow.conn, 'inbox_saved_views') else []
        result = []
        for row in rows:
            result.append({**row, "filters": __import__('json').loads(row.get('filter_json') or '{}')})
        return ok(result)

    def create_saved_view(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        conn = uow.conn
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "conversation.manage")
        if not table_exists(conn, 'inbox_saved_views'):
            raise HTTPException(status_code=500, detail='Saved views table is unavailable')
        slug = slugify(payload.name)[:80] or new_id('view')
        if payload.is_default:
            execute(conn, "UPDATE inbox_saved_views SET is_default = 0, updated_at = ? WHERE organization_id = ? AND user_id = ?", (utcnow_iso(), payload.organization_id, user['id']))
        existing = fetch_one(conn, "SELECT * FROM inbox_saved_views WHERE organization_id = ? AND user_id = ? AND slug = ?", (payload.organization_id, user['id'], slug))
        now = utcnow_iso()
        if existing:
            execute(conn, "UPDATE inbox_saved_views SET name = ?, filter_json = ?, is_default = ?, updated_at = ? WHERE id = ?", (payload.name, to_json(payload.filters), 1 if payload.is_default else 0, now, existing['id']))
            view_id = existing['id']
        else:
            view_id = new_id('view')
            execute(conn, "INSERT INTO inbox_saved_views (id, organization_id, user_id, name, slug, filter_json, is_default, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (view_id, payload.organization_id, user['id'], payload.name, slug, to_json(payload.filters), 1 if payload.is_default else 0, now, now))
        create_audit_log(conn, organization_id=payload.organization_id, actor_user_id=user['id'], actor_type='user', entity_type='inbox_saved_view', entity_id=view_id, action='inbox_saved_view.upserted', metadata={'name': payload.name, 'is_default': payload.is_default})
        uow.commit()
        row = fetch_one(conn, "SELECT * FROM inbox_saved_views WHERE id = ?", (view_id,))
        return ok({**row, 'filters': __import__('json').loads(row.get('filter_json') or '{}')})


onboarding_service = OnboardingService()
