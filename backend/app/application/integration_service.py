from __future__ import annotations

from fastapi import HTTPException

from ..config import settings
from ..contracts import ok
from ..db import execute, fetch_all, fetch_one, table_exists
from ..integration_observability import integration_observability_summary, list_integration_events
from ..providers.google_calendar import google_calendar_provider
from ..providers.meta import meta_provider
from ..providers.stripe import stripe_provider
from ..platform import (
    create_integration_sync_run,
    finish_integration_sync_run,
    list_integration_sync_runs,
    list_rate_limit_policies,
    resolve_secret,
    serialize_secret_row,
    store_secret,
    upsert_integration,
    upsert_rate_limit_policy,
)
from ..repositories import create_audit_log, get_bot, get_whatsapp_number_for_bot
from ..security import ensure_bot_access, ensure_org_access
from ..utils import from_json, new_id, to_json, utcnow_iso
from ..whatsapp import resolve_whatsapp_app_secret
from .support import org_filter_sql, require_permission
from .uow import UnitOfWork


class IntegrationService:
    def _get_integration(self, uow: UnitOfWork, integration_id: str) -> dict:
        row = fetch_one(uow.conn, "SELECT * FROM integration_connections WHERE id = ?", (integration_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Integration not found")
        return row

    def _ensure_integration_access(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> None:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "integration.manage")
        if bot_id:
            bot = get_bot(uow.conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            if bot["organization_id"] != organization_id:
                raise HTTPException(status_code=403, detail="Bot does not belong to organization")
            ensure_bot_access(user, bot)

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

    def upsert_integration(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        self._ensure_integration_access(uow, organization_id=payload.organization_id, bot_id=payload.bot_id, user=user)
        integration = upsert_integration(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            integration_type=payload.integration_type,
            provider=payload.provider,
            name=payload.name,
            status=payload.status,
            config=payload.config,
        )
        create_audit_log(uow.conn, organization_id=payload.organization_id, actor_user_id=user["id"], actor_type="user", entity_type="integration", entity_id=integration["id"], action="integration.upserted", metadata=payload.model_dump(exclude={"config"}) | {"config_keys": sorted(payload.config.keys())})
        uow.commit()
        return {**integration, "config": from_json(integration["config_json"], {})}

    def configure_whatsapp(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        self._ensure_integration_access(uow, organization_id=payload.organization_id, bot_id=payload.bot_id, user=user)
        config = {
            "phone_number": payload.phone_number,
            "phone_number_id": payload.phone_number_id,
            "waba_id": payload.waba_id,
            "webhook_verify_token": payload.webhook_verify_token or settings.meta_verify_token,
        }
        final_status = "active" if payload.access_token and payload.phone_number_id else payload.status
        integration = upsert_integration(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            integration_type="whatsapp",
            provider=payload.provider,
            name=payload.name,
            status=final_status,
            config=config,
        )
        scope = "bot" if payload.bot_id else "tenant"
        if payload.access_token:
            store_secret(uow.conn, organization_id=payload.organization_id, bot_id=payload.bot_id, scope=scope, key_name="META_ACCESS_TOKEN", secret_value=payload.access_token)
        if payload.app_secret:
            store_secret(uow.conn, organization_id=payload.organization_id, bot_id=payload.bot_id, scope=scope, key_name="META_APP_SECRET", secret_value=payload.app_secret)
        if payload.bot_id:
            existing = fetch_one(uow.conn, "SELECT * FROM whatsapp_numbers WHERE bot_id = ?", (payload.bot_id,))
            now = utcnow_iso()
            if existing:
                execute(
                    uow.conn,
                    "UPDATE whatsapp_numbers SET phone_number = ?, phone_number_id = ?, waba_id = ?, connection_status = ?, webhook_verify_token = ?, access_token_masked = ?, updated_at = ? WHERE id = ?",
                    (payload.phone_number, payload.phone_number_id, payload.waba_id, "connected" if payload.access_token and payload.phone_number_id else "configured", payload.webhook_verify_token or settings.meta_verify_token, "***redacted" if payload.access_token else existing.get("access_token_masked"), now, existing["id"]),
                )
            else:
                execute(
                    uow.conn,
                    "INSERT INTO whatsapp_numbers (id, organization_id, bot_id, provider, phone_number, phone_number_id, waba_id, connection_status, webhook_verify_token, access_token_masked, metadata_json, created_at, updated_at) VALUES (?, ?, ?, 'meta_cloud_api', ?, ?, ?, ?, ?, ?, '{}', ?, ?)",
                    (new_id("wan"), payload.organization_id, payload.bot_id, payload.phone_number, payload.phone_number_id or f"PHONE-{payload.bot_id[-8:]}", payload.waba_id, "connected" if payload.access_token and payload.phone_number_id else "configured", payload.webhook_verify_token or settings.meta_verify_token, "***redacted" if payload.access_token else None, now, now),
                )
        create_audit_log(
            uow.conn,
            organization_id=payload.organization_id,
            actor_user_id=user["id"],
            actor_type="user",
            entity_type="integration",
            entity_id=integration["id"],
            action="integration.whatsapp.configured",
            metadata={"bot_id": payload.bot_id, "phone_number_id": payload.phone_number_id, "waba_id": payload.waba_id},
        )
        uow.commit()
        row = fetch_one(uow.conn, "SELECT * FROM integration_connections WHERE id = ?", (integration["id"],))
        return {**row, "config": from_json((row or {}).get("config_json"), {})}


    def configure_google_calendar(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        self._ensure_integration_access(uow, organization_id=payload.organization_id, bot_id=payload.bot_id, user=user)
        config = {
            "client_id": payload.client_id,
            "redirect_uri": payload.redirect_uri,
            "frontend_redirect_uri": payload.frontend_redirect_uri or f"{settings.public_app_url.rstrip('/')}/integrations?section=configuracion",
            "calendar_id": payload.calendar_id,
            "scopes": payload.scopes,
            "timezone": payload.timezone or settings.default_timezone,
            "sync_mode": "auto" if payload.auto_sync_enabled else "manual",
            "sync_frequency_minutes": max(5, int(payload.sync_frequency_minutes or 30)),
        }
        integration = upsert_integration(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            integration_type="calendar",
            provider="google_calendar",
            name=payload.name,
            status=payload.status,
            config=config,
        )
        scope = "bot" if payload.bot_id else "tenant"
        if payload.client_secret:
            store_secret(uow.conn, organization_id=payload.organization_id, bot_id=payload.bot_id, scope=scope, key_name="GOOGLE_CLIENT_SECRET", secret_value=payload.client_secret)
        execute(
            uow.conn,
            "UPDATE integration_connections SET auto_sync_enabled = ?, sync_frequency_minutes = ?, next_sync_at = ?, retry_count = 0, last_error = NULL, updated_at = ? WHERE id = ?",
            (
                1 if payload.auto_sync_enabled else 0,
                max(5, int(payload.sync_frequency_minutes or 30)),
                utcnow_iso() if payload.auto_sync_enabled else None,
                utcnow_iso(),
                integration["id"],
            ),
        )
        create_audit_log(
            uow.conn,
            organization_id=payload.organization_id,
            actor_user_id=user["id"],
            actor_type="user",
            entity_type="integration",
            entity_id=integration["id"],
            action="integration.google_calendar.configured",
            metadata={
                "redirect_uri": payload.redirect_uri,
                "calendar_id": payload.calendar_id,
                "auto_sync_enabled": payload.auto_sync_enabled,
                "sync_frequency_minutes": max(5, int(payload.sync_frequency_minutes or 30)),
            },
        )
        uow.commit()
        row = fetch_one(uow.conn, "SELECT * FROM integration_connections WHERE id = ?", (integration["id"],))
        return {**row, "config": from_json((row or {}).get("config_json"), {})}

    def configure_stripe(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        self._ensure_integration_access(uow, organization_id=payload.organization_id, bot_id=payload.bot_id, user=user)
        config = {
            "success_url": payload.success_url,
            "cancel_url": payload.cancel_url,
            "webhook_url": payload.webhook_url,
            "publishable_key": payload.publishable_key,
            "sync_mode": "auto" if payload.auto_sync_enabled else "manual",
            "sync_frequency_minutes": max(5, int(payload.sync_frequency_minutes or 10)),
        }
        integration = upsert_integration(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            integration_type="payments",
            provider="stripe",
            name=payload.name,
            status=payload.status,
            config=config,
        )
        scope = "bot" if payload.bot_id else "tenant"
        if payload.secret_key:
            store_secret(uow.conn, organization_id=payload.organization_id, bot_id=payload.bot_id, scope=scope, key_name="STRIPE_SECRET_KEY", secret_value=payload.secret_key)
        if payload.webhook_secret:
            store_secret(uow.conn, organization_id=payload.organization_id, bot_id=payload.bot_id, scope=scope, key_name="STRIPE_WEBHOOK_SECRET", secret_value=payload.webhook_secret)
        execute(
            uow.conn,
            "UPDATE integration_connections SET auto_sync_enabled = ?, sync_frequency_minutes = ?, next_sync_at = ?, retry_count = 0, last_error = NULL, updated_at = ? WHERE id = ?",
            (
                1 if payload.auto_sync_enabled else 0,
                max(5, int(payload.sync_frequency_minutes or 10)),
                utcnow_iso() if payload.auto_sync_enabled else None,
                utcnow_iso(),
                integration["id"],
            ),
        )
        create_audit_log(
            uow.conn,
            organization_id=payload.organization_id,
            actor_user_id=user["id"],
            actor_type="user",
            entity_type="integration",
            entity_id=integration["id"],
            action="integration.stripe.configured",
            metadata={
                "success_url": payload.success_url,
                "cancel_url": payload.cancel_url,
                "webhook_url": payload.webhook_url,
                "auto_sync_enabled": payload.auto_sync_enabled,
                "sync_frequency_minutes": max(5, int(payload.sync_frequency_minutes or 10)),
            },
        )
        uow.commit()
        row = fetch_one(uow.conn, "SELECT * FROM integration_connections WHERE id = ?", (integration["id"],))
        return {**row, "config": from_json((row or {}).get("config_json"), {})}

    def test_integration(self, uow: UnitOfWork, *, integration_id: str, user: dict) -> dict:
        row = self._get_integration(uow, integration_id)
        ensure_org_access(user, row["organization_id"])
        require_permission(user, row["organization_id"], "integration.manage")
        config = from_json(row["config_json"], {})
        try:
            if row["provider"] == "google_calendar":
                result = test_google_calendar_connection(uow.conn, {**row, "config": config})
                health_status = "healthy"
                credential_status = "connected"
                last_error = None
            elif row["provider"] == "stripe":
                has_secret = bool(resolve_secret(uow.conn, organization_id=row["organization_id"], bot_id=row.get("bot_id"), key_name="STRIPE_SECRET_KEY"))
                result = {
                    "has_secret_key": has_secret,
                    "has_publishable_key": bool(config.get("publishable_key")),
                    "has_success_url": bool(config.get("success_url")),
                    "has_cancel_url": bool(config.get("cancel_url")),
                    "has_webhook_secret": bool(resolve_secret(uow.conn, organization_id=row["organization_id"], bot_id=row.get("bot_id"), key_name="STRIPE_WEBHOOK_SECRET")),
                }
                health_status = "healthy" if has_secret and config.get("success_url") and config.get("cancel_url") else "degraded"
                credential_status = "connected" if has_secret else "missing_credentials"
                last_error = None if has_secret else "missing_stripe_secret_key"
            elif row["provider"] == "meta_cloud_api":
                token = resolve_secret(uow.conn, organization_id=row["organization_id"], bot_id=row.get("bot_id"), key_name="META_ACCESS_TOKEN")
                number = get_whatsapp_number_for_bot(uow.conn, row.get("bot_id")) if row.get("bot_id") else None
                result = {
                    "has_access_token": bool(token),
                    "phone_number_id": number.get("phone_number_id") if number else None,
                    "webhook_app_secret_configured": bool(resolve_whatsapp_app_secret(uow.conn, organization_id=row["organization_id"], bot_id=row.get("bot_id"))),
                    "waba_id": number.get("waba_id") if number else None,
                }
                health_status = "healthy" if token and number and number.get("phone_number_id") else "degraded"
                credential_status = "connected" if token else "missing_credentials"
                last_error = None if token else "missing_whatsapp_access_token"
            elif row["provider"] == "meta_embedded_signup":
                result = {
                    "has_app_id": bool(config.get("app_id")),
                    "has_config_id": bool(config.get("config_id") or config.get("setup_config_id")),
                    "has_redirect_uri": bool(config.get("redirect_uri")),
                    "embedded_signup_completed_at": config.get("embedded_signup_completed_at"),
                }
                health_status = "healthy" if result["has_app_id"] and result["has_config_id"] and result["has_redirect_uri"] else "degraded"
                credential_status = "configured" if health_status == "healthy" else "missing_credentials"
                last_error = None if health_status == "healthy" else "meta_embedded_signup_missing_config"
            else:
                has_credentials = bool(config.get("client_id") or config.get("webhook_url") or config.get("calendar_id") or config.get("access_token_masked"))
                result = {"ok": has_credentials}
                health_status = "healthy" if has_credentials else "degraded"
                credential_status = "connected" if has_credentials else "unknown"
                last_error = None if has_credentials else "integration_not_fully_configured"
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
            health_status = "degraded"
            credential_status = "error"
            last_error = str(exc)
        execute(uow.conn, "UPDATE integration_connections SET health_status = ?, credential_status = ?, last_error = ?, last_test_at = ?, updated_at = ? WHERE id = ?", (health_status, credential_status, last_error, utcnow_iso(), utcnow_iso(), integration_id))
        uow.commit()
        return {**fetch_one(uow.conn, "SELECT * FROM integration_connections WHERE id = ?", (integration_id,)), "config": config, "result": result}

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

    def create_secret(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "secret.manage")
        if payload.bot_id:
            bot = get_bot(uow.conn, payload.bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            if bot["organization_id"] != payload.organization_id:
                raise HTTPException(status_code=403, detail="Bot does not belong to organization")
            ensure_bot_access(user, bot)
        secret = store_secret(uow.conn, organization_id=payload.organization_id, bot_id=payload.bot_id, scope=payload.scope, key_name=payload.key_name, secret_value=payload.secret_value)
        create_audit_log(uow.conn, organization_id=payload.organization_id, actor_user_id=user["id"], actor_type="user", entity_type="secret", entity_id=secret["id"], action="secret.stored", metadata={"scope": payload.scope, "key_name": payload.key_name})
        uow.commit()
        return secret

    def rotate_secret(self, uow: UnitOfWork, *, secret_id: str, payload, user: dict) -> dict:
        existing = fetch_one(uow.conn, "SELECT * FROM secret_entries WHERE id = ?", (secret_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Secret not found")
        ensure_org_access(user, existing["organization_id"])
        require_permission(user, existing["organization_id"], "secret.manage")
        if existing.get("bot_id"):
            bot = get_bot(uow.conn, existing["bot_id"])
            if bot:
                ensure_bot_access(user, bot)
        secret = store_secret(uow.conn, organization_id=existing["organization_id"], bot_id=existing.get("bot_id"), scope=existing["scope"], key_name=existing["key_name"], secret_value=payload.secret_value)
        create_audit_log(uow.conn, organization_id=existing["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="secret", entity_id=secret_id, action="secret.rotated", metadata={"key_name": existing["key_name"]})
        uow.commit()
        return secret

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

    def upsert_rate_limit(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "rate_limit.manage")
        if payload.bot_id:
            bot = get_bot(uow.conn, payload.bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            if bot["organization_id"] != payload.organization_id:
                raise HTTPException(status_code=403, detail="Bot does not belong to organization")
            ensure_bot_access(user, bot)
        row = upsert_rate_limit_policy(uow.conn, organization_id=payload.organization_id, bot_id=payload.bot_id, scope=payload.scope, window_seconds=payload.window_seconds, max_requests=payload.max_requests, is_active=payload.is_active)
        create_audit_log(uow.conn, organization_id=payload.organization_id, actor_user_id=user["id"], actor_type="user", entity_type="rate_limit_policy", entity_id=row["id"], action="rate_limit.upserted", metadata=payload.model_dump())
        uow.commit()
        return row

    def integration_sync_runs(self, uow: UnitOfWork, *, organization_id: str, integration_id: str | None, user: dict) -> list[dict]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "integration.manage")
        return list_integration_sync_runs(uow.conn, organization_id=organization_id, integration_id=integration_id)

    def trigger_integration_sync(self, uow: UnitOfWork, *, integration_id: str, user: dict) -> dict:
        integration = self._get_integration(uow, integration_id)
        ensure_org_access(user, integration["organization_id"])
        require_permission(user, integration["organization_id"], "integration.manage")
        config = from_json(integration.get("config_json"), {})
        sync_run = create_integration_sync_run(uow.conn, organization_id=integration["organization_id"], integration_id=integration_id, bot_id=integration.get("bot_id"), direction="pull_push", summary={"provider": integration["provider"], "integration_type": integration["integration_type"]})
        try:
            if integration["provider"] == "google_calendar":
                summary = sync_google_calendar(uow.conn, {**integration, "config": config})
            elif integration["provider"] == "stripe":
                summary = reconcile_pending_provider_payments(uow.conn, integration={**integration, "config": config}, limit=50)
            else:
                summary = {"provider": integration["provider"], "integration_type": integration["integration_type"], "mode": "noop", "reason": "sync_not_applicable_for_provider"}
            finished = finish_integration_sync_run(uow.conn, sync_id=sync_run["id"], status="completed", summary=summary)
            execute(
                uow.conn,
                "UPDATE integration_connections SET health_status = 'healthy', credential_status = CASE WHEN provider = 'stripe' THEN credential_status ELSE 'connected' END, last_error = NULL, last_sync_at = ?, last_success_at = ?, retry_count = 0, next_sync_at = CASE WHEN auto_sync_enabled = 1 THEN ? ELSE next_sync_at END, updated_at = ? WHERE id = ?",
                (utcnow_iso(), utcnow_iso(), utcnow_iso(), utcnow_iso(), integration_id),
            )
            create_audit_log(uow.conn, organization_id=integration["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="integration", entity_id=integration_id, action="integration.synced", metadata=summary)
            uow.commit()
            return {**finished, "summary": from_json(finished.get("summary_json"), {}), "error": from_json(finished.get("error_json"), {})}
        except HTTPException:
            raise
        except Exception as exc:
            finished = finish_integration_sync_run(uow.conn, sync_id=sync_run["id"], status="failed", summary={}, error={"error": str(exc)})
            execute(uow.conn, "UPDATE integration_connections SET health_status = 'degraded', last_error = ?, retry_count = COALESCE(retry_count, 0) + 1, updated_at = ? WHERE id = ?", (str(exc), utcnow_iso(), integration_id))
            uow.commit()
            return {**finished, "summary": from_json(finished.get("summary_json"), {}), "error": from_json(finished.get("error_json"), {})}

    def integration_availability(self, uow: UnitOfWork, *, integration_id: str, time_min: str, time_max: str, user: dict) -> dict:
        integration = self._get_integration(uow, integration_id)
        ensure_org_access(user, integration["organization_id"])
        require_permission(user, integration["organization_id"], "integration.manage")
        if integration["provider"] != "google_calendar":
            raise HTTPException(status_code=400, detail="Availability only available for google_calendar")
        return get_google_calendar_availability(uow.conn, {**integration, "config": from_json(integration.get("config_json"), {})}, time_min=time_min, time_max=time_max)

    def start_meta_signup(self, uow: UnitOfWork, *, integration_id: str, user: dict) -> dict:
        integration = self._get_integration(uow, integration_id)
        ensure_org_access(user, integration["organization_id"])
        require_permission(user, integration["organization_id"], "integration.manage")
        if integration["provider"] != "meta_embedded_signup":
            raise HTTPException(status_code=400, detail="Integration is not meta_embedded_signup")
        return start_meta_embedded_signup(uow.conn, {**integration, "config": from_json(integration.get("config_json"), {})})

    def complete_meta_signup(self, uow: UnitOfWork, *, integration_id: str, payload, user: dict) -> dict:
        integration = self._get_integration(uow, integration_id)
        ensure_org_access(user, integration["organization_id"])
        require_permission(user, integration["organization_id"], "integration.manage")
        if integration["provider"] != "meta_embedded_signup":
            raise HTTPException(status_code=400, detail="Integration is not meta_embedded_signup")
        result = complete_meta_embedded_signup(
            uow.conn,
            integration=integration,
            state=payload.state,
            bot_id=integration.get("bot_id"),
            phone_number_id=payload.phone_number_id,
            phone_number=payload.phone_number,
            waba_id=payload.waba_id,
            access_token=payload.access_token,
            app_secret=payload.app_secret,
            webhook_verify_token=payload.webhook_verify_token,
            payload=payload.payload,
        )
        create_audit_log(uow.conn, organization_id=integration["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="integration", entity_id=integration_id, action="integration.meta_embedded_signup.completed", metadata={"phone_number_id": payload.phone_number_id, "waba_id": payload.waba_id})
        uow.commit()
        return result

    def start_google_oauth(self, uow: UnitOfWork, *, integration_id: str, user: dict) -> dict:
        integration = self._get_integration(uow, integration_id)
        ensure_org_access(user, integration["organization_id"])
        require_permission(user, integration["organization_id"], "integration.manage")
        if integration["provider"] != "google_calendar":
            raise HTTPException(status_code=400, detail="OAuth start currently only available for google_calendar")
        return build_google_oauth_url(uow.conn, {**integration, "config": from_json(integration.get("config_json"), {})})

    def finish_google_oauth(self, uow: UnitOfWork, *, state: str, code: str) -> dict:
        result = google_calendar_provider.exchange_code(uow.conn, state=state, code=code)
        integration = result["integration"]
        return {"ok": True, "integration_id": integration["id"], "organization_id": integration["organization_id"], "config": result["config"], "token_response": result["token_response"]}

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

    def replay_webhook_receipt(self, uow: UnitOfWork, *, receipt_id: str, payload, user: dict) -> dict:
        receipt = fetch_one(uow.conn, "SELECT * FROM webhook_event_receipts WHERE id = ?", (receipt_id,))
        if not receipt:
            raise HTTPException(status_code=404, detail="Webhook receipt not found")
        organization_id = receipt.get("organization_id")
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "integration.replay")
        now = utcnow_iso()
        preview = {
            "receipt_id": receipt_id,
            "channel": receipt.get("channel"),
            "external_event_id": receipt.get("external_event_id"),
            "current_status": receipt.get("status"),
            "dry_run": bool(payload.dry_run),
            "note": payload.note,
            "recommended_action": "safe_replay" if str(receipt.get("status") or "").lower() not in {"processed", "completed", "ok"} else "skip_duplicate",
        }
        if table_exists(uow.conn, "integration_replay_requests"):
            execute(
                uow.conn,
                "INSERT INTO integration_replay_requests (id, organization_id, webhook_receipt_id, requested_by, dry_run, status, result_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id("ireplay"), organization_id, receipt_id, user["id"], 1 if payload.dry_run else 0, "dry_run" if payload.dry_run else "requested", to_json(preview), now, now),
            )
        create_audit_log(uow.conn, organization_id=organization_id, actor_user_id=user["id"], actor_type="user", entity_type="webhook_receipt", entity_id=receipt_id, action="integration.webhook_replay_requested", metadata=preview)
        uow.commit()
        return ok(preview)


integration_service = IntegrationService()
