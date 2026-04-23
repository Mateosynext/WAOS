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
    require_permission(user, organization_id, 'conversation.manage')
    members = fetch_all(
        conn,
        """
        SELECT om.user_id, om.role, u.full_name,
               (
                 SELECT COUNT(*) FROM conversations c
                 WHERE c.organization_id = om.organization_id
                   AND c.assigned_user_id = om.user_id
                   AND c.status NOT IN ('closed','resolved')
               ) AS open_count,
               (
                 SELECT COUNT(*) FROM conversations c
                 WHERE c.organization_id = om.organization_id
                   AND c.assigned_user_id = om.user_id
                   AND c.status = 'human_takeover'
               ) AS human_takeover_count
        FROM organization_members om
        JOIN users u ON u.id = om.user_id
        WHERE om.organization_id = ? AND om.is_active = 1
        ORDER BY open_count DESC, u.full_name ASC
        """,
        (organization_id,),
    )
    unassigned = fetch_one(conn, "SELECT COUNT(*) AS value FROM conversations WHERE organization_id = ? AND assigned_user_id IS NULL AND status NOT IN ('closed','resolved')", (organization_id,))
    return ok({'organization_id': organization_id, 'unassigned_open': int((unassigned or {}).get('value') or 0), 'owners': members})
