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

def handle(service, uow: UnitOfWork, *, user: dict, conversation_id: str, freeze_minutes: int) -> dict:
    conn = uow.conn
    conversation = service._get_accessible_conversation(conn, user, conversation_id)
    require_permission(user, conversation["organization_id"], "conversation.manage")
    conn.execute(
        """
        UPDATE conversations
        SET status = 'human_takeover', human_takeover = 1, ai_active = 0, assigned_user_id = ?, automation_freeze_until = ?, updated_at = ?
        WHERE id = ?
        """,
        (user["id"], add_minutes(utcnow_iso(), freeze_minutes), utcnow_iso(), conversation_id),
    )
    build_takeover_brief(conn, conversation_id, brief_type="takeover", generated_by_user_id=user.get("id"), persist=True)
    create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.takeover", metadata={"freeze_minutes": freeze_minutes})
    return get_conversation(conn, conversation_id)
