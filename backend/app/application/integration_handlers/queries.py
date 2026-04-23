from __future__ import annotations

from fastapi import HTTPException

from ...config import settings
from ...contracts import ok
from ...db import execute, fetch_all, fetch_one, table_exists
from ...integration_observability import integration_observability_summary, list_integration_events
from ...platform import list_integration_sync_runs, list_rate_limit_policies, resolve_secret, serialize_secret_row
from ...providers.google_calendar import google_calendar_provider
from ...providers.meta import meta_provider
from ...providers.stripe import stripe_provider
from ...repositories import create_audit_log, get_bot, get_whatsapp_number_for_bot
from ...security import ensure_bot_access, ensure_org_access
from ...utils import from_json, new_id, to_json, utcnow_iso
from ...whatsapp import resolve_whatsapp_app_secret
from ...integrations_runtime import build_google_oauth_url, exchange_google_oauth_code, get_google_calendar_availability, list_google_calendars, sync_google_calendar, test_google_calendar_connection
from ..support import org_filter_sql, require_permission
from ..uow import UnitOfWork

def list_integrations(self, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, limit: int, offset: int, user: dict, clamp_limit, clamp_offset) -> list[dict]:
    if organization_id:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "integration.manage")
    where_sql, params = org_filter_sql(user, organization_id, "organization_id")
    if not where_sql:
        where_sql = " WHERE 1 = 1 "
    if bot_id:
        bot = get_bot(uow.conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if organization_id and bot["organization_id"] != organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)
        where_sql += " AND bot_id = ? "
        params.append(bot_id)
    rows = fetch_all(uow.conn, f"SELECT * FROM integration_connections {where_sql} ORDER BY updated_at DESC LIMIT ? OFFSET ?", params + [clamp_limit(limit), clamp_offset(offset)])
    return [{**row, "config": from_json(row["config_json"], {})} for row in rows]


def list_secrets(self, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, user: dict) -> list[dict]:
    if organization_id:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "secret.manage")
    where_sql, params = org_filter_sql(user, organization_id, "organization_id")
    if not where_sql:
        where_sql = " WHERE 1 = 1 "
    if bot_id:
        bot = get_bot(uow.conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if organization_id and bot["organization_id"] != organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)
        require_permission(user, bot["organization_id"], "secret.manage")
        where_sql += " AND bot_id = ? "
        params.append(bot_id)
    rows = fetch_all(uow.conn, f"SELECT * FROM secret_entries {where_sql} ORDER BY updated_at DESC", params)
    return [serialize_secret_row(row) for row in rows]


