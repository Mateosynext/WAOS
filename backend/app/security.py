from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi import Header, HTTPException, Request

from .config import settings
from .request_context import get_request_context
from .utils import sign_payload, utcnow, verify_signed_payload


def accessible_org_ids(user: dict[str, Any] | None) -> list[str]:
    if not user:
        return []
    if str(user.get("global_role") or "").strip() == "super_admin":
        return [str(item).strip() for item in (user.get("organization_ids") or []) if str(item or "").strip()]
    ids: list[str] = []
    for membership in user.get("memberships") or []:
        org_id = str((membership or {}).get("organization_id") or "").strip()
        if org_id and org_id not in ids:
            ids.append(org_id)
    for org_id in user.get("organization_ids") or []:
        value = str(org_id or "").strip()
        if value and value not in ids:
            ids.append(value)
    return ids


def ensure_org_access(user: dict[str, Any] | None, organization_id: str | None) -> None:
    org_id = str(organization_id or "").strip()
    if not org_id:
        raise HTTPException(status_code=404, detail="organization_not_found")
    if user and str(user.get("global_role") or "").strip() == "super_admin":
        return
    # Guardrail: membership still validates that organization_id not in user.get("organization_ids", []) unless membership grants access.
    if org_id not in accessible_org_ids(user):
        raise HTTPException(status_code=403, detail={"code": "tenant_context_mismatch", "message": "No access to organization"})


def ensure_bot_access(user: dict[str, Any] | None, bot: dict[str, Any] | None) -> None:
    if not bot:
        raise HTTPException(status_code=404, detail="bot_not_found")
    ensure_org_access(user, str(bot.get("organization_id") or ""))


def ensure_request_scope_matches(*, organization_id: str | None = None, bot_id: str | None = None, resource_type: str = "resource") -> None:
    context = get_request_context()
    if context is None:
        return
    if organization_id and context.organization_id and str(context.organization_id) != str(organization_id):
        raise HTTPException(status_code=403, detail={"code": "tenant_context_mismatch", "resource_type": resource_type, "message": "Request organization scope does not match resource organization"})
    if bot_id and context.bot_id and str(context.bot_id) != str(bot_id):
        raise HTTPException(status_code=403, detail={"code": "bot_context_mismatch", "resource_type": resource_type, "message": "Request bot scope does not match resource bot"})


def create_access_token(user: dict[str, Any], *, session_id: str | None = None, ttl_minutes: int | None = None) -> str:
    expires_at = utcnow() + timedelta(minutes=int(ttl_minutes or settings.access_token_ttl_minutes))
    payload = {
        "sub": str(user.get("id") or user.get("user_id") or ""),
        "email": user.get("email"),
        "global_role": user.get("global_role") or "operator",
        "memberships": user.get("memberships") or [],
        "organization_ids": accessible_org_ids(user),
        "session_id": session_id,
        "exp": int(expires_at.timestamp()),
    }
    return sign_payload(payload, settings.app_secret)


def _user_from_claims(claims: dict[str, Any]) -> dict[str, Any]:
    memberships = claims.get("memberships") or []
    if not memberships and claims.get("organization_ids"):
        memberships = [{"organization_id": org_id, "role": claims.get("global_role") or "operator"} for org_id in claims.get("organization_ids") or []]
    return {
        "id": str(claims.get("sub") or claims.get("id") or claims.get("user_id") or ""),
        "email": claims.get("email"),
        "global_role": claims.get("global_role") or "operator",
        "memberships": memberships,
        "organization_ids": claims.get("organization_ids") or [item.get("organization_id") for item in memberships if item.get("organization_id")],
        "session_id": claims.get("session_id"),
    }


def get_current_user(request: Request | None = None, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token and request is not None:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    if token:
        claims = verify_signed_payload(token, settings.app_secret)
        if not claims:
            raise HTTPException(status_code=401, detail="invalid_token")
        return _user_from_claims(claims)
    if settings.app_env.strip().lower() in {"development", "dev", "local", "test", "testing"} and request is not None:
        org_id = request.headers.get("x-waos-org-id") or request.headers.get("x-organization-id") or "org_dev"
        return {
            "id": request.headers.get("x-user-id") or "user_dev",
            "email": request.headers.get("x-user-email") or "dev@example.com",
            "global_role": request.headers.get("x-user-role") or "org_admin",
            "memberships": [{"organization_id": org_id, "role": request.headers.get("x-user-role") or "org_admin"}],
            "organization_ids": [org_id],
        }
    raise HTTPException(status_code=401, detail="authentication_required")
def get_optional_current_user(request: Request | None = None, authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    """Return the authenticated user when present; return None for anonymous requests.

    This is intentionally strict for invalid tokens: invalid credentials still produce 401
    instead of silently downgrading a bad token to anonymous access.
    """
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token and request is not None:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    if not token:
        return None
    return get_current_user(request=request, authorization=f"Bearer {token}")
