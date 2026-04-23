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
    try:
        queued = enqueue_manual_whatsapp_message(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=conversation["bot_id"],
            conversation_id=conversation_id,
            contact_id=conversation["contact_id"],
            body=payload.body,
            author_user_id=user["id"],
            whatsapp_payload=payload.whatsapp_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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
            (queued.get("message") or {}).get("body") or payload.body or "",
            to_json({"latest_inbound_at": latest_inbound.get("created_at") if latest_inbound else None}),
            utcnow_iso(),
        ),
    )
    create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.manual_message_queued", metadata={"outbox_id": queued["outbox_id"], "training_example_captured": True})
    return {"message": queued["message"], "outbox_id": queued["outbox_id"], "conversation": get_conversation(conn, conversation_id)}
