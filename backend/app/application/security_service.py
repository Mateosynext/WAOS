from __future__ import annotations

from fastapi import HTTPException, Request

from ..db import execute, fetch_one
from ..platform import (
    activate_mfa_factor,
    create_mfa_challenge,
    enroll_mfa_factor,
    get_security_policy,
    list_sso_providers,
    serialize_mfa_factor,
    store_secret,
    upsert_security_policy,
    upsert_sso_provider,
    verify_mfa_challenge,
)
from ..repositories import create_audit_log
from ..security import ensure_org_access
from ..providers.sso import sso_provider
from .support import client_ip, permissions_matrix, require_permission
from .uow import UnitOfWork


class SecurityService:
    def _audit_context(self, request: Request | None, user: dict | None = None) -> dict:
        return {
            "request_id": getattr(request.state, "request_id", None) if request else None,
            "session_id": user.get("session_id") if user else None,
            "ip_address": client_ip(request) if request else None,
            "user_agent": request.headers.get("user-agent") if request else None,
            "trace_id": getattr(request.state, "request_id", None) if request else None,
        }

    def access_matrix(self, *, user: dict) -> dict:
        return {"roles": permissions_matrix(), "current_user_role": user["global_role"]}

    def get_mfa_status(self, uow: UnitOfWork, *, user: dict) -> dict:
        factor = fetch_one(uow.conn, "SELECT * FROM mfa_factors WHERE user_id = ?", (user["id"],))
        enabled = bool(factor and factor.get("status") == "active" and not factor.get("revoked_at"))
        return {"enabled": enabled, "factor": serialize_mfa_factor(factor)}

    def enroll_mfa(self, uow: UnitOfWork, *, user: dict, request: Request | None = None) -> dict:
        enrolled = enroll_mfa_factor(uow.conn, user_id=user["id"])
        create_audit_log(uow.conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="mfa", entity_id=enrolled["id"], action="mfa.enrolled", metadata={"status": enrolled["status"]}, **self._audit_context(request, user))
        uow.commit()
        return enrolled

    def activate_mfa(self, uow: UnitOfWork, *, payload, user: dict, request: Request | None = None) -> dict:
        factor = activate_mfa_factor(uow.conn, user_id=user["id"], code=payload.code)
        if not factor:
            raise HTTPException(status_code=400, detail="Invalid code")
        create_audit_log(uow.conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="mfa", entity_id=factor["id"], action="mfa.activated", metadata={"status": factor["status"]}, **self._audit_context(request, user))
        uow.commit()
        return factor

    def regenerate_mfa_recovery_codes(self, uow: UnitOfWork, *, payload, user: dict, request: Request | None = None) -> dict:
        challenge = create_mfa_challenge(uow.conn, user_id=user["id"])
        if not challenge or not verify_mfa_challenge(uow.conn, user_id=user["id"], challenge_id=challenge["id"], code=payload.code):
            raise HTTPException(status_code=401, detail="Invalid MFA code")
        factor = enroll_mfa_factor(uow.conn, user_id=user["id"])
        active = activate_mfa_factor(uow.conn, user_id=user["id"], code=payload.code)
        create_audit_log(uow.conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="mfa", entity_id=active["id"] if active else None, action="mfa.recovery_codes_regenerated", metadata={}, severity="warning", **self._audit_context(request, user))
        uow.commit()
        return {"factor": active, "recovery_codes": factor.get("recovery_codes")}

    def get_security_policies(self, uow: UnitOfWork, *, organization_id: str, user: dict) -> dict:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "security.manage")
        return get_security_policy(uow.conn, organization_id=organization_id)

    def upsert_security_policies(self, uow: UnitOfWork, *, payload, user: dict, request: Request | None = None) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "security.manage")
        row = upsert_security_policy(
            uow.conn,
            organization_id=payload.organization_id,
            updated_by=user["id"],
            require_mfa=payload.require_mfa,
            require_sso=payload.require_sso,
            session_ttl_minutes=payload.session_ttl_minutes,
            session_idle_timeout_minutes=payload.session_idle_timeout_minutes,
            step_up_window_minutes=payload.step_up_window_minutes,
            max_sessions_per_user=payload.max_sessions_per_user,
            require_dual_approval_releases=payload.require_dual_approval_releases,
            webhook_signature_required=payload.webhook_signature_required,
            strict_idempotency=payload.strict_idempotency,
            ip_allowlist=payload.ip_allowlist,
            allowed_origins=payload.allowed_origins,
        )
        create_audit_log(uow.conn, organization_id=payload.organization_id, actor_user_id=user["id"], actor_type="user", entity_type="security_policy", entity_id=row.get("id"), action="security_policy.upserted", metadata=payload.model_dump(), **self._audit_context(request, user))
        uow.commit()
        return row

    def get_sso_providers(self, uow: UnitOfWork, *, organization_id: str, user: dict) -> list[dict]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "security.manage")
        return list_sso_providers(uow.conn, organization_id=organization_id)

    def upsert_sso(self, uow: UnitOfWork, *, payload, user: dict, request: Request | None = None) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "security.manage")
        metadata = dict(payload.metadata)
        client_secret = metadata.pop("client_secret", None)
        row = upsert_sso_provider(
            uow.conn,
            organization_id=payload.organization_id,
            provider=payload.provider,
            issuer=payload.issuer,
            client_id=payload.client_id,
            status=payload.status,
            scopes=payload.scopes,
            metadata=metadata,
        )
        if client_secret:
            store_secret(uow.conn, organization_id=payload.organization_id, bot_id=None, scope="tenant", key_name=f"SSO_CLIENT_SECRET_{row['id']}", secret_value=client_secret)
        create_audit_log(uow.conn, organization_id=payload.organization_id, actor_user_id=user["id"], actor_type="user", entity_type="sso_provider", entity_id=row["id"], action="sso.upserted", metadata=payload.model_dump(exclude={"metadata"}) | {"metadata_keys": sorted(metadata.keys())}, **self._audit_context(request, user))
        uow.commit()
        return row

    def test_sso_provider(self, uow: UnitOfWork, *, provider_id: str, user: dict) -> dict:
        provider = fetch_one(uow.conn, "SELECT * FROM sso_providers WHERE id = ?", (provider_id,))
        if not provider:
            raise HTTPException(status_code=404, detail="SSO provider not found")
        ensure_org_access(user, provider["organization_id"])
        require_permission(user, provider["organization_id"], "security.manage")
        result = sso_provider.test_connection(uow.conn, provider)
        execute(uow.conn, "UPDATE sso_providers SET last_test_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (provider_id,))
        uow.commit()
        return {**provider, "result": result}

    def start_sso_provider(self, uow: UnitOfWork, *, provider_id: str) -> dict:
        provider = fetch_one(uow.conn, "SELECT * FROM sso_providers WHERE id = ?", (provider_id,))
        if not provider or provider.get("status") != "active":
            raise HTTPException(status_code=404, detail="SSO provider not found")
        return sso_provider.build_authorization_url(uow.conn, provider)

    def finish_sso_provider(self, uow: UnitOfWork, *, state: str, code: str, request: Request) -> dict:
        return sso_provider.exchange_code(uow.conn, state=state, code=code, ip_address=client_ip(request), user_agent=request.headers.get("user-agent"))


security_service = SecurityService()
