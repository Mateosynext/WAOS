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

def handle(service, uow: UnitOfWork, *, user: dict, conversation_id: str, payload) -> dict:
    conn = uow.conn
    conversation = service._get_accessible_conversation(conn, user, conversation_id)
    require_permission(user, conversation["organization_id"], "conversation.manage")
    note = save_structured_internal_note(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=conversation["bot_id"],
        conversation_id=conversation_id,
        contact_id=conversation["contact_id"],
        author_user_id=user["id"],
        category=payload.category,
        priority=payload.priority,
        summary=payload.summary,
        detail=payload.detail,
        next_steps=payload.next_steps,
        sources=payload.sources,
        risk_level=payload.risk_level,
        risk_flags=payload.risk_flags,
        visibility=payload.visibility,
    )
    return ok(note)
