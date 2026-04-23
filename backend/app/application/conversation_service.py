from __future__ import annotations

from fastapi import HTTPException

from ..config import settings
from ..human_ops_runtime import build_human_reply_suggestion, build_supervisor_console, build_takeover_brief, detect_failed_takeover, qa_scorecard, recommend_ai_reactivation, save_structured_internal_note
from ..contracts import ok
from ..db import fetch_all, fetch_one, table_exists
from ..performance import clamp_limit, clamp_offset
from ..repositories import create_audit_log, create_message, get_bot, get_contact_memory, get_conversation
from ..security import ensure_bot_access, ensure_org_access
from ..serializers import serialize_conversation_details
from ..utils import add_minutes, from_json, new_id, to_json, utcnow_iso
from ..whatsapp import enqueue_manual_whatsapp_message
from .conversation_presenters import decorate_conversation_item
from .support import org_filter_sql, require_permission
from .uow import UnitOfWork


class ConversationService:
    def _base_list_rows(self, conn, *, user: dict, organization_id: str | None, bot_id: str | None, status: str | None, sort: str | None, limit: int, offset: int) -> list[dict]:
        where_sql, params = org_filter_sql(user, organization_id, "c.organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if organization_id:
            require_permission(user, organization_id, "conversation.manage")
        if bot_id:
            bot = get_bot(conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            ensure_bot_access(user, bot)
            where_sql += " AND c.bot_id = ? "
            params.append(bot_id)
        if status:
            where_sql += " AND c.status = ? "
            params.append(status)
        order_by = "COALESCE(c.last_message_at, c.updated_at) DESC"
        if str(sort or "").lower() == "priority":
            order_by = "COALESCE(cm.urgency_score, 0) DESC, COALESCE(cm.lead_score, 0) DESC, COALESCE(c.last_message_at, c.updated_at) DESC"
        elif str(sort or "").lower() == "lead":
            order_by = "COALESCE(cm.lead_score, 0) DESC, COALESCE(c.last_message_at, c.updated_at) DESC"
        elif str(sort or "").lower() == "urgency":
            order_by = "COALESCE(cm.urgency_score, 0) DESC, COALESCE(c.last_message_at, c.updated_at) DESC"
        return fetch_all(
            conn,
            f"""
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
            {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            params + [clamp_limit(limit), clamp_offset(offset)],
        )

    def _decorate_item(self, item: dict) -> dict:
        return decorate_conversation_item(item)

    def list(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None, status: str | None, sort: str | None, limit: int, offset: int) -> list[dict]:
        from .conversation_handlers.list import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id, bot_id=bot_id, status=status, sort=sort, limit=limit, offset=offset)


    def get(self, uow: UnitOfWork, *, user: dict, conversation_id: str) -> dict:
        from .conversation_handlers.get import handle as _handle
        return _handle(self, uow=uow, user=user, conversation_id=conversation_id)


    def decision_support(self, uow: UnitOfWork, *, user: dict, conversation_id: str) -> dict:
        from .conversation_handlers.decision_support import handle as _handle
        return _handle(self, uow=uow, user=user, conversation_id=conversation_id)


    def list_work_queues(self, uow: UnitOfWork, *, user: dict, organization_id: str) -> dict:
        from .conversation_handlers.list_work_queues import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id)


    def _org_assignment_candidates(self, conn, organization_id: str, queue_role: str) -> list[dict]:
        rows = fetch_all(
            conn,
            """
            SELECT om.user_id, om.role, u.full_name, u.email,
                   (
                     SELECT COUNT(*) FROM conversations c
                     WHERE c.organization_id = om.organization_id
                       AND c.assigned_user_id = om.user_id
                       AND c.status NOT IN ('closed','resolved')
                   ) AS open_conversations
            FROM organization_members om
            JOIN users u ON u.id = om.user_id
            WHERE om.organization_id = ? AND om.is_active = 1 AND u.is_active = 1
            ORDER BY open_conversations ASC, om.created_at ASC
            """,
            (organization_id,),
        )
        preferred_roles = {
            'ventas': {'org_admin', 'operator'},
            'agenda': {'org_admin', 'operator'},
            'cobranza': {'org_admin'},
            'soporte': {'org_admin', 'operator'},
        }.get(queue_role, {'org_admin', 'operator'})
        filtered = [row for row in rows if str(row.get('role') or '').lower() in preferred_roles]
        return filtered or rows

    def _record_assignment(self, conn, *, conversation: dict, previous_user_id: str | None, new_user_id: str | None, queue_role: str | None, mode: str, note: str, actor_user_id: str) -> None:
        if not table_exists(conn, 'conversation_assignment_history'):
            return
        conn.execute(
            """
            INSERT INTO conversation_assignment_history (id, organization_id, conversation_id, previous_assigned_user_id, new_assigned_user_id, queue_role, assignment_mode, reasoning_json, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id('casg'),
                conversation['organization_id'],
                conversation['id'],
                previous_user_id,
                new_user_id,
                queue_role,
                mode,
                to_json({'note': note}),
                actor_user_id,
                utcnow_iso(),
            ),
        )

    def assign(self, uow: UnitOfWork, *, user: dict, conversation_id: str, payload) -> dict:
        from .conversation_handlers.assign import handle as _handle
        return _handle(self, uow=uow, user=user, conversation_id=conversation_id, payload=payload)


    def auto_assign(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        from .conversation_handlers.auto_assign import handle as _handle
        return _handle(self, uow=uow, user=user, payload=payload)


    def ownership_summary(self, uow: UnitOfWork, *, user: dict, organization_id: str) -> dict:
        from .conversation_handlers.ownership_summary import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id)


    def add_message_or_note(self, uow: UnitOfWork, *, user: dict, conversation_id: str, payload) -> dict:
        from .conversation_handlers.add_message_or_note import handle as _handle
        return _handle(self, uow=uow, user=user, conversation_id=conversation_id, payload=payload)


    def takeover(self, uow: UnitOfWork, *, user: dict, conversation_id: str, freeze_minutes: int) -> dict:
        from .conversation_handlers.takeover import handle as _handle
        return _handle(self, uow=uow, user=user, conversation_id=conversation_id, freeze_minutes=freeze_minutes)


    def reactivate_ai(self, uow: UnitOfWork, *, user: dict, conversation_id: str) -> dict:
        from .conversation_handlers.reactivate_ai import handle as _handle
        return _handle(self, uow=uow, user=user, conversation_id=conversation_id)


    def add_structured_internal_note(self, uow: UnitOfWork, *, user: dict, conversation_id: str, payload) -> dict:
        from .conversation_handlers.add_structured_internal_note import handle as _handle
        return _handle(self, uow=uow, user=user, conversation_id=conversation_id, payload=payload)


    def takeover_brief(self, uow: UnitOfWork, *, user: dict, conversation_id: str, brief_type: str = 'takeover') -> dict:
        from .conversation_handlers.takeover_brief import handle as _handle
        return _handle(self, uow=uow, user=user, conversation_id=conversation_id, brief_type=brief_type)


    def supervisor_console(self, uow: UnitOfWork, *, user: dict, organization_id: str) -> dict:
        from .conversation_handlers.supervisor_console import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id)


    def qa_overview(self, uow: UnitOfWork, *, user: dict, organization_id: str, bot_id: str | None = None) -> dict:
        from .conversation_handlers.qa_overview import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id, bot_id=bot_id)


    def list_leads(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None) -> list[dict]:
        from .conversation_handlers.list_leads import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id, bot_id=bot_id)


    def update_lead_memory(self, uow: UnitOfWork, *, user: dict, contact_id: str, bot_id: str, payload) -> dict:
        from .conversation_handlers.update_lead_memory import handle as _handle
        return _handle(self, uow=uow, user=user, contact_id=contact_id, bot_id=bot_id, payload=payload)


    def _get_accessible_conversation(self, conn, user: dict, conversation_id: str) -> dict:
        conversation = get_conversation(conn, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        ensure_org_access(user, conversation["organization_id"])
        return conversation
