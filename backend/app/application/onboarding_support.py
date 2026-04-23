from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from ..db import execute, fetch_all, fetch_one, table_exists
from ..repositories import create_audit_log, get_bot, get_org
from ..security import ensure_bot_access, ensure_org_access
from ..utils import new_id, slugify, to_json, utcnow_iso
from ..vertical_onboarding_runtime import latest_guided_onboarding_wizard, get_guided_onboarding_wizard
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


DEFAULT_GO_LIVE_CHECKLIST = [
    {"key": "vertical", "label": "Vertical definida", "required": True},
    {"key": "catalog", "label": "Oferta mínima visible", "required": True},
    {"key": "channel", "label": "Canal principal conectado", "required": True},
    {"key": "bot", "label": "Bot listo para responder", "required": True},
    {"key": "agenda", "label": "Agenda o reglas mínimas listas", "required": False},
]


def vertical_key(value: str | None) -> str:
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


class OnboardingSupport:
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

        vertical = (bot or {}).get("vertical") or org.get("vertical")
        normalized_vertical = vertical_key(vertical)

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

        checklist_source = GO_LIVE_CHECKLISTS.get(normalized_vertical) or DEFAULT_GO_LIVE_CHECKLIST
        checks = {
            "vertical": bool(vertical),
            "catalog": catalog_items > 0,
            "channel": channels_ready > 0,
            "bot": bot_ready > 0,
            "agenda": bool(agenda_ready),
        }
        checklist = [{**item, "completed": checks.get(item["key"], False)} for item in checklist_source]

        if table_exists(conn, "activation_progress"):
            existing = fetch_one(conn, "SELECT id FROM activation_progress WHERE organization_id = ?", (organization_id,))
            payload = (
                existing.get("id") if existing else new_id("actp"),
                organization_id,
                (bot or {}).get("id"),
                normalized_vertical or None,
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
                execute(
                    conn,
                    """
                    UPDATE activation_progress
                    SET bot_id = ?, vertical = ?, tenant_mode = ?, activated_channels_count = ?, bots_ready_count = ?,
                        catalog_items_count = ?, agenda_ready = ?, readiness_score = ?, first_value_at = ?, ttfv_hours = ?,
                        recommended_next_step = ?, blockers_json = ?, checklist_json = ?, updated_at = ?
                    WHERE organization_id = ?
                    """,
                    (
                        (bot or {}).get("id"),
                        normalized_vertical or None,
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
                        organization_id,
                    ),
                )
            else:
                execute(
                    conn,
                    """
                    INSERT INTO activation_progress (
                        id, organization_id, bot_id, vertical, tenant_mode, activated_channels_count, bots_ready_count, catalog_items_count,
                        agenda_ready, readiness_score, first_value_at, ttfv_hours, recommended_next_step, blockers_json, checklist_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload,
                )

        return {
            "organization_id": organization_id,
            "bot_id": (bot or {}).get("id"),
            "tenant_mode": tenant_mode,
            "vertical": normalized_vertical or vertical,
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
            "feature_flags": self._current_flags(conn, organization_id, (bot or {}).get("id")),
            "guided_wizard": latest_guided_onboarding_wizard(conn, organization_id=organization_id, bot_id=(bot or {}).get("id")),
        }

    def _get_accessible_wizard(self, conn, *, wizard_id: str, user: dict, permission: str) -> dict[str, Any]:
        wizard = get_guided_onboarding_wizard(conn, wizard_id)
        if not wizard:
            raise HTTPException(status_code=404, detail="Wizard not found")
        ensure_org_access(user, wizard["organization_id"])
        require_permission(user, wizard["organization_id"], permission)
        if wizard.get("bot_id"):
            bot = get_bot(conn, wizard["bot_id"])
            if bot:
                ensure_bot_access(user, bot)
        return wizard

    def _serialize_saved_view(self, row: dict[str, Any]) -> dict[str, Any]:
        return {**row, "filters": json.loads(row.get("filter_json") or "{}")}

    def _load_saved_views(self, conn, *, organization_id: str, user_id: str) -> list[dict[str, Any]]:
        if not table_exists(conn, "inbox_saved_views"):
            return []
        rows = fetch_all(
            conn,
            "SELECT * FROM inbox_saved_views WHERE organization_id = ? AND user_id = ? ORDER BY is_default DESC, updated_at DESC, created_at DESC",
            (organization_id, user_id),
        )
        return [self._serialize_saved_view(row) for row in rows]

    def _upsert_saved_view(self, conn, *, organization_id: str, user_id: str, payload) -> dict[str, Any]:
        if not table_exists(conn, "inbox_saved_views"):
            raise HTTPException(status_code=500, detail="Saved views table is unavailable")
        slug = slugify(payload.name)[:80] or new_id("view")
        now = utcnow_iso()
        if payload.is_default:
            execute(
                conn,
                "UPDATE inbox_saved_views SET is_default = 0, updated_at = ? WHERE organization_id = ? AND user_id = ?",
                (now, organization_id, user_id),
            )
        existing = fetch_one(
            conn,
            "SELECT * FROM inbox_saved_views WHERE organization_id = ? AND user_id = ? AND slug = ?",
            (organization_id, user_id, slug),
        )
        if existing:
            view_id = existing["id"]
            execute(
                conn,
                "UPDATE inbox_saved_views SET name = ?, filter_json = ?, is_default = ?, updated_at = ? WHERE id = ?",
                (payload.name, to_json(payload.filters), 1 if payload.is_default else 0, now, view_id),
            )
        else:
            view_id = new_id("view")
            execute(
                conn,
                "INSERT INTO inbox_saved_views (id, organization_id, user_id, name, slug, filter_json, is_default, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (view_id, organization_id, user_id, payload.name, slug, to_json(payload.filters), 1 if payload.is_default else 0, now, now),
            )
        create_audit_log(
            conn,
            organization_id=organization_id,
            actor_user_id=user_id,
            actor_type="user",
            entity_type="inbox_saved_view",
            entity_id=view_id,
            action="inbox_saved_view.upserted",
            metadata={"name": payload.name, "is_default": payload.is_default},
        )
        row = fetch_one(conn, "SELECT * FROM inbox_saved_views WHERE id = ?", (view_id,))
        return self._serialize_saved_view(row)
