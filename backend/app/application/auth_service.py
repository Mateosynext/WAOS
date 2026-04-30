from __future__ import annotations

from fastapi import Request

from ..config import settings
from ..db import fetch_all, fetch_one
from ..errors import ForbiddenError, NotFoundError, RateLimitedError, UnauthorizedError
from ..platform import (
    activate_mfa_factor,
    check_login_rate_limit,
    create_mfa_challenge,
    enroll_mfa_factor,
    get_security_policy,
    list_auth_sessions,
    record_login_attempt,
    refresh_auth_session,
    revoke_auth_session,
    revoke_other_auth_sessions,
    verify_mfa_challenge,
)
from ..repositories import create_audit_log
from ..request_context import get_request_context
from ..security import create_access_token
from ..serializers import serialize_authenticated_user
from ..utils import hash_password, password_needs_rehash, utcnow_iso, verify_password
from .support import client_ip, issue_tokens
from .uow import UnitOfWork


class AuthService:
    def _audit_context(self, request: Request | None, user: dict | None = None) -> dict:
        return {
            "request_id": getattr(request.state, "request_id", None) if request else None,
            "session_id": user.get("session_id") if user else None,
            "ip_address": client_ip(request) if request else None,
            "user_agent": request.headers.get("user-agent") if request else None,
            "trace_id": getattr(request.state, "request_id", None) if request else None,
        }

    def _scope_key(self, email: str, request: Request) -> str:
        return f"{email.strip().lower()}|{client_ip(request) or 'unknown'}"

    def _response(self, payload: dict) -> dict:
        context = get_request_context()
        meta: dict[str, str] = {}
        if context is not None:
            if context.request_id:
                meta["request_id"] = context.request_id
            if context.correlation_id:
                meta["correlation_id"] = context.correlation_id
        return {**payload, "ok": True, "meta": meta, **({"request_id": meta["request_id"]} if meta.get("request_id") else {}), **({"correlation_id": meta["correlation_id"]} if meta.get("correlation_id") else {})}

    def login(self, uow: UnitOfWork, *, payload, request: Request) -> dict:
        conn = uow.conn
        scope_key = self._scope_key(payload.email, request)
        rate_state = check_login_rate_limit(conn, scope_key=scope_key)
        if not rate_state.get("allowed"):
            raise RateLimitedError("Too many login attempts", details=rate_state)
        user = fetch_one(conn, "SELECT * FROM users WHERE email = ? AND is_active = 1", (payload.email,))
        if not user or not verify_password(payload.password, user["password_hash"]):
            result = record_login_attempt(conn, scope_key=scope_key, success=False, ip_address=client_ip(request), user_agent=request.headers.get("user-agent"))
            create_audit_log(conn, organization_id=None, actor_user_id=user.get("id") if user else None, actor_type="user" if user else "anonymous", entity_type="auth", entity_id=user.get("id") if user else payload.email, action="auth.login_failed", metadata={"email": payload.email, "rate_limit": result}, severity="warning", **self._audit_context(request))
            raise UnauthorizedError("Invalid credentials")
        if password_needs_rehash(user["password_hash"]):
            conn.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?", (hash_password(payload.password), utcnow_iso(), user["id"]))
            user = fetch_one(conn, "SELECT * FROM users WHERE id = ?", (user["id"],))
        memberships = fetch_all(
            conn,
            "SELECT organization_id, role FROM organization_members WHERE user_id = ? AND is_active = 1",
            (user["id"],),
        )
        org_ids = [m["organization_id"] for m in memberships]
        organizations = self._load_organizations(conn, org_ids)
        factors = fetch_all(conn, "SELECT * FROM mfa_factors WHERE user_id = ? AND status = 'active' AND revoked_at IS NULL", (user["id"],))
        require_mfa = bool(factors)
        require_sso = False
        max_sessions = settings.max_sessions_per_user
        session_idle_timeout_minutes = settings.session_idle_timeout_minutes
        session_ttl_minutes = settings.refresh_token_ttl_minutes
        for org_id in org_ids:
            policy = get_security_policy(conn, organization_id=org_id)
            require_mfa = require_mfa or bool(int(policy.get("require_mfa", 0)))
            require_sso = require_sso or bool(int(policy.get("require_sso", 0)))
            max_sessions = min(max_sessions, int(policy.get("max_sessions_per_user") or settings.max_sessions_per_user))
            session_idle_timeout_minutes = min(session_idle_timeout_minutes, int(policy.get("session_idle_timeout_minutes") or settings.session_idle_timeout_minutes))
            session_ttl_minutes = min(session_ttl_minutes, int(policy.get("session_ttl_minutes") or settings.refresh_token_ttl_minutes))
        if require_sso and org_ids:
            placeholders = ",".join("?" for _ in org_ids)
            active_sso = fetch_all(conn, f"SELECT * FROM sso_providers WHERE organization_id IN ({placeholders}) AND status = 'active'", org_ids)
            if active_sso:
                raise ForbiddenError("Password login disabled because SSO is required for this organization", code="sso_required")
        user_for_token = {**user, "memberships": memberships, "organization_ids": org_ids}
        user_payload = serialize_authenticated_user(user_for_token, organizations)
        if require_mfa:
            if not factors:
                if not getattr(payload, "mfa_setup_code", None):
                    enrollment = enroll_mfa_factor(conn, user_id=user["id"])
                    create_audit_log(conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="mfa", entity_id=enrollment.get("id"), action="auth.mfa_enrollment_started", metadata={"email": payload.email}, severity="warning", **self._audit_context(request))
                    return self._response(
                        {
                            "mfa_setup_required": True,
                            "user": user_payload,
                            "mfa_setup": {
                                "factor_id": enrollment.get("id"),
                                "qr_svg_data_url": enrollment.get("qr_svg_data_url"),
                                "provisioning_uri": enrollment.get("provisioning_uri"),
                                "recovery_codes": enrollment.get("recovery_codes") or [],
                            },
                        }
                    )
                activated = activate_mfa_factor(conn, user_id=user["id"], code=payload.mfa_setup_code)
                if not activated:
                    create_audit_log(conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="mfa", entity_id=None, action="auth.mfa_activation_failed", metadata={"email": payload.email}, severity="warning", **self._audit_context(request))
                    raise UnauthorizedError("Invalid MFA setup code")
                factors = fetch_all(conn, "SELECT * FROM mfa_factors WHERE user_id = ? AND status = 'active' AND revoked_at IS NULL", (user["id"],))
            if not payload.otp_code or not payload.challenge_id:
                challenge = create_mfa_challenge(conn, user_id=user["id"])
                create_audit_log(conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="mfa", entity_id=challenge["id"] if challenge else None, action="auth.mfa_challenge_issued", metadata={"email": payload.email}, **self._audit_context(request))
                return self._response(
                    {
                        "mfa_required": True,
                        "challenge_id": challenge["id"],
                        "expires_at": challenge["expires_at"],
                        "user": user_payload,
                    }
                )
            if not verify_mfa_challenge(conn, user_id=user["id"], challenge_id=payload.challenge_id, code=payload.otp_code):
                create_audit_log(conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="mfa", entity_id=payload.challenge_id, action="auth.mfa_failed", metadata={"email": payload.email}, severity="warning", **self._audit_context(request))
                raise UnauthorizedError("Invalid MFA code")
        token_bundle = issue_tokens(conn, user=user_for_token, request=request, ttl_minutes=session_ttl_minutes, idle_timeout_minutes=session_idle_timeout_minutes, max_sessions=max_sessions)
        record_login_attempt(conn, scope_key=scope_key, success=True, ip_address=client_ip(request), user_agent=request.headers.get("user-agent"))
        create_audit_log(conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="session", entity_id=token_bundle["session"]["id"], action="auth.login_succeeded", metadata={"organization_ids": org_ids, "max_sessions": max_sessions}, **self._audit_context(request))
        return self._response({**token_bundle, "user": user_payload})

    def refresh(self, uow: UnitOfWork, *, refresh_token: str, request: Request | None = None) -> dict:
        conn = uow.conn
        session = refresh_auth_session(conn, refresh_token=refresh_token, ttl_minutes=settings.refresh_token_ttl_minutes)
        if not session:
            raise UnauthorizedError("Invalid or expired refresh token", code="refresh_invalid")
        if session.get("reuse_detected"):
            raise UnauthorizedError("Refresh token reuse detected", code="refresh_reused")
        user = fetch_one(conn, "SELECT * FROM users WHERE id = ? AND is_active = 1", (session["user_id"],))
        if not user:
            raise UnauthorizedError("User not found")
        memberships = fetch_all(conn, "SELECT organization_id, role FROM organization_members WHERE user_id = ? AND is_active = 1", (user["id"],))
        org_ids = [m["organization_id"] for m in memberships]
        user_for_token = {**user, "memberships": memberships, "organization_ids": org_ids}
        access_token = create_access_token(user_for_token, session_id=session["id"])
        organizations = self._load_organizations(conn, org_ids)
        user_payload = serialize_authenticated_user(user_for_token, organizations)
        create_audit_log(conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="session", entity_id=session["id"], action="auth.refresh_succeeded", metadata={"expires_at": session["expires_at"]}, **self._audit_context(request, {"session_id": session["id"]}))
        return self._response(
            {
                "access_token": access_token,
                "refresh_token": session["refresh_token"],
                "token_type": "bearer",
                "session": {
                    "id": session["id"],
                    "expires_at": session["expires_at"],
                    "status": session["status"],
                    "max_idle_at": session.get("max_idle_at"),
                },
                "user": user_payload,
            }
        )

    def logout(self, uow: UnitOfWork, *, refresh_token: str, user: dict, request: Request | None = None) -> dict:
        conn = uow.conn
        row = revoke_auth_session(conn, refresh_token=refresh_token)
        if not row:
            raise NotFoundError("Session not found", code="session_not_found")
        create_audit_log(conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="session", entity_id=row["id"], action="auth.logout", metadata={"status": row["status"]}, **self._audit_context(request, user))
        return self._response({"session_id": row["id"], "status": row["status"]})

    def me(self, uow: UnitOfWork, *, user: dict) -> dict:
        conn = uow.conn
        if user["global_role"] == "super_admin":
            organizations = fetch_all(conn, "SELECT * FROM organizations ORDER BY created_at DESC")
        else:
            organizations = self._load_organizations(conn, user.get("organization_ids", []), order_by_created_desc=True)
        return self._response(serialize_authenticated_user(user, organizations))

    def sessions(self, uow: UnitOfWork, *, user: dict) -> dict:
        return self._response({"sessions": list_auth_sessions(uow.conn, user_id=user["id"]), "current_session_id": user.get("session_id")})

    def revoke_other_sessions(self, uow: UnitOfWork, *, user: dict, request: Request | None = None) -> dict:
        revoked = revoke_other_auth_sessions(uow.conn, user_id=user["id"], current_session_id=user.get("session_id"))
        create_audit_log(uow.conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="session", entity_id=user.get("session_id"), action="auth.other_sessions_revoked", metadata={"revoked_count": revoked}, severity="warning", **self._audit_context(request, user))
        return self._response({"revoked_count": revoked})

    def revoke_session(self, uow: UnitOfWork, *, session_id: str, user: dict, request: Request | None = None) -> dict:
        target = fetch_one(uow.conn, "SELECT * FROM auth_sessions WHERE id = ? AND user_id = ?", (session_id, user["id"]))
        if not target:
            raise NotFoundError("Session not found", code="session_not_found")
        row = revoke_auth_session(uow.conn, session_id=session_id)
        create_audit_log(uow.conn, organization_id=None, actor_user_id=user["id"], actor_type="user", entity_type="session", entity_id=session_id, action="auth.session_revoked", metadata={"status": row["status"] if row else "unknown"}, severity="warning", **self._audit_context(request, user))
        return self._response({"session_id": session_id, "status": row["status"] if row else "unknown"})

    def _load_organizations(self, conn, org_ids: list[str], *, order_by_created_desc: bool = False) -> list[dict]:
        if not org_ids:
            return []
        placeholders = ",".join("?" for _ in org_ids)
        order_by = " ORDER BY created_at DESC" if order_by_created_desc else ""
        return fetch_all(conn, f"SELECT * FROM organizations WHERE id IN ({placeholders}){order_by}", org_ids)
