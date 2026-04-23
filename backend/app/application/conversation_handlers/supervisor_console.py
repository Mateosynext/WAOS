from __future__ import annotations

from fastapi import HTTPException

from ...config import settings
from ...human_ops_runtime import build_human_reply_suggestion, build_supervisor_console, build_takeover_brief, detect_failed_takeover, qa_scorecard, recommend_ai_reactivation, save_structured_internal_note
from ...contracts import ok
from ...db import fetch_all, fetch_one, table_exists
from ...performance import clamp_limit, clamp_offset
from ...repositories import create_audit_log, create_message, get_bot, get_contact_memory, get_conversation
from ...security import ensure_bot_access, ensure_org_access
from ...serializers import serialize_conversation_details
from ...utils import add_minutes, from_json, new_id, to_json, utcnow_iso
from ...whatsapp import enqueue_manual_whatsapp_message
from ..conversation_presenters import decorate_conversation_item
from ..support import org_filter_sql, require_permission
from ..uow import UnitOfWork


from typing import Any

def handle(service, uow: UnitOfWork, *, user: dict, organization_id: str) -> dict:
    conn = uow.conn
    ensure_org_access(user, organization_id)
    require_permission(user, organization_id, "conversation.manage")
    payload = build_supervisor_console(conn, organization_id)
    if table_exists(conn, "supervisor_console_snapshots"):
        conn.execute(
            "INSERT INTO supervisor_console_snapshots (id, organization_id, summary_json, teams_json, qa_json, failed_takeovers_json, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id("supc"), organization_id, to_json(payload["summary"]), to_json(payload["teams"]), to_json(payload["qa"]), to_json(payload["failed_takeovers"]), user.get("id"), utcnow_iso()),
        )
    create_audit_log(conn, organization_id=organization_id, actor_user_id=user["id"], actor_type="user", entity_type="supervisor_console", entity_id=organization_id, action="supervisor.console_viewed", metadata={"teams": len(payload.get("teams") or [])})
    return ok(payload)
