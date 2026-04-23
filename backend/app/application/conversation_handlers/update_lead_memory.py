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

def handle(service, uow: UnitOfWork, *, user: dict, contact_id: str, bot_id: str, payload) -> dict:
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
