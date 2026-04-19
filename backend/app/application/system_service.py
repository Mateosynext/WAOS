from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from ..config import settings
from ..db import fetch_all, fetch_one, get_pool_stats, migration_status, table_exists
from ..repositories import create_audit_log
from ..whatsapp_governance import whatsapp_governance_snapshot
from ..runtime_settings import GLOBAL_SETTINGS_PATH, read_global_settings, write_global_settings
from ..world_class import circuit_breaker_summary, summarize_ai_usage
from .uow import UnitOfWork


class SystemService:
    def read_global_settings(self) -> dict[str, Any]:
        return read_global_settings()

    def write_global_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        return write_global_settings(data)

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
        checks.append({"name": "openai_circuit", "status": "warning" if circuit_breaker_summary(conn).get('open') else "ok", "detail": str(circuit_breaker_summary(conn))})
        ai_usage = summarize_ai_usage(conn, limit=200)
        checks.append({"name": "ai_usage", "status": "warning" if float((ai_usage.get('totals') or {}).get('estimated_cost') or 0) > 5 else "ok", "detail": str(ai_usage.get('totals'))})

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
            "ai": ai_usage,
            "circuits": circuit_breaker_summary(conn),
            "config": settings.public_summary(),
        }

    def livez(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
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

    def whatsapp_governance_panel(self, uow: UnitOfWork, *, user: dict, bot_id: str | None = None) -> dict[str, Any]:
        organization_id = None
        memberships = user.get("memberships") or []
        if memberships:
            organization_id = memberships[0].get("organization_id")
        if not organization_id:
            raise HTTPException(status_code=403, detail="organization_context_required")
        return whatsapp_governance_snapshot(uow.conn, organization_id=organization_id, bot_id=bot_id)

    def deploy_checklist(self, uow: UnitOfWork) -> dict[str, Any]:
        payload = self.system_status_payload(uow)
        public_host = (settings.public_app_url.split('://', 1)[-1].split('/', 1)[0].split(':', 1)[0]).lower()
        api_host = (settings.api_base_url.split('://', 1)[-1].split('/', 1)[0].split(':', 1)[0]).lower()
        cors_hosts = {(origin.split('://', 1)[-1].split('/', 1)[0].split(':', 1)[0]).lower() for origin in settings.cors_allowed_origins if origin.strip()}
        allowed_hosts = {host.strip().lower() for host in settings.allowed_hosts if host.strip()}
        items = [
            {"key": "database_url", "status": "ok" if settings.database_url else "error", "detail": "DATABASE_URL configured" if settings.database_url else "DATABASE_URL missing"},
            {"key": "app_secret", "status": "ok" if not settings.app_secret_is_default else "error", "detail": "APP_SECRET rotated" if not settings.app_secret_is_default else "APP_SECRET still default"},
            {"key": "secret_encryption_key", "status": "ok" if not settings.encryption_key_is_default else "error", "detail": "SECRET_ENCRYPTION_KEY rotated" if not settings.encryption_key_is_default else "SECRET_ENCRYPTION_KEY still default"},
            {"key": "public_app_url_in_cors", "status": "ok" if public_host in cors_hosts else "error", "detail": settings.public_app_url},
            {"key": "api_host_allowed", "status": "ok" if api_host in allowed_hosts else "error", "detail": settings.api_base_url},
            {"key": "secure_cookies", "status": "ok" if settings.secure_cookies else "error", "detail": f"secure_cookies={settings.secure_cookies}"},
            {"key": "trust_proxy_headers", "status": "ok" if settings.trust_proxy_headers else "warning", "detail": f"trust_proxy_headers={settings.trust_proxy_headers}"},
            {"key": "openai_provider", "status": "ok" if settings.openai_api_key else "warning", "detail": settings.openai_base_url},
            {"key": "migrations_mode", "status": "ok" if settings.auto_run_migrations else "warning", "detail": f"auto_run_migrations={settings.auto_run_migrations}"},
        ]
        counts = {"ok": 0, "warning": 0, "error": 0}
        for item in items:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        status = "error" if counts["error"] else ("degraded" if counts["warning"] else "ok")
        return {
            "status": status,
            "counts": counts,
            "items": items,
            "system": {
                "environment": settings.app_env,
                "version": settings.app_version,
                "health": payload["status"],
            },
        }

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
        ai_usage = summarize_ai_usage(conn, limit=200)
        circuits = circuit_breaker_summary(conn)
        oldest_job = fetch_one(conn, "SELECT scheduled_for FROM automation_jobs WHERE status IN ('queued','retry','scheduled') ORDER BY scheduled_for ASC LIMIT 1") if table_exists(conn, 'automation_jobs') else None
        autoscaling = runtime_autoscaling_plan(conn)
        modules = module_health_checks(conn)
        return {
            "status": "ok" if migrations["pending_count"] == 0 and circuits.get('open', 0) == 0 and modules.get('status') == 'ok' else "degraded",
            "database": {"backend": settings.database_backend, "pool": get_pool_stats(), "migrations": migrations},
            "ai": {"configured": ai_ok, "provider": "openai" if ai_ok else "heuristic_only", "usage": ai_usage, "circuits": circuits},
            "queue": {**queue, "oldest_scheduled_for": (oldest_job or {}).get('scheduled_for'), "recommended_worker_concurrency": max(1, min(20, 1 + int(queue.get('jobs_queued') or 0) // 25 + int(queue.get('outbox_queued') or 0) // 50)), "autoscaling": autoscaling.get('autoscaling')},
            "webhooks": webhooks,
            "releases": releases,
            "providers": providers,
            "modules": modules,
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
