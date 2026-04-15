from __future__ import annotations

from fastapi import HTTPException

from ..config import settings
from ..contact_intelligence import enrich_conversation_row
from ..db import fetch_all, fetch_one
from ..performance import clamp_limit, clamp_offset
from ..repositories import create_audit_log, create_message, get_bot, get_contact_memory, get_conversation
from ..security import ensure_bot_access, ensure_org_access
from ..serializers import serialize_conversation_details
from ..utils import add_minutes, new_id, to_json, utcnow_iso
from ..whatsapp import enqueue_manual_whatsapp_message
from .support import org_filter_sql, require_permission
from .uow import UnitOfWork


class ConversationService:
    def list(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None, status: str | None, limit: int, offset: int) -> list[dict]:
        conn = uow.conn
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
        rows = fetch_all(
            conn,
            f"""
            SELECT c.*, ct.name as contact_name, ct.phone as contact_phone, b.name as bot_name, cm.lead_stage, cm.lead_score, cm.summary, cm.memory_json
            FROM conversations c
            JOIN contacts ct ON ct.id = c.contact_id
            JOIN bots b ON b.id = c.bot_id
            LEFT JOIN contact_memory cm ON cm.contact_id = c.contact_id AND cm.bot_id = c.bot_id
            {where_sql}
            ORDER BY COALESCE(c.last_message_at, c.updated_at) DESC
            LIMIT ? OFFSET ?
            """,
            params + [clamp_limit(limit), clamp_offset(offset)],
        )
        return [enrich_conversation_row(row) for row in rows]

    def get(self, uow: UnitOfWork, *, user: dict, conversation_id: str) -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
        require_permission(user, conversation["organization_id"], "conversation.manage")
        return serialize_conversation_details(conn, conversation)

    def add_message_or_note(self, uow: UnitOfWork, *, user: dict, conversation_id: str, payload) -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
        require_permission(user, conversation["organization_id"], "conversation.manage")
        if payload.kind == "note":
            message = create_message(
                conn,
                organization_id=conversation["organization_id"],
                conversation_id=conversation_id,
                contact_id=conversation["contact_id"],
                bot_id=conversation["bot_id"],
                direction="internal",
                kind="note",
                source="human",
                body=payload.body,
                status="internal",
                metadata={"author_user_id": user["id"]},
            )
            create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.note_added", metadata={})
            return {"message": message}
        queued = enqueue_manual_whatsapp_message(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=conversation["bot_id"],
            conversation_id=conversation_id,
            contact_id=conversation["contact_id"],
            body=payload.body,
            author_user_id=user["id"],
        )
        now = utcnow_iso()
        conn.execute(
            """
            UPDATE conversations
            SET status = 'human_takeover', human_takeover = 1, ai_active = 0, assigned_user_id = ?, last_human_at = ?, automation_freeze_until = ?, updated_at = ?
            WHERE id = ?
            """,
            (user["id"], now, add_minutes(now, 30), now, conversation_id),
        )
        latest_inbound = fetch_one(conn, "SELECT body, created_at FROM messages WHERE conversation_id = ? AND direction = 'inbound' ORDER BY created_at DESC LIMIT 1", (conversation_id,))
        conn.execute(
            """
            INSERT INTO operator_training_examples (id, organization_id, bot_id, conversation_id, contact_id, operator_user_id, input_text, output_text, example_type, status, context_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'manual_takeover', 'captured', ?, ?)
            """,
            (
                new_id("otrain"),
                conversation["organization_id"],
                conversation["bot_id"],
                conversation_id,
                conversation["contact_id"],
                user["id"],
                latest_inbound.get("body") if latest_inbound else None,
                payload.body,
                to_json({"latest_inbound_at": latest_inbound.get("created_at") if latest_inbound else None}),
                utcnow_iso(),
            ),
        )
        create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.manual_message_queued", metadata={"outbox_id": queued["outbox_id"], "training_example_captured": True})
        return {"message": queued["message"], "outbox_id": queued["outbox_id"], "conversation": get_conversation(conn, conversation_id)}

    def takeover(self, uow: UnitOfWork, *, user: dict, conversation_id: str, freeze_minutes: int) -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
        require_permission(user, conversation["organization_id"], "conversation.manage")
        conn.execute(
            """
            UPDATE conversations
            SET status = 'human_takeover', human_takeover = 1, ai_active = 0, assigned_user_id = ?, automation_freeze_until = ?, updated_at = ?
            WHERE id = ?
            """,
            (user["id"], add_minutes(utcnow_iso(), freeze_minutes), utcnow_iso(), conversation_id),
        )
        create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.takeover", metadata={"freeze_minutes": freeze_minutes})
        return get_conversation(conn, conversation_id)

    def reactivate_ai(self, uow: UnitOfWork, *, user: dict, conversation_id: str) -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
        require_permission(user, conversation["organization_id"], "conversation.manage")
        conn.execute(
            """
            UPDATE conversations
            SET status = 'ai_active', human_takeover = 0, ai_active = 1, assigned_user_id = NULL, updated_at = ?
            WHERE id = ?
            """,
            (utcnow_iso(), conversation_id),
        )
        create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.ai_reactivated", metadata={})
        return get_conversation(conn, conversation_id)

    def list_leads(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None) -> list[dict]:
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

    def update_lead_memory(self, uow: UnitOfWork, *, user: dict, contact_id: str, bot_id: str, payload) -> dict:
        conn = uow.conn
        memory = get_contact_memory(conn, contact_id, bot_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        ensure_org_access(user, memory["organization_id"])
        require_permission(user, memory["organization_id"], "crm.manage")
        updated = {
            "lead_stage": payload.lead_stage if payload.lead_stage is not None else memory["lead_stage"],
            "lead_score": payload.lead_score if payload.lead_score is not None else memory["lead_score"],
            "interest": payload.interest if payload.interest is not None else memory["interest"],
            "objections": payload.objections if payload.objections is not None else memory["objections"],
            "summary": payload.summary if payload.summary is not None else memory["summary"],
            "next_action": payload.next_action if payload.next_action is not None else memory["next_action"],
            "followup_at": payload.followup_at if payload.followup_at is not None else memory["followup_at"],
        }
        conn.execute(
            """
            UPDATE contact_memory
            SET lead_stage = ?, lead_score = ?, interest = ?, objections = ?, summary = ?, next_action = ?, followup_at = ?, last_updated_at = ?
            WHERE contact_id = ? AND bot_id = ?
            """,
            (
                updated["lead_stage"],
                updated["lead_score"],
                updated["interest"],
                updated["objections"],
                updated["summary"],
                updated["next_action"],
                updated["followup_at"],
                utcnow_iso(),
                contact_id,
                bot_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO contact_memory_history (id, organization_id, contact_memory_id, contact_id, bot_id, changed_by, before_json, after_json, changed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("memh"),
                memory["organization_id"],
                memory["id"],
                contact_id,
                bot_id,
                user["id"],
                to_json({
                    "lead_stage": memory.get("lead_stage"),
                    "lead_score": memory.get("lead_score"),
                    "interest": memory.get("interest"),
                    "objections": memory.get("objections"),
                    "summary": memory.get("summary"),
                    "next_action": memory.get("next_action"),
                    "followup_at": memory.get("followup_at"),
                }),
                to_json(updated),
                utcnow_iso(),
            ),
        )
        create_audit_log(conn, organization_id=memory["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="contact_memory", entity_id=memory["id"], action="lead.memory_updated", metadata=updated)
        return get_contact_memory(conn, contact_id, bot_id)

    def _get_accessible_conversation(self, conn, user: dict, conversation_id: str) -> dict:
        conversation = get_conversation(conn, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        ensure_org_access(user, conversation["organization_id"])
        return conversation
