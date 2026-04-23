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

def handle(service, uow: UnitOfWork, *, user: dict, payload) -> dict:
    conn = uow.conn
    ensure_org_access(user, payload.organization_id)
    require_permission(user, payload.organization_id, 'conversation.manage')
    rows = service._base_list_rows(conn, user=user, organization_id=payload.organization_id, bot_id=None, status=None, sort='priority', limit=payload.limit, offset=0)
    assigned = []
    for row in rows:
        item = service._decorate_item(row)
        if item.get('assigned_user_id'):
            continue
        if payload.queue_role and str(item.get('work_queue_role') or '') != str(payload.queue_role):
            continue
        candidates = service._org_assignment_candidates(conn, payload.organization_id, item['work_queue_role'])
        if not candidates:
            continue
        target_user_id = candidates[0].get('user_id')
        conn.execute(
            "UPDATE conversations SET assigned_user_id = ?, status = 'human_takeover', human_takeover = 1, updated_at = ? WHERE id = ?",
            (target_user_id, utcnow_iso(), item['id']),
        )
        service._record_assignment(conn, conversation=item, previous_user_id=item.get('assigned_user_id'), new_user_id=target_user_id, queue_role=item.get('work_queue_role'), mode='auto', note='bulk auto assignment', actor_user_id=user['id'])
        assigned.append({'conversation_id': item['id'], 'assigned_user_id': target_user_id, 'queue_role': item.get('work_queue_role'), 'priority_score': item.get('priority_score')})
    create_audit_log(conn, organization_id=payload.organization_id, actor_user_id=user['id'], actor_type='user', entity_type='inbox', entity_id=payload.organization_id, action='inbox.auto_assign', metadata={'assigned_count': len(assigned), 'queue_role': payload.queue_role, 'limit': payload.limit})
    return ok({'organization_id': payload.organization_id, 'assigned_count': len(assigned), 'assignments': assigned})
