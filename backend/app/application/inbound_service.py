from __future__ import annotations

from typing import Any
import time

from fastapi import HTTPException

from ..ai import run_ai_pipeline
from ..db import execute, fetch_one, table_exists
from ..domain_events import emit_domain_event
from ..platform import check_rate_limit
from ..rate_limiter import defensive_limit_status, inbound_client_rate_limit
from ..voice_pipeline import voice_pipeline_service
from ..repositories import create_audit_log, create_message, get_bot, get_contact, get_conversation, upsert_contact, upsert_conversation, upsert_memory
from ..utils import add_minutes, hash_value, new_id, utcnow_iso
from ..telemetry_runtime import record_stage_metric
from ..world_class import finish_trace_span, start_trace_span
from ..api.handlers.common import _apply_routing_rules, _detect_cancel_intent, _mark_followup_reply, _insert_notification
from ..whatsapp import enqueue_manual_whatsapp_message
from ..whatsapp_safety import is_opt_out_request, register_opt_out
from .operational_control_service import operational_control_service


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

    def handle_inbound(self, conn, *, bot_id: str, phone: str, name: str | None, body: str, external_id: str | None = None, correlation_id: str | None = None, kind: str = 'text', source: str = 'user', metadata: dict[str, Any] | None = None, apply_defensive_rate_limit: bool = True) -> dict[str, Any]:
        inbound_started = time.perf_counter()
        trace_id = correlation_id or new_id("trace")
        intake_span_id = new_id("span")
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        if apply_defensive_rate_limit:
            defensive_limit = inbound_client_rate_limit(
                conn,
                organization_id=bot["organization_id"],
                bot_id=bot_id,
                phone=phone,
                metadata={"path": "inbound.whatsapp", "external_id": external_id, "correlation_id": correlation_id},
            )
            if not defensive_limit.get("allowed"):
                raise HTTPException(status_code=429, detail={"message": "Inbound spam protection triggered", "rate_limit": defensive_limit_status(defensive_limit)})

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

        start_trace_span(
            conn,
            trace_id=trace_id,
            span_id=intake_span_id,
            parent_span_id=None,
            name="whatsapp.inbound",
            organization_id=bot["organization_id"],
            bot_id=bot_id,
            conversation_id=None,
            correlation_id=correlation_id,
            attributes={"channel": "whatsapp", "kind": kind or "text", "source": source or "user"},
        )
        contact = upsert_contact(conn, organization_id=bot["organization_id"], phone=phone, name=name)
        conversation = upsert_conversation(conn, organization_id=bot["organization_id"], bot_id=bot_id, contact_id=contact["id"])
        if conversation["status"] == "closed":
            execute(conn, "UPDATE conversations SET status = 'ai_active', ai_active = 1, updated_at = ? WHERE id = ?", (utcnow_iso(), conversation["id"]))
            conversation = get_conversation(conn, conversation["id"])
        memory = upsert_memory(conn, organization_id=bot["organization_id"], contact_id=contact["id"], bot_id=bot_id)
        inbound_metadata = {"channel": "whatsapp", **(metadata or {})}
        if correlation_id:
            inbound_metadata.setdefault("correlation_id", correlation_id)
        inbound = create_message(
            conn,
            organization_id=bot["organization_id"],
            conversation_id=conversation["id"],
            contact_id=contact["id"],
            bot_id=bot_id,
            direction="inbound",
            kind=kind or "text",
            source=source or "user",
            body=body,
            external_id=external_id,
            status="received",
            metadata=inbound_metadata,
            correlation_id=correlation_id,
        )
        if (kind or "text") == "audio" or inbound_metadata.get("is_voice_note"):
            voice_result = voice_pipeline_service.process_inbound_voice_message(
                conn,
                organization_id=bot["organization_id"],
                bot_id=bot_id,
                conversation_id=conversation["id"],
                contact_id=contact.get("id"),
                inbound_message=inbound,
                metadata=inbound_metadata,
                preferred_transcript=body,
            )
            if voice_result and voice_result.get("processed") and voice_result.get("message"):
                inbound = voice_result["message"]
                body = inbound.get("body") or body
        execute(conn, "UPDATE conversations SET last_message_at = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), conversation["id"]))
        emit_domain_event(conn, event_name="inbound_received", organization_id=bot["organization_id"], bot_id=bot_id, conversation_id=conversation["id"], message_id=inbound["id"], correlation_id=correlation_id, payload={"external_id": external_id, "phone": phone})

        if is_opt_out_request(body):
            opt_out = register_opt_out(
                conn,
                organization_id=bot["organization_id"],
                bot_id=bot_id,
                contact_id=contact.get("id"),
                conversation_id=conversation.get("id"),
                phone=phone,
                source_message_id=inbound.get("id"),
                keyword=body,
            )
            confirmation = enqueue_manual_whatsapp_message(
                conn,
                organization_id=bot["organization_id"],
                bot_id=bot_id,
                conversation_id=conversation["id"],
                contact_id=contact.get("id"),
                body="Has sido dado de baja. Ya no te enviaremos mensajes automáticos por WhatsApp.",
                author_user_id=None,
            )
            emit_domain_event(conn, event_name="whatsapp_opt_out_registered", organization_id=bot["organization_id"], bot_id=bot_id, conversation_id=conversation["id"], message_id=inbound["id"], correlation_id=correlation_id, payload={"contact_id": contact.get("id"), "opt_out_id": opt_out.get("id")})
            self._release_lock(conn, lock=lock, conversation_id=conversation["id"], status="completed")
            return {
                "contact": contact,
                "conversation": get_conversation(conn, conversation["id"]),
                "inbound_message": inbound,
                "ai": {"skipped": True, "reason": "opt_out_registered", "opt_out": opt_out, "confirmation_outbox_id": confirmation.get("outbox_id")},
            }

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

        operational = operational_control_service.handle_chat_command(
            conn,
            bot_id=bot_id,
            phone=phone,
            body=body,
            conversation_id=conversation["id"],
            contact_id=contact.get("id"),
            inbound_message_id=inbound.get("id"),
            external_id=external_id,
            correlation_id=correlation_id,
        )
        if operational and operational.get("handled"):
            outbound = create_message(
                conn,
                organization_id=bot["organization_id"],
                conversation_id=conversation["id"],
                contact_id=contact.get("id"),
                bot_id=bot_id,
                direction="outbound",
                kind="text",
                source="system",
                body=operational.get("reply_text") or "Comando operativo procesado.",
                status="queued",
                metadata={"channel": "whatsapp", "category": "operational_control"},
                correlation_id=correlation_id,
            )
            emit_domain_event(conn, event_name="operational_command_handled", organization_id=conversation["organization_id"], bot_id=conversation["bot_id"], conversation_id=conversation["id"], message_id=outbound["id"], correlation_id=correlation_id, payload={"status": operational.get("status")})
            self._release_lock(conn, lock=lock, conversation_id=conversation["id"], status="completed")
            return {
                "contact": contact,
                "conversation": get_conversation(conn, conversation["id"]),
                "inbound_message": inbound,
                "ai": {"skipped": True, "reason": "operational_command", "operational": operational, "routing": routing, "experiment_reply": experiment_reply},
            }

        result = run_ai_pipeline(conn, incoming_message=inbound, conversation=conversation, bot=bot, contact=contact, memory=memory, correlation_id=trace_id)
        if isinstance(result, dict):
            voice_reply = voice_pipeline_service.orchestrate_ai_reply(
                conn,
                organization_id=bot["organization_id"],
                bot_id=bot_id,
                conversation_id=conversation["id"],
                contact_id=contact.get("id"),
                inbound_message=inbound,
                ai_result=result,
            )
            if voice_reply:
                result["voice_reply"] = voice_reply
                if voice_reply.get("response_message"):
                    result["response_message"] = voice_reply["response_message"]
            result["routing"] = routing
            result["experiment_reply"] = experiment_reply
        self._release_lock(conn, lock=lock, conversation_id=conversation["id"], status="completed")
        intake_duration_ms = int((time.perf_counter() - inbound_started) * 1000)
        finish_trace_span(conn, trace_id=trace_id, span_id=intake_span_id, status="ok", attributes={"duration_ms": intake_duration_ms, "stage": "whatsapp.inbound"})
        record_stage_metric(
            conn,
            organization_id=bot["organization_id"],
            bot_id=bot_id,
            conversation_id=conversation["id"],
            trace_id=trace_id,
            correlation_id=correlation_id,
            vertical=bot.get("vertical"),
            source_type="whatsapp_webhook",
            stage_name="whatsapp.inbound",
            duration_ms=intake_duration_ms,
            metrics={"kind": kind or "text", "source": source or "user"},
        )
        return {
            "contact": contact,
            "conversation": get_conversation(conn, conversation["id"]),
            "inbound_message": inbound,
            "ai": result,
        }


inbound_service = InboundService()
