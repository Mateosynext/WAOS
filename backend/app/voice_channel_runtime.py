from __future__ import annotations

import re
from typing import Any

from .agent_policy_runtime import evaluate_specialist_policy
from .domains.customer_experience import ingest_voice_note
from .multi_agent_runtime import build_shared_memory_context, route_intent_to_specialist
from .repositories.conversations import create_message, get_conversation, upsert_conversation
from .repositories.voice_channels import (
    create_handoff as repo_create_handoff,
    create_session as repo_create_session,
    create_turn as repo_create_turn,
    get_turn as repo_get_turn,
    interrupt_active_assistant_turn as repo_interrupt_active_assistant_turn,
    list_recent_conversation_messages as repo_list_recent_conversation_messages,
    list_session_rows as repo_list_session_rows,
    load_bot as repo_load_bot,
    load_handoffs as repo_load_handoffs,
    load_recent_contact_memory as repo_load_recent_contact_memory,
    load_session as repo_load_session,
    load_turns as repo_load_turns,
    mark_session_handoff as repo_mark_session_handoff,
    next_turn_index as repo_next_turn_index,
    update_session_after_turn as repo_update_session_after_turn,
    update_session_state as repo_update_session_state,
    update_voice_note_urgency as repo_update_voice_note_urgency,
)
from .utils import from_json, new_id, to_json, utcnow_iso
from .voice_pipeline import voice_pipeline_service
from .runtime_schema_guards import assert_schema_ready

VOICE_SURFACE_VERSION = "voice_channel_v1"


def ensure_voice_channel_schema(conn) -> None:
    assert_schema_ready(
        conn,
        owner="voice_channel_runtime",
        tables=("voice_channel_sessions", "voice_channel_turns", "voice_channel_handoffs"),
    )


def _normalize(text: str | None) -> str:
    return str(text or "").strip().lower()


def _detect_intent(text: str) -> str:
    lower = _normalize(text)
    if any(token in lower for token in ("reagendar", "mover la cita", "cambiar la cita")):
        return "reschedule"
    if any(token in lower for token in ("cita", "agenda", "agendar", "horario", "disponibilidad")):
        return "schedule"
    if any(token in lower for token in ("pago", "cobro", "factura", "link", "tarjeta", "adeudo")):
        return "payment"
    if any(token in lower for token in ("precio", "cotizacion", "cotización", "promo", "plan")):
        return "pricing"
    if any(token in lower for token in ("cancelar", "cancelación", "baja", "ya no", "reembolso")):
        return "cancel"
    if any(token in lower for token in ("ayuda", "soporte", "problema", "error", "no funciona", "queja")):
        return "support"
    return "general"


def _detect_urgency(text: str) -> tuple[str, int]:
    lower = _normalize(text)
    if any(token in lower for token in ("urgente", "emergencia", "ahora", "ya", "hoy mismo", "inmediato")):
        return "high", 90
    if any(token in lower for token in ("pronto", "hoy", "cuanto antes", "pendiente")):
        return "medium", 60
    return "normal", 25


def _requested_human(text: str) -> bool:
    lower = _normalize(text)
    return any(token in lower for token in ("humano", "persona", "asesor", "agente", "operador", "llamame", "llámame"))


def _extract_entities(text: str) -> dict[str, Any]:
    raw = str(text or "")
    lower = raw.lower()
    phones = re.findall(r"(?:\+?\d[\d\s\-]{7,}\d)", raw)
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", raw)
    amounts = [match.group(0) for match in re.finditer(r"(?:\$|mxn\s?)?\d{2,6}(?:\.\d{1,2})?", lower)]
    dates = [token for token in ("hoy", "mañana", "lunes", "martes", "miercoles", "miércoles", "jueves", "viernes", "sábado", "sabado", "domingo") if token in lower]
    return {
        "phones": phones,
        "emails": emails,
        "amount_mentions": amounts[:3],
        "date_mentions": dates,
        "has_payment_reference": any(token in lower for token in ("pago", "cobro", "factura", "link")),
        "has_appointment_reference": any(token in lower for token in ("cita", "agenda", "reagendar", "horario")),
    }


