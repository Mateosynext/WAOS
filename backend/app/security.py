from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .db import execute, fetch_all, fetch_one, get_connection
from .errors import TenantIsolationError, UnauthorizedError
from .utils import add_minutes, parse_iso, sign_payload, utcnow, utcnow_iso, verify_signed_payload

bearer_scheme = HTTPBearer(auto_error=False)



def create_access_token(user: dict, *, session_id: str | None = None, ttl_minutes: int | None = None) -> str:
    now = int(utcnow().timestamp())
    ttl = ttl_minutes or settings.access_token_ttl_minutes
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["global_role"],
        "type": "access",
        "iat": now,
        "nbf": now,
        "exp": now + 60 * ttl,
        "iss": settings.app_name,
    }
    if session_id:
        payload["sid"] = session_id
    return sign_payload(payload, settings.app_secret)



def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if not creds:
        raise UnauthorizedError("Missing bearer token")
    payload = verify_signed_payload(creds.credentials, settings.app_secret)
    if not payload or payload.get("type", "access") != "access":
        raise UnauthorizedError("Invalid or expired token")
    now_iso = utcnow_iso()
    now_dt = parse_iso(now_iso)
    with get_connection() as conn:
        user = fetch_one(conn, "SELECT * FROM users WHERE id = ? AND is_active = 1", (payload["sub"],))
        if not user:
            raise UnauthorizedError("User not found")
        sid = payload.get("sid")
        if sid:
            session = fetch_one(conn, "SELECT * FROM auth_sessions WHERE id = ?", (sid,))
            if not session or session["status"] != "active":
                raise UnauthorizedError("Session expired", code="session_expired")
            idle_expires = parse_iso(session.get("max_idle_at"))
            session_expires = parse_iso(session.get("expires_at"))
            if (idle_expires and now_dt and idle_expires <= now_dt) or (session_expires and now_dt and session_expires <= now_dt):
                execute(conn, "UPDATE auth_sessions SET status = 'expired', revoked_at = ?, last_seen_at = ? WHERE id = ?", (now_iso, now_iso, sid))
                raise UnauthorizedError("Session expired", code="session_expired")
            idle_timeout_minutes = int(session.get("idle_timeout_minutes") or settings.session_idle_timeout_minutes)
            execute(conn, "UPDATE auth_sessions SET last_seen_at = ?, max_idle_at = ? WHERE id = ?", (now_iso, add_minutes(now_iso, idle_timeout_minutes), sid))
        memberships = fetch_all(
            conn,
            """
            SELECT organization_id, role
            FROM organization_members
            WHERE user_id = ? AND is_active = 1
            """,
            (user["id"],),
        )
    user["memberships"] = memberships
    user["organization_ids"] = [m["organization_id"] for m in memberships]
    user["session_id"] = payload.get("sid")
    request_org_id = getattr(request.state, "organization_id", None)
    if request_org_id and user["global_role"] != "super_admin" and request_org_id not in user["organization_ids"]:
        raise HTTPException(status_code=403, detail="No access to organization")
    request.state.user_id = user["id"]
    request.state.session_id = payload.get("sid")
    return user



def require_global_roles(*allowed_roles: str):
    def _dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["global_role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return _dependency



def ensure_org_access(user: dict, organization_id: str) -> None:
    if user["global_role"] == "super_admin":
        return
    if organization_id not in user.get("organization_ids", []):
        raise HTTPException(status_code=403, detail="No access to organization")



def ensure_bot_access(user: dict, bot: dict) -> None:
    ensure_org_access(user, bot["organization_id"])



def accessible_org_ids(user: dict) -> list[str]:
    if user["global_role"] == "super_admin":
        return []
    return user.get("organization_ids", [])
