from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from ..config import settings
from ..db import fetch_all, fetch_one, get_pool_stats, migration_status, table_exists
from ..repositories import create_audit_log
from .uow import UnitOfWork

APP_DIR = Path(__file__).resolve().parents[1]
GLOBAL_SETTINGS_PATH = APP_DIR / "global_settings.json"


class SystemService:
    def read_global_settings(self) -> dict[str, Any]:
        if not GLOBAL_SETTINGS_PATH.exists():
            defaults = {
                "global_policy": "No inventar precios, políticas ni disponibilidad.",
                "default_model": settings.openai_model,
                "freeze_minutes_after_takeover": 30,
            }
            GLOBAL_SETTINGS_PATH.write_text(json.dumps(defaults, indent=2, ensure_ascii=False), encoding="utf-8")
            return defaults
        return json.loads(GLOBAL_SETTINGS_PATH.read_text(encoding="utf-8"))

    def write_global_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        GLOBAL_SETTINGS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return data

    def system_status_payload(self, uow: UnitOfWork) -> dict[str, Any]:
        conn = uow.conn
        checks: list[dict[str, Any]] = []
        overall_status = "ok"

        try:
            fetch_one(conn, "SELECT 1 AS ok")
            checks.append({"name": "database", "status": "ok", "detail": f"{settings.database_backend} reachable"})
        except Exception as exc:  # pragma: no cover
            overall_status = "degraded"
            checks.append({"name": "database", "status": "error", "detail": str(exc)})

        global_settings_exists = GLOBAL_SETTINGS_PATH.exists()
        checks.append({
            "name": "global_settings",
            "status": "ok" if global_settings_exists else "warning",
            "detail": str(GLOBAL_SETTINGS_PATH),
        })
        if not global_settings_exists and overall_status == "ok":
            overall_status = "degraded"

        checks.append({"name": "security_headers", "status": "ok", "detail": "Secure runtime headers enabled"})
        checks.append({
            "name": "cors",
            "status": "ok" if settings.cors_allowed_origins else "warning",
            "detail": f"{len(settings.cors_allowed_origins)} configured origins",
        })
        checks.append({"name": "db_pool", "status": "ok", "detail": str(get_pool_stats())})

        launch_checks = [
            {"name": "APP_SECRET", "status": "ok" if not settings.app_secret_is_default else "warning", "detail": "Default secret must be replaced in production"},
            {"name": "SECRET_ENCRYPTION_KEY", "status": "ok" if not settings.encryption_key_is_default else "warning", "detail": "Set a dedicated encryption key"},
            {"name": "CORS_ALLOWED_ORIGINS", "status": "ok" if settings.cors_allowed_origins else "warning", "detail": ", ".join(settings.cors_allowed_origins)},
            {"name": "SECURE_COOKIES", "status": "ok" if settings.secure_cookies else "warning", "detail": f"secure_cookies={settings.secure_cookies}"},
        ]
        if any(item["status"] != "ok" for item in launch_checks) and overall_status == "ok":
            overall_status = "degraded"

        return {
            "status": overall_status,
            "environment": settings.app_env,
            "version": settings.app_version,
            "checks": checks,
            "launch_checks": launch_checks,
            "config": settings.public_summary(),
        }

    def healthz(self, uow: UnitOfWork) -> dict[str, Any]:
        payload = self.system_status_payload(uow)
        return {
            "status": payload["status"],
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
        }

    def readyz(self, uow: UnitOfWork) -> JSONResponse:
        payload = self.system_status_payload(uow)
        status_code = 503 if payload["status"] == "error" else 200
        return JSONResponse(status_code=status_code, content=payload)

    def runtime_health_panel(self, uow: UnitOfWork) -> dict[str, Any]:
        conn = uow.conn
        migrations = migration_status(conn)

        def _count(sql: str, params=()) -> int:
            row = fetch_one(conn, sql, params)
            return int((row or {}).get("value") or 0)

        queue = {
            "jobs_queued": _count("SELECT COUNT(*) AS value FROM automation_jobs WHERE status IN ('queued', 'retry')"),
            "jobs_stuck": _count("SELECT COUNT(*) AS value FROM automation_jobs WHERE status = 'locked'"),
            "outbox_queued": _count("SELECT COUNT(*) AS value FROM outbox_messages WHERE status IN ('queued', 'retry')"),
            "outbox_dead_letters": _count("SELECT COUNT(*) AS value FROM outbox_messages WHERE status = 'dead_letter'"),
        }
        webhooks = {
            "locks_processing": _count("SELECT COUNT(*) AS value FROM inbound_message_locks WHERE status = 'processing'") if table_exists(conn, 'inbound_message_locks') else 0,
            "recent_receipts": _count("SELECT COUNT(*) AS value FROM webhook_event_receipts") if table_exists(conn, 'webhook_event_receipts') else 0,
        }
        releases = {
            "blocked": _count("SELECT COUNT(*) AS value FROM release_requests WHERE status IN ('blocked', 'rejected', 'pending_approval')") if table_exists(conn, 'release_requests') else 0,
            "ready": _count("SELECT COUNT(*) AS value FROM release_requests WHERE status IN ('approved', 'ready', 'published')") if table_exists(conn, 'release_requests') else 0,
        }
        providers = fetch_all(conn, "SELECT provider, status, health_status, credential_status, last_error, updated_at FROM integration_connections ORDER BY updated_at DESC LIMIT 20") if table_exists(conn, 'integration_connections') else []
        ai_ok = bool(settings.openai_api_key)
        return {
            "status": "ok" if migrations["pending_count"] == 0 else "degraded",
            "database": {"backend": settings.database_backend, "pool": get_pool_stats(), "migrations": migrations},
            "ai": {"configured": ai_ok, "provider": "openai" if ai_ok else "heuristic_only"},
            "queue": queue,
            "webhooks": webhooks,
            "releases": releases,
            "providers": providers,
        }

    def get_global_settings(self, *, user: dict) -> dict[str, Any]:
        if user["global_role"] != "super_admin":
            raise HTTPException(status_code=403, detail="Only super admin can access global settings")
        return self.read_global_settings()

    def update_global_settings(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        if user["global_role"] != "super_admin":
            raise HTTPException(status_code=403, detail="Only super admin can update global settings")
        current = self.read_global_settings()
        for key, value in payload.model_dump(exclude_none=True).items():
            current[key] = value
        updated = self.write_global_settings(current)
        create_audit_log(
            uow.conn,
            organization_id=None,
            actor_user_id=user["id"],
            actor_type="user",
            entity_type="global_settings",
            entity_id="global",
            action="global_settings.updated",
            metadata=updated,
        )
        uow.commit()
        return updated


system_service = SystemService()