def _next_turn_index(conn, session_id: str) -> int:
    return repo_next_turn_index(conn, session_id)


def _serialize_messages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row) if not isinstance(row, dict) else dict(row)
        payload["metadata"] = from_json(payload.get("metadata_json"), {})
        items.append(payload)
    return items


def _load_session(conn, session_id: str) -> dict[str, Any] | None:
    return repo_load_session(conn, session_id)


def _load_turns(conn, session_id: str) -> list[dict[str, Any]]:
    return repo_load_turns(conn, session_id)


def _load_handoffs(conn, session_id: str) -> list[dict[str, Any]]:
    return repo_load_handoffs(conn, session_id)


def _interrupt_active_assistant_turn(conn, session: dict[str, Any], reason: str) -> dict[str, Any] | None:
    return repo_interrupt_active_assistant_turn(conn, session=session, reason=reason)


def _response_text_for_route(*, transcript: str, route: dict[str, Any], shared_memory: dict[str, Any], urgency_level: str) -> str:
    specialist = route.get("specialist_agent_key") or "general"
    prefix = "Lo atiendo de inmediato. " if urgency_level == "high" else ""
    if specialist == "booking":
        latest = (shared_memory.get("appointments") or [{}])[0]
        if latest and latest.get("scheduled_for"):
            return prefix + f"Ya vi tu contexto de cita. Puedo ayudarte a confirmar o mover tu cita programada para {latest.get('scheduled_for')}. ¿Prefieres mantenerla o reagendarla?"
        return prefix + "Te ayudo con tu cita. Tengo tu contexto listo y puedo proponerte horarios o reagendar en este mismo flujo."
    if specialist == "sales":
        lead = (shared_memory.get("leads") or [{}])[0]
        if lead and lead.get("estimated_amount"):
            return prefix + f"Te ayudo con la parte comercial. Con tu contexto actual puedo avanzar una propuesta y resolver objeciones para acercarte al cierre."
        return prefix + "Te ayudo con precio, propuesta y siguiente paso para avanzar esta venta sin salir del flujo."
    if specialist == "collections":
        payment = (shared_memory.get("payments") or [{}])[0]
        if payment and payment.get("status"):
            return prefix + f"Ya vi tu contexto de pago con estado {payment.get('status')}. Puedo enviarte un link de cobro, revisar el intento fallido o confirmar el pago contigo ahora mismo."
        return prefix + "Te ayudo con el cobro. Puedo enviarte un link de pago, validar el estado del intento y seguir contigo hasta que quede resuelto."
    if specialist == "support":
        return prefix + "Voy a ayudarte con eso. Ya conservé tu contexto de voz y texto para resolverlo sin que tengas que repetir todo."
    if specialist == "retention":
        return prefix + "Quiero ayudarte a resolver esto sin fricción. Puedo revisar alternativas, reagendar o dejarte una solución clara antes de que tomes una decisión final."
    if specialist == "recovery":
        return prefix + "Retomo contigo el caso con el contexto completo para moverlo al siguiente paso de forma simple."
    return prefix + "Ya tengo tu contexto y puedo seguir por voz o por texto sin perder continuidad."


def _render_assistant_audio(conn, *, organization_id: str, bot_id: str, conversation_id: str, contact_id: str | None, message_id: str, text: str, session: dict[str, Any]) -> dict[str, Any]:
    profile = voice_pipeline_service.build_voice_runtime_context(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        language="es",
        base_context={"channel": session.get("channel"), "session_id": session.get("id"), "surface": VOICE_SURFACE_VERSION},
    )
    try:
        asset = voice_pipeline_service._synthesize_audio(
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            contact_id=contact_id,
            message_id=message_id,
            text=text,
            language="es",
            voice_context=profile,
        )
    except Exception as exc:  # pragma: no cover - network/provider dependent
        return {"status": "failed", "error": str(exc), "provider": "voice_pipeline"}
    if asset:
        return {"status": "ready", "asset": asset, "provider": "voice_pipeline"}
    settings_map = voice_pipeline_service._voice_settings()
    if settings_map.get("tts_webhook"):
        return {"status": "queued_render", "provider": "voice_pipeline"}
    return {"status": "text_fallback", "provider": "voice_pipeline"}


