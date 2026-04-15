from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ..ai import run_ai_pipeline
from ..db import execute, fetch_one, table_exists
from ..domain_events import emit_domain_event
from ..platform import check_rate_limit
from ..repositories import create_audit_log, create_message, get_bot, get_contact, get_conversation, upsert_contact, upsert_conversation, upsert_memory
from ..utils import add_minutes, hash_value, new_id, utcnow_iso
from ..api.handlers.common import _apply_routing_rules, _detect_cancel_intent, _mark_followup_reply, _insert_notification


class InboundService:
    def _try_acquire_lock(self, conn, *, organization_id: str, bot_id: str, external_id: str | None, phone: str, body: str, correlation_id: str | None) -> dict[str, Any] | None:
        if not table_exists(conn, "inbound_message_locks"):
            return None
        lock_key = f"{organization_id}:{bot_id}:{external_id}" if external_id else f"{organization_id}:{bot_id}:{phone}:{hash_value(body)[:24]}"
        lock_id = new_id("inlock")
        try:
            execute(
                conn,
                "INSERT INTO inbound_message_locks (id, organization_id, bot_id, external_id, lock_key, status, correlation_id, metadata_json, acquired_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (lock_id, organization_id, bot_id, external_id, lock_key, "processing", correlation_id, "{}", utcnow_iso()),
            )
            return {"id": lock_id, "lock_key": lock_key, "deduplicated": False}
        except Exception:
            existing = fetch_one(conn, "SELECT * FROM inbound_message_locks WHERE lock_key = ?", (lock_key,))
            if existing:
                return {"id": existing["id"], "lock_key": lock_key, "deduplicated": True, "existing": existing}
            return None

    def _release_lock(self, conn, *, lock: dict[str, Any] | None, conversation_id: str | None, status: str) -> None:
        if not lock or not table_exists(conn, "inbound_message_locks"):
            return
        execute(conn, "UPDATE inbound_message_locks SET status = ?, conversation_id = ?, released_at = ? WHERE id = ?", (status, conversation_id, utcnow_iso(), lock["id"]))

    def handle_inbound(self, conn, *, bot_id: str, phone: str, name: str | None, body: str, external_id: str | None = None, correlation_id: str | None = None) -> dict[str, Any]:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        rate_limit = check_rate_limit(conn, organization_id=bot["organization_id"], bot_id=bot_id, phone=phone)
        if not rate_limit.get("allowed"):
            raise HTTPException(status_code=429, detail={"message": "Rate limit exceeded", "rate_limit": rate_limit})

        lock = self._try_acquire_lock(conn, organization_id=bot["organization_id"], bot_id=bot_id, external_id=external_id, phone=phone, body=body, correlation_id=correlation_id)
        if external_id:
            existing = fetch_one(conn, "SELECT * FROM messages WHERE external_id = ?", (external_id,))
            if existing:
                conversation = get_conversation(conn, existing["conversation_id"])
                contact = get_contact(conn, existing["contact_id"]) if existing.get("contact_id") else None
                self._release_lock(conn, lock=lock, conversation_id=existing["conversation_id"], status="completed")
                return {
                    "contact": contact,
                    "conversation": conversation,
                    "inbound_message": existing,
                    "ai": {"deduplicated": True, "reason": "external_id_already_processed"},
                }
        if lock and lock.get("deduplicated"):
            existing = fetch_one(conn, "SELECT * FROM messages WHERE external_id = ? ORDER BY created_at DESC LIMIT 1", (external_id,)) if external_id else None
            if existing:
                conversation = get_conversation(conn, existing["conversation_id"])
                contact = get_contact(conn, existing["contact_id"]) if existing.get("contact_id") else None
                return {
                    "contact": contact,
                    "conversation": conversation,
                    "inbound_message": existing,
                    "ai": {"deduplicated": True, "reason": "inbound_lock_already_present"},
                }

        contact = upsert_contact(conn, organization_id=bot["organization_id"], phone=phone, name=name)
        conversation = upsert_conversation(conn, organization_id=bot["organization_id"], bot_id=bot_id, contact_id=contact["id"])
        if conversation["status"] == "closed":
            execute(conn, "UPDATE conversations SET status = 'ai_active', ai_active = 1, updated_at = ? WHERE id = ?", (utcnow_iso(), conversation["id"]))
            conversation = get_conversation(conn, conversation["id"])
        memory = upsert_memory(conn, organization_id=bot["organization_id"], contact_id=contact["id"], bot_id=bot_id)
        inbound = create_message(
            conn,
            organization_id=bot["organization_id"],
            conversation_id=conversation["id"],
            contact_id=contact["id"],
            bot_id=bot_id,
            direction="inbound",
            kind="text",
            source="user",
            body=body,
            external_id=external_id,
            status="received",
            metadata={"channel": "whatsapp", "correlation_id": correlation_id},
            correlation_id=correlation_id,
        )
        execute(conn, "UPDATE conversations SET last_message_at = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), conversation["id"]))
        emit_domain_event(conn, event_name="inbound_received", organization_id=bot["organization_id"], bot_id=bot_id, conversation_id=conversation["id"], message_id=inbound["id"], correlation_id=correlation_id, payload={"external_id": external_id, "phone": phone})

        experiment_reply = _mark_followup_reply(conn, conversation_id=conversation["id"], inbound_message_id=inbound["id"])
        conversation = get_conversation(conn, conversation["id"])
        routing = _apply_routing_rules(conn, conversation=conversation, bot=bot, contact=contact, memory=memory, body=body)
        cancel_flags = _detect_cancel_intent(body)
        if cancel_flags:
            execute(
                conn,
                """
                UPDATE conversations
                SET status = 'human_takeover', human_takeover = 1, ai_active = 0, automation_freeze_until = ?, updated_at = ?
                WHERE id = ?
                """,
                (add_minutes(utcnow_iso(), 60), utcnow_iso(), conversation["id"]),
            )
            _insert_notification(
                conn,
                organization_id=conversation["organization_id"],
                bot_id=conversation["bot_id"],
                user_id=(routing or {}).get("assigned_user_id") or conversation.get("assigned_user_id"),
                conversation_id=conversation["id"],
                category="risk",
                title="Lead con intencion de cancelar",
                body=f"{contact.get('name') or contact.get('phone') or 'Lead'} mostro senales de salida: {', '.join(cancel_flags)}.",
                severity="critical",
                metadata={"cancel_flags": cancel_flags},
            )
            create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=None, actor_type="system", entity_type="conversation", entity_id=conversation["id"], action="conversation.cancel_intent_detected", metadata={"flags": cancel_flags})
            emit_domain_event(conn, event_name="handoff_triggered", organization_id=conversation["organization_id"], bot_id=conversation["bot_id"], conversation_id=conversation["id"], message_id=inbound["id"], correlation_id=correlation_id, payload={"reason": "cancel_intent_detected", "flags": cancel_flags})
            self._release_lock(conn, lock=lock, conversation_id=conversation["id"], status="completed")
            return {
                "contact": contact,
                "conversation": get_conversation(conn, conversation["id"]),
                "inbound_message": inbound,
                "ai": {"skipped": True, "reason": "cancel_intent_detected", "routing": routing, "cancel_flags": cancel_flags, "experiment_reply": experiment_reply},
            }
        if routing and routing.get("takeover_applied"):
            emit_domain_event(conn, event_name="handoff_triggered", organization_id=conversation["organization_id"], bot_id=conversation["bot_id"], conversation_id=conversation["id"], message_id=inbound["id"], correlation_id=correlation_id, payload={"reason": "routing_takeover", "routing": routing})
            self._release_lock(conn, lock=lock, conversation_id=conversation["id"], status="completed")
            return {
                "contact": contact,
                "conversation": get_conversation(conn, conversation["id"]),
                "inbound_message": inbound,
                "ai": {"skipped": True, "reason": "routing_takeover", "routing": routing, "experiment_reply": experiment_reply},
            }

        result = run_ai_pipeline(conn, incoming_message=inbound, conversation=conversation, bot=bot, contact=contact, memory=memory, correlation_id=correlation_id)
        if isinstance(result, dict):
            result["routing"] = routing
            result["experiment_reply"] = experiment_reply
        self._release_lock(conn, lock=lock, conversation_id=conversation["id"], status="completed")
        return {
            "contact": contact,
            "conversation": get_conversation(conn, conversation["id"]),
            "inbound_message": inbound,
            "ai": result,
        }


inbound_service = InboundService()
