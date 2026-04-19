from __future__ import annotations

import ipaddress
from typing import Any

from fastapi import HTTPException, Request

from ..db import fetch_all, fetch_one
from ..platform import create_auth_session
from ..config import settings
from ..repositories import get_bot, get_contact, get_contact_memory, get_conversation, get_whatsapp_number_for_bot, list_bot_versions
from ..security import accessible_org_ids, create_access_token, ensure_org_access
from ..utils import from_json


def org_filter_sql(user: dict, organization_id: str | None, column: str = "organization_id") -> tuple[str, list]:
    params: list[Any] = []
    if organization_id:
        ensure_org_access(user, organization_id)
        return f" WHERE {column} = ? ", [organization_id]
    if user["global_role"] == "super_admin":
        return "", []
    org_ids = accessible_org_ids(user)
    if not org_ids:
        return " WHERE 1 = 0 ", []
    placeholders = ",".join("?" for _ in org_ids)
    return f" WHERE {column} IN ({placeholders}) ", org_ids


def bot_payload(conn, bot: dict) -> dict:
    number = get_whatsapp_number_for_bot(conn, bot["id"])
    versions = list_bot_versions(conn, bot["id"])
    payload = dict(bot)
    payload["config_draft"] = from_json(bot["config_draft_json"], {})
    payload["whatsapp_number"] = number
    payload["versions"] = versions
    return payload


def conversation_payload(conn, conversation: dict) -> dict:
    contact = get_contact(conn, conversation["contact_id"])
    memory = get_contact_memory(conn, conversation["contact_id"], conversation["bot_id"])
    bot = get_bot(conn, conversation["bot_id"])
    messages = fetch_all(
        conn,
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation["id"],),
    )
    tags = [row["tag"] for row in fetch_all(conn, "SELECT tag FROM conversation_tags WHERE conversation_id = ? ORDER BY tag ASC", (conversation["id"],))]
    latest_summary_row = fetch_one(conn, "SELECT * FROM conversation_summaries WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1", (conversation["id"],))
    cross_bot_memory = fetch_all(
        conn,
        """
        SELECT cm.*, b.name AS bot_name
        FROM contact_memory cm
        JOIN bots b ON b.id = cm.bot_id
        WHERE cm.contact_id = ? AND cm.organization_id = ?
        ORDER BY cm.last_updated_at DESC
        """,
        (conversation["contact_id"], conversation["organization_id"]),
    )
    return {
        "conversation": conversation,
        "contact": contact,
        "memory": memory,
        "bot": bot,
        "tags": tags,
        "latest_summary": from_json(latest_summary_row.get("content_json"), {}) if latest_summary_row else None,
        "cross_bot_memory": [{**row, "memory": from_json(row.get("memory_json"), {})} for row in cross_bot_memory],
        "messages": [{**m, "metadata": from_json(m.get("metadata_json"), {})} for m in messages],
    }


def normalize_memory(memory: dict | None) -> dict:
    if not memory:
        return {}
    return {**memory, "memory": from_json(memory.get("memory_json"), {})}


def permissions_matrix() -> dict[str, list[str]]:
    return {
        "super_admin": [
            "org.manage", "bot.manage", "conversation.manage", "appointment.manage",
            "release.request", "release.approve", "release.publish",
            "integration.manage", "integration.replay", "integration.fallback", "secret.manage", "rate_limit.manage",
            "audit.read", "security.manage", "runs.read", "logs.read",
            "scheduler.read", "operations.read", "operations.requeue", "client_view.read",
            "revenue.manage", "crm.manage", "insights.read", "playbooks.manage",
            "activation.manage", "quality.review", "portal.approve", "feedback.manage",
            "operations.control.read", "operations.control.execute", "operations.control.high_impact", "operations.control.schedule", "operations.control.undo", "operations.control.audit.read", "operations.chat.authorize_number",
        ],
        "org_admin": [
            "bot.manage", "conversation.manage", "appointment.manage",
            "release.request", "release.approve", "release.publish",
            "integration.manage", "integration.replay", "integration.fallback", "secret.manage", "rate_limit.manage",
            "audit.read", "security.manage", "runs.read", "logs.read",
            "scheduler.read", "operations.read", "operations.requeue", "client_view.read",
            "revenue.manage", "crm.manage", "insights.read", "playbooks.manage",
            "activation.manage", "quality.review", "portal.approve", "feedback.manage",
            "operations.control.read", "operations.control.execute", "operations.control.high_impact", "operations.control.schedule", "operations.control.undo", "operations.control.audit.read", "operations.chat.authorize_number",
        ],
        "operator": [
            "conversation.manage", "appointment.manage", "release.request",
            "runs.read", "logs.read", "scheduler.read", "operations.read", "operations.requeue", "crm.manage", "insights.read",
            "feedback.manage", "operations.control.read", "operations.control.execute", "operations.control.undo",
        ],
        "client": ["client_view.read", "runs.read", "insights.read", "operations.control.read", "operations.control.execute", "operations.control.undo", "operations.control.schedule", "operations.chat.authorize_number"],
    }


def org_role(user: dict, organization_id: str) -> str:
    if user["global_role"] == "super_admin":
        return "super_admin"
    for membership in user.get("memberships", []):
        if membership.get("organization_id") == organization_id:
            return membership.get("role") or user.get("global_role")
    return user.get("global_role")


def has_permission(user: dict, organization_id: str | None, permission: str) -> bool:
    if user["global_role"] == "super_admin":
        return True
    role = org_role(user, organization_id) if organization_id else user.get("global_role")
    return permission in permissions_matrix().get(role or "", [])


def require_permission(user: dict, organization_id: str | None, permission: str) -> None:
    if not has_permission(user, organization_id, permission):
        raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")


def client_ip(request: Request) -> str | None:
    direct_ip = request.client.host if request.client else None
    if not settings.trust_proxy_headers or not direct_ip:
        return direct_ip
    if direct_ip not in settings.trusted_proxy_ips:
        return direct_ip
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return direct_ip
    chain = [item.strip() for item in forwarded.split(",") if item.strip()]
    for candidate in chain:
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            continue
    return direct_ip


def enforce_ip_allowlist(policy: dict[str, Any], request: Request) -> None:
    allowlist = policy.get("ip_allowlist") or []
    if not allowlist:
        return
    source_ip = client_ip(request)
    if not source_ip:
        raise HTTPException(status_code=403, detail="IP not allowlisted")
    try:
        ip_obj = ipaddress.ip_address(source_ip)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="IP not allowlisted") from exc
    for item in allowlist:
        try:
            if "/" in str(item):
                if ip_obj in ipaddress.ip_network(str(item), strict=False):
                    return
            elif ip_obj == ipaddress.ip_address(str(item)):
                return
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="IP not allowlisted")


def issue_tokens(conn, *, user: dict, request: Request, ttl_minutes: int = 720, idle_timeout_minutes: int | None = None, max_sessions: int | None = None) -> dict:
    session = create_auth_session(
        conn,
        user=user,
        ttl_minutes=ttl_minutes,
        idle_timeout_minutes=idle_timeout_minutes,
        max_sessions=max_sessions,
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    access_token = create_access_token(user, session_id=session["id"], ttl_minutes=min(settings.access_token_ttl_minutes, ttl_minutes))
    return {
        "access_token": access_token,
        "refresh_token": session["refresh_token"],
        "token_type": "bearer",
        "session": {
            "id": session["id"],
            "expires_at": session["expires_at"],
            "status": session["status"],
            "max_idle_at": session.get("max_idle_at"),
        },
    }