def start_voice_channel_session(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    contact_id: str | None,
    conversation_id: str | None,
    channel: str = "voice",
    requested_modality: str = "voice",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_voice_channel_schema(conn)
    conversation = get_conversation(conn, conversation_id) if conversation_id else None
    resolved_contact_id = contact_id or (conversation.get("contact_id") if conversation else None)
    if not resolved_contact_id:
        raise ValueError("contact_id is required when conversation_id cannot resolve it")
    if not conversation:
        conversation = upsert_conversation(conn, organization_id=organization_id, bot_id=bot_id, contact_id=resolved_contact_id)
    memory = repo_load_recent_contact_memory(conn, organization_id=organization_id, bot_id=bot_id, contact_id=resolved_contact_id)
    recent_messages = _serialize_messages(repo_list_recent_conversation_messages(conn, conversation_id=conversation["id"], limit=6))
    shared_memory = build_shared_memory_context(
        conn=conn,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=conversation["id"],
        contact_id=resolved_contact_id,
        memory=dict(memory) if not isinstance(memory, dict) else memory,
        recent_messages=list(reversed(recent_messages)),
    )
    session = repo_create_session(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        contact_id=resolved_contact_id,
        conversation_id=conversation["id"],
        channel=channel,
        requested_modality=requested_modality,
        shared_memory=shared_memory,
        metadata=metadata,
    )
    return get_voice_channel_session(conn, session_id=session["id"])


def get_voice_channel_session(conn, *, session_id: str) -> dict[str, Any] | None:
    ensure_voice_channel_schema(conn)
    session = _load_session(conn, session_id)
    if not session:
        return None
    session["turns"] = _load_turns(conn, session_id)
    session["handoffs"] = _load_handoffs(conn, session_id)
    return session


def list_voice_channel_sessions(conn, *, organization_id: str, bot_id: str | None = None, contact_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    ensure_voice_channel_schema(conn)
    rows = repo_list_session_rows(conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact_id, limit=limit)
    return [get_voice_channel_session(conn, session_id=row["id"]) for row in rows]


def ingest_voice_channel_turn(
    conn,
    *,
    session_id: str,
    actor: str,
    transcript_text: str | None,
    provider_transcript: str | None = None,
    audio_url: str | None = None,
    requested_reply_mode: str = "voice",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_voice_channel_schema(conn)
    session = _load_session(conn, session_id)
    if not session:
        raise ValueError("Voice session not found")
    if actor not in {"contact", "assistant", "system"}:
        raise ValueError("Unsupported actor")
    transcript = str(transcript_text or provider_transcript or "").strip()
    urgency_level, urgency_score = _detect_urgency(transcript)
    requested_human = _requested_human(transcript)
    classification = {
        "intent": _detect_intent(transcript),
        "urgency_score": urgency_score,
        "requested_human": requested_human,
    }
    conversation = get_conversation(conn, session["conversation_id"]) or {"id": session["conversation_id"], "human_takeover": 0}
    bot = repo_load_bot(conn, bot_id=session["bot_id"])
    bot_config = from_json(bot.get("config_draft_json"), {})
    memory = repo_load_recent_contact_memory(conn, organization_id=session["organization_id"], bot_id=session["bot_id"], contact_id=session["contact_id"])
    recent_messages = _serialize_messages(repo_list_recent_conversation_messages(conn, conversation_id=session["conversation_id"], limit=6))
    shared_memory = build_shared_memory_context(
        conn=conn,
        organization_id=session["organization_id"],
        bot_id=session["bot_id"],
        conversation_id=session["conversation_id"],
        contact_id=session["contact_id"],
        memory=dict(memory) if not isinstance(memory, dict) else memory,
        recent_messages=list(reversed(recent_messages)),
    )
    route = route_intent_to_specialist(
        text=transcript,
        classification=classification,
        memory=dict(memory) if not isinstance(memory, dict) else memory,
        conversation=conversation,
        bot_config=bot_config,
    )
    policy_evaluation = evaluate_specialist_policy(
        conn,
        organization_id=session["organization_id"],
        bot_id=session["bot_id"],
        conversation_id=session["conversation_id"],
        contact_id=session["contact_id"],
        route=route,
        classification=classification,
        conversation=conversation,
        shared_memory=shared_memory,
        requested_action=None,
    )
    if actor == "contact" and session.get("barge_in_enabled"):
        _interrupt_active_assistant_turn(conn, session, reason="customer_barge_in")

    linked_voice_note = None
    modality = "voice" if actor == "contact" else requested_reply_mode
    message_kind = "audio" if modality.startswith("voice") else "text"
    message = create_message(
        conn,
        organization_id=session["organization_id"],
        conversation_id=session["conversation_id"],
        contact_id=session["contact_id"],
        bot_id=session["bot_id"],
        direction="inbound" if actor == "contact" else "outbound",
        kind=message_kind,
        source="voice_channel",
        body=transcript or ("[voice turn]" if actor == "contact" else "[assistant voice turn]"),
        status="received" if actor == "contact" else "queued",
        metadata={
            "voice_channel": {"session_id": session_id, "channel": session.get("channel"), "surface": VOICE_SURFACE_VERSION},
            "requested_reply_mode": requested_reply_mode,
            **(metadata or {}),
        },
    )
    if actor == "contact":
        linked_voice_note = ingest_voice_note(
            conn,
            organization_id=session["organization_id"],
            bot_id=session["bot_id"],
            conversation_id=session["conversation_id"],
            contact_id=session["contact_id"],
            message_id=message["id"],
            transcript=transcript or "Nota de voz sin transcript",
            language="es",
            media_url=audio_url,
            transcription_source="voice_channel_runtime",
            transcription_confidence=0.96 if transcript else 0.0,
            processing_status="completed" if transcript else "transcription_pending",
            reply_mode=requested_reply_mode,
            metadata={"voice_channel_session_id": session_id, "channel": session.get("channel")},
        )
        note_meta = from_json(linked_voice_note.get("metadata_json"), {})
        note_meta["voice_channel_session_id"] = session_id
        repo_update_voice_note_urgency(conn, voice_note_id=linked_voice_note["id"], urgency_level=urgency_level, metadata=note_meta)
    turn_index = _next_turn_index(conn, session_id)
    response_payload: dict[str, Any] = {}
    state = "completed"
    audio_render_status = None
    if actor == "assistant":
        response_payload = {"mode": requested_reply_mode}
    input_turn = repo_create_turn(
        conn,
        session_id=session_id,
        organization_id=session["organization_id"],
        bot_id=session["bot_id"],
        contact_id=session["contact_id"],
        conversation_id=session["conversation_id"],
        message_id=message["id"],
        linked_voice_note_id=linked_voice_note["id"] if linked_voice_note else None,
        turn_index=turn_index,
        actor=actor,
        modality=modality,
        transcript_text=transcript,
        normalized_text=_normalize(transcript),
        intent_family=route.get("intent_family"),
        urgency_level=urgency_level,
        urgency_score=urgency_score,
        requested_human=requested_human,
        extracted_entities=_extract_entities(transcript),
        route=route,
        policy=policy_evaluation,
        shared_memory=shared_memory,
        response=response_payload,
        state=state,
        audio_render_status=audio_render_status,
        metadata=metadata,
    )
    turn_id = input_turn["id"]
    repo_update_session_after_turn(
        conn,
        session_id=session_id,
        state=("thinking" if actor == "contact" else "speaking"),
        intent_family=route.get("intent_family"),
        specialist_agent_key=route.get("specialist_agent_key"),
        urgency_level=urgency_level,
        urgency_score=urgency_score,
        policy_profile_key=policy_evaluation.get("policy_profile_key"),
        policy_profile_version=policy_evaluation.get("policy_profile_version"),
        shared_memory=shared_memory,
    )

    handoff = None
    assistant_turn = None
    if actor == "contact":
        response_text = _response_text_for_route(transcript=transcript, route=route, shared_memory=shared_memory, urgency_level=urgency_level)
        handoff_needed = requested_human or conversation.get("human_takeover") or (route.get("specialist_agent_key") == "support" and urgency_score >= 85)
        if handoff_needed:
            handoff = create_voice_channel_handoff(
                conn,
                session_id=session_id,
                to_channel="text",
                reason="requested_human" if requested_human else "high_risk_or_existing_takeover",
                summary_text=response_text,
                target_queue="human_ops",
                metadata={"route": route, "policy": policy_evaluation},
            )
            repo_mark_session_handoff(conn, session_id=session_id, to_channel="text")
        render_result = _render_assistant_audio(
            conn,
            organization_id=session["organization_id"],
            bot_id=session["bot_id"],
            conversation_id=session["conversation_id"],
            contact_id=session["contact_id"],
            message_id=message["id"],
            text=response_text,
            session=session,
        )
        assistant_message = create_message(
            conn,
            organization_id=session["organization_id"],
            conversation_id=session["conversation_id"],
            contact_id=session["contact_id"],
            bot_id=session["bot_id"],
            direction="outbound",
            kind="audio" if requested_reply_mode == "voice" else "text",
            source="voice_channel_ai",
            body=response_text,
            status="queued",
            metadata={
                "voice_channel": {"session_id": session_id, "channel": session.get("channel"), "surface": VOICE_SURFACE_VERSION},
                "route": route,
                "policy": policy_evaluation,
                "audio_render": render_result,
            },
        )
        assistant_turn_index = _next_turn_index(conn, session_id)
        assistant_turn = repo_create_turn(
            conn,
            session_id=session_id,
            organization_id=session["organization_id"],
            bot_id=session["bot_id"],
            contact_id=session["contact_id"],
            conversation_id=session["conversation_id"],
            message_id=assistant_message["id"],
            linked_voice_note_id=None,
            turn_index=assistant_turn_index,
            actor="assistant",
            modality=requested_reply_mode,
            transcript_text=response_text,
            normalized_text=_normalize(response_text),
            intent_family=route.get("intent_family"),
            urgency_level=urgency_level,
            urgency_score=urgency_score,
            requested_human=False,
            extracted_entities={},
            route=route,
            policy=policy_evaluation,
            shared_memory=shared_memory,
            response={"text": response_text, "render": render_result},
            state=("queued_render" if render_result.get("status") in {"queued_render", "text_fallback"} else "speaking"),
            audio_render_status=render_result.get("status"),
            metadata={"generated_by": VOICE_SURFACE_VERSION},
        )
        repo_update_session_state(conn, session_id=session_id, state=("handoff" if handoff else "speaking"), active_modality=requested_reply_mode)
    return {
        "session": get_voice_channel_session(conn, session_id=session_id),
        "input_turn": input_turn,
        "assistant_turn": assistant_turn,
        "handoff": handoff,
        "route": route,
        "policy": policy_evaluation,
        "shared_memory": shared_memory,
    }


def interrupt_voice_channel_session(conn, *, session_id: str, reason: str = "customer_barge_in") -> dict[str, Any]:
    ensure_voice_channel_schema(conn)
    session = _load_session(conn, session_id)
    if not session:
        raise ValueError("Voice session not found")
    interrupted = _interrupt_active_assistant_turn(conn, session, reason=reason)
    repo_update_session_state(conn, session_id=session_id, state="listening")
    return {
        "session": get_voice_channel_session(conn, session_id=session_id),
        "interrupted_turn": dict(interrupted) if interrupted and not isinstance(interrupted, dict) else interrupted,
        "reason": reason,
    }


def create_voice_channel_handoff(
    conn,
    *,
    session_id: str,
    to_channel: str,
    reason: str,
    summary_text: str | None,
    target_queue: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_voice_channel_schema(conn)
    session = _load_session(conn, session_id)
    if not session:
        raise ValueError("Voice session not found")
    return repo_create_handoff(
        conn,
        session=session,
        to_channel=to_channel,
        reason=reason,
        summary_text=summary_text,
        target_queue=target_queue,
        metadata=metadata,
    )
