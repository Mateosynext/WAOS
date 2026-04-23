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

def handle(service, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None) -> list[dict]:
    conn = uow.conn
    if organization_id:
        require_permission(user, organization_id, "crm.manage")
    where_sql, params = org_filter_sql(user, organization_id, "cm.organization_id")
    if not where_sql:
        where_sql = " WHERE 1 = 1 "
    if organization_id:
        require_permission(user, organization_id, "conversation.manage")
    if bot_id:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        where_sql += " AND cm.bot_id = ? "
        params.append(bot_id)
    return fetch_all(
        conn,
        f"""
        SELECT cm.*, ct.name as contact_name, ct.phone as contact_phone, b.name as bot_name
        FROM contact_memory cm
        JOIN contacts ct ON ct.id = cm.contact_id
        JOIN bots b ON b.id = cm.bot_id
        {where_sql}
        ORDER BY cm.lead_score DESC, cm.last_updated_at DESC
        """,
        params,
    )