def get_rate_limits(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> list[dict]:
    ensure_org_access(user, organization_id)
    require_permission(user, organization_id, "rate_limit.manage")
    if bot_id:
        bot = get_bot(uow.conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if bot["organization_id"] != organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)
    return list_rate_limit_policies(uow.conn, organization_id=organization_id, bot_id=bot_id)


def integration_sync_runs(self, uow: UnitOfWork, *, organization_id: str, integration_id: str | None, user: dict) -> list[dict]:
    ensure_org_access(user, organization_id)
    require_permission(user, organization_id, "integration.manage")
    return list_integration_sync_runs(uow.conn, organization_id=organization_id, integration_id=integration_id)


def integration_availability(self, uow: UnitOfWork, *, integration_id: str, time_min: str, time_max: str, user: dict) -> dict:
    integration = self._get_integration(uow, integration_id)
    ensure_org_access(user, integration["organization_id"])
    require_permission(user, integration["organization_id"], "integration.manage")
    if integration["provider"] != "google_calendar":
        raise HTTPException(status_code=400, detail="Availability only available for google_calendar")
    return get_google_calendar_availability(uow.conn, {**integration, "config": from_json(integration.get("config_json"), {})}, time_min=time_min, time_max=time_max)


def list_google_calendars(self, uow: UnitOfWork, *, integration_id: str, user: dict) -> list[dict]:
    integration = self._get_integration(uow, integration_id)
    ensure_org_access(user, integration["organization_id"])
    require_permission(user, integration["organization_id"], "integration.manage")
    if integration["provider"] != "google_calendar":
        raise HTTPException(status_code=400, detail="Calendars only available for google_calendar")
    return list_google_calendars(uow.conn, {**integration, "config": from_json(integration.get("config_json"), {})})


def integration_events(self, uow: UnitOfWork, *, organization_id: str, integration_id: str | None, user: dict) -> list[dict]:
    ensure_org_access(user, organization_id)
    require_permission(user, organization_id, "integration.manage")
    return list_integration_events(uow.conn, organization_id=organization_id, integration_id=integration_id, limit=100)


def integration_observability(self, uow: UnitOfWork, *, organization_id: str, integration_id: str | None, user: dict) -> dict:
    ensure_org_access(user, organization_id)
    require_permission(user, organization_id, "integration.manage")
    return integration_observability_summary(uow.conn, organization_id=organization_id, integration_id=integration_id)


def integration_center(self, uow: UnitOfWork, *, organization_id: str, user: dict) -> dict:
    ensure_org_access(user, organization_id)
    require_permission(user, organization_id, "integration.manage")
    integrations = self.list_integrations(uow, organization_id=organization_id, bot_id=None, limit=200, offset=0, user=user, clamp_limit=lambda value: value, clamp_offset=lambda value: value)
    observability = integration_observability_summary(uow.conn, organization_id=organization_id, integration_id=None)
    sync_runs = list_integration_sync_runs(uow.conn, organization_id=organization_id, integration_id=None)[:20]
    receipts = fetch_all(uow.conn, "SELECT * FROM webhook_event_receipts WHERE organization_id = ? ORDER BY created_at DESC LIMIT 30", (organization_id,)) if table_exists(uow.conn, "webhook_event_receipts") else []
    receipt_rows = [{**row, "replay_supported": True} for row in receipts]
    dependency_map = [
        {"integration_type": "whatsapp", "modules": ["inbox", "bot-studio", "crm"]},
        {"integration_type": "calendar", "modules": ["agenda", "inbox", "appointments"]},
        {"integration_type": "payments", "modules": ["commerce", "crm", "client portal"]},
    ]
    degraded = [item for item in integrations if str(item.get("health_status") or item.get("status") or "").lower() not in {"healthy", "ok", "connected", "configured", "active"}]
    expiring = [item for item in integrations if item.get("credential_expires_at") or item.get("expires_at") or str(item.get("credential_status") or "").lower() in {"expired", "expiring"}]
    retry_hotspots = [
        {
            "integration_id": item.get("id"),
            "name": item.get("name"),
            "provider": item.get("provider"),
            "retry_count": int(item.get("retry_count") or 0),
            "last_error": item.get("last_error"),
            "health_status": item.get("health_status") or item.get("status"),
        }
        for item in integrations if int(item.get("retry_count") or 0) > 0 or item.get("last_error")
    ]
    return ok({
        "organization_id": organization_id,
        "summary": {
            "total_integrations": len(integrations),
            "active_integrations": len([item for item in integrations if str(item.get("status") or "").lower() in {"active", "connected", "configured"}]),
            "degraded_integrations": len(degraded),
            "credential_alerts": len(expiring),
            "failed_receipts": len([item for item in receipt_rows if str(item.get("status") or "").lower() not in {"processed", "ok", "completed"}]),
            "retry_hotspots": len(retry_hotspots),
        },
        "integrations": integrations,
        "observability": observability,
        "recent_sync_runs": [{**row, "summary": from_json(row.get("summary_json"), {}), "error": from_json(row.get("error_json"), {})} for row in sync_runs],
        "failed_receipts": receipt_rows,
        "retry_hotspots": retry_hotspots,
        "dependency_map": dependency_map,
    })

