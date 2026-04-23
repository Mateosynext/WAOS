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
    require_permission(user, conversation['organization_id'], 'conversation.manage')
    previous_user_id = conversation.get('assigned_user_id')
    target_user_id = payload.assigned_user_id
    queue_role = service._decorate_item(fetch_one(
        conn,
        """
        SELECT c.*, ct.name as contact_name, ct.phone as contact_phone, b.name as bot_name,
               cm.lead_stage, cm.lead_score, cm.summary, cm.memory_json, cm.next_action, cm.followup_at,
               cm.current_intent, cm.urgency_score AS memory_urgency_score, cm.urgency_level AS memory_urgency_level,
               (SELECT body FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) AS latest_message_preview,
               (SELECT MAX(created_at) FROM messages WHERE conversation_id = c.id AND direction = 'inbound') AS last_inbound_at,
               (SELECT MAX(created_at) FROM messages WHERE conversation_id = c.id AND direction = 'outbound') AS last_outbound_at,
               (SELECT COUNT(*) FROM appointments a WHERE a.conversation_id = c.id AND a.status NOT IN ('cancelled','no_show')) AS appointment_count,
               (SELECT COUNT(*) FROM commerce_payments p WHERE p.conversation_id = c.id AND p.status IN ('pending','pending_provider','requires_action')) AS pending_payment_count,
               (SELECT COALESCE(MAX(close_probability), 0) FROM crm_leads l WHERE l.conversation_id = c.id) AS close_probability,
               (SELECT COALESCE(MAX(score_buying_intent), 0) FROM crm_leads l WHERE l.conversation_id = c.id) AS score_buying_intent,
               (SELECT best_next_action FROM crm_leads l WHERE l.conversation_id = c.id ORDER BY updated_at DESC LIMIT 1) AS lead_best_next_action
        FROM conversations c
        JOIN contacts ct ON ct.id = c.contact_id
        JOIN bots b ON b.id = c.bot_id
        LEFT JOIN contact_memory cm ON cm.contact_id = c.contact_id AND cm.bot_id = c.bot_id
        WHERE c.id = ?
        LIMIT 1
        """,
        (conversation_id,),
    ) or {})['work_queue_role']
    if payload.mode == 'auto' and not target_user_id:
        candidates = service._org_assignment_candidates(conn, conversation['organization_id'], queue_role)
        target_user_id = (candidates[0] or {}).get('user_id') if candidates else None
    if target_user_id:
        membership = fetch_one(conn, 'SELECT * FROM organization_members WHERE organization_id = ? AND user_id = ? AND is_active = 1', (conversation['organization_id'], target_user_id))
        if not membership:
            raise HTTPException(status_code=404, detail='Assignee not found in organization')
    now = utcnow_iso()
    conn.execute(
        "UPDATE conversations SET assigned_user_id = ?, status = CASE WHEN ? IS NOT NULL THEN 'human_takeover' ELSE status END, human_takeover = CASE WHEN ? IS NOT NULL THEN 1 ELSE human_takeover END, updated_at = ? WHERE id = ?",
        (target_user_id, target_user_id, target_user_id, now, conversation_id),
    )
    service._record_assignment(conn, conversation=conversation, previous_user_id=previous_user_id, new_user_id=target_user_id, queue_role=queue_role, mode=payload.mode, note=payload.note, actor_user_id=user['id'])
    create_audit_log(conn, organization_id=conversation['organization_id'], actor_user_id=user['id'], actor_type='user', entity_type='conversation', entity_id=conversation_id, action='conversation.assigned', metadata={'assigned_user_id': target_user_id, 'previous_assigned_user_id': previous_user_id, 'queue_role': queue_role, 'mode': payload.mode, 'note': payload.note})
    return get_conversation(conn, conversation_id)
