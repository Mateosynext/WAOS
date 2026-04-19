from __future__ import annotations

import re
from typing import Any

from .agent_policy_runtime import evaluate_specialist_policy, get_policy_profile_for_specialist, serialize_policy_profile
from .db import execute, fetch_all, fetch_one, table_exists
from .domains.customer_experience import ingest_voice_note
from .multi_agent_runtime import build_shared_memory_context, route_intent_to_specialist
from .repositories.conversations import create_message, get_conversation, upsert_conversation
from .utils import from_json, new_id, to_json, utcnow_iso
from .voice_pipeline import voice_pipeline_service

VOICE_SURFACE_VERSION = "voice_channel_v1"


def ensure_voice_channel_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS voice_channel_sessions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'listening',
            requested_modality TEXT NOT NULL DEFAULT 'voice',
            active_modality TEXT NOT NULL DEFAULT 'voice',
            turn_taking_mode TEXT NOT NULL DEFAULT 'full_duplex_guarded',
            barge_in_enabled INTEGER NOT NULL DEFAULT 1,
            continuity_mode TEXT NOT NULL DEFAULT 'shared_runtime_memory',
            stt_provider TEXT,
            tts_provider TEXT,
            latest_intent_family TEXT,
            latest_specialist_agent_key TEXT,
            urgency_level TEXT NOT NULL DEFAULT 'normal',
            urgency_score INTEGER NOT NULL DEFAULT 0,
            policy_profile_key TEXT,
            policy_profile_version TEXT,
            handoff_channel TEXT,
            handoff_state TEXT NOT NULL DEFAULT 'none',
            shared_memory_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            ended_at TEXT,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        CREATE INDEX IF NOT EXISTS idx_voice_channel_sessions_org ON voice_channel_sessions(organization_id, bot_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_voice_channel_sessions_contact ON voice_channel_sessions(contact_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS voice_channel_turns (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            message_id TEXT,
            linked_voice_note_id TEXT,
            turn_index INTEGER NOT NULL,
            actor TEXT NOT NULL,
            modality TEXT NOT NULL,
            transcript_text TEXT,
            normalized_text TEXT,
            intent_family TEXT,
            urgency_level TEXT,
            urgency_score INTEGER NOT NULL DEFAULT 0,
            requested_human INTEGER NOT NULL DEFAULT 0,
            extracted_entities_json TEXT NOT NULL DEFAULT '{}',
            route_json TEXT NOT NULL DEFAULT '{}',
            policy_json TEXT NOT NULL DEFAULT '{}',
            shared_memory_json TEXT NOT NULL DEFAULT '{}',
            response_json TEXT NOT NULL DEFAULT '{}',
            state TEXT NOT NULL DEFAULT 'completed',
            interruption_reason TEXT,
            audio_render_status TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES voice_channel_sessions(id),
            FOREIGN KEY (message_id) REFERENCES messages(id),
            FOREIGN KEY (linked_voice_note_id) REFERENCES voice_notes(id)
        );
        CREATE INDEX IF NOT EXISTS idx_voice_channel_turns_session ON voice_channel_turns(session_id, turn_index ASC);
        CREATE INDEX IF NOT EXISTS idx_voice_channel_turns_conversation ON voice_channel_turns(conversation_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS voice_channel_handoffs (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            from_channel TEXT NOT NULL,
            to_channel TEXT NOT NULL,
            reason TEXT NOT NULL,
            summary_text TEXT,
            target_queue TEXT,
            status TEXT NOT NULL DEFAULT 'completed',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            accepted_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (session_id) REFERENCES voice_channel_sessions(id)
        );
        CREATE INDEX IF NOT EXISTS idx_voice_channel_handoffs_session ON voice_channel_handoffs(session_id, created_at DESC);
        """
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
    row = fetch_one(conn, "SELECT COALESCE(MAX(turn_index), 0) AS value FROM voice_channel_turns WHERE session_id = ?", (session_id,))
    return int((row or {}).get("value") or 0) + 1


def _serialize_messages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row) if not isinstance(row, dict) else dict(row)
        payload["metadata"] = from_json(payload.get("metadata_json"), {})
        items.append(payload)
    return items


def _load_session(conn, session_id: str) -> dict[str, Any] | None:
    session = fetch_one(conn, "SELECT * FROM voice_channel_sessions WHERE id = ?", (session_id,))
    if not session:
        return None
    payload = dict(session) if not isinstance(session, dict) else dict(session)
    payload["shared_memory"] = from_json(payload.get("shared_memory_json"), {})
    payload["metadata"] = from_json(payload.get("metadata_json"), {})
    return payload


def _load_turns(conn, session_id: str) -> list[dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM voice_channel_turns WHERE session_id = ? ORDER BY turn_index ASC", (session_id,))
    items: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row) if not isinstance(row, dict) else dict(row)
        payload["entities"] = from_json(payload.get("extracted_entities_json"), {})
        payload["route"] = from_json(payload.get("route_json"), {})
        payload["policy"] = from_json(payload.get("policy_json"), {})
        payload["shared_memory"] = from_json(payload.get("shared_memory_json"), {})
        payload["response"] = from_json(payload.get("response_json"), {})
        payload["metadata"] = from_json(payload.get("metadata_json"), {})
        items.append(payload)
    return items


def _load_handoffs(conn, session_id: str) -> list[dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM voice_channel_handoffs WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
    items: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row) if not isinstance(row, dict) else dict(row)
        payload["metadata"] = from_json(payload.get("metadata_json"), {})
        items.append(payload)
    return items


def _interrupt_active_assistant_turn(conn, session: dict[str, Any], reason: str) -> dict[str, Any] | None:
    active = fetch_one(
        conn,
        "SELECT * FROM voice_channel_turns WHERE session_id = ? AND actor = 'assistant' AND state IN ('queued_render', 'speaking', 'completed', 'delivered') ORDER BY turn_index DESC LIMIT 1",
        (session["id"],),
    )
    if not active:
        return None
    metadata = from_json(active.get("metadata_json"), {})
    if metadata.get("interrupted"):
        return dict(active) if not isinstance(active, dict) else active
    metadata["interrupted"] = True
    metadata["interruption_reason"] = reason
    execute(
        conn,
        "UPDATE voice_channel_turns SET state = 'interrupted', interruption_reason = ?, metadata_json = ?, updated_at = ? WHERE id = ?",
        (reason, to_json(metadata), utcnow_iso(), active["id"]),
    )
    execute(conn, "UPDATE voice_channel_sessions SET state = 'listening', updated_at = ? WHERE id = ?", (utcnow_iso(), session["id"]))
    return fetch_one(conn, "SELECT * FROM voice_channel_turns WHERE id = ?", (active["id"],))


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
    memory = fetch_one(conn, "SELECT * FROM contact_memory WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY last_updated_at DESC LIMIT 1", (organization_id, bot_id, resolved_contact_id)) or {}
    recent_messages = _serialize_messages(fetch_all(conn, "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 6", (conversation["id"],)))
    shared_memory = build_shared_memory_context(
        conn=conn,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=conversation["id"],
        contact_id=resolved_contact_id,
        memory=dict(memory) if not isinstance(memory, dict) else memory,
        recent_messages=list(reversed(recent_messages)),
    )
    session_id = new_id("voice_session")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO voice_channel_sessions (id, organization_id, bot_id, contact_id, conversation_id, channel, state, requested_modality, active_modality, turn_taking_mode, barge_in_enabled, continuity_mode, stt_provider, tts_provider, latest_intent_family, latest_specialist_agent_key, urgency_level, urgency_score, policy_profile_key, policy_profile_version, handoff_channel, handoff_state, shared_memory_json, metadata_json, started_at, updated_at, ended_at) VALUES (?, ?, ?, ?, ?, ?, 'listening', ?, ?, 'full_duplex_guarded', 1, 'shared_runtime_memory', ?, ?, NULL, NULL, 'normal', 0, NULL, NULL, NULL, 'none', ?, ?, ?, ?, NULL)",
        (
            session_id,
            organization_id,
            bot_id,
            resolved_contact_id,
            conversation["id"],
            channel,
            requested_modality,
            requested_modality,
            'voice_stt_runtime',
            'voice_tts_runtime',
            to_json(shared_memory),
            to_json(metadata or {}),
            now,
            now,
        ),
    )
    return get_voice_channel_session(conn, session_id=session_id)


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
    clauses = ["organization_id = ?"]
    params: list[Any] = [organization_id]
    if bot_id:
        clauses.append("bot_id = ?")
        params.append(bot_id)
    if contact_id:
        clauses.append("contact_id = ?")
        params.append(contact_id)
    params.append(limit)
    rows = fetch_all(conn, f"SELECT * FROM voice_channel_sessions WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC LIMIT ?", tuple(params))
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
    bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ?", (session["bot_id"],)) or {}
    bot_config = from_json(bot.get("config_draft_json"), {})
    memory = fetch_one(conn, "SELECT * FROM contact_memory WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY last_updated_at DESC LIMIT 1", (session["organization_id"], session["bot_id"], session["contact_id"])) or {}
    recent_messages = _serialize_messages(fetch_all(conn, "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 6", (session["conversation_id"],)))
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
        execute(conn, "UPDATE voice_notes SET urgency_level = ?, metadata_json = ? WHERE id = ?", ("alta" if urgency_level == "high" else "media" if urgency_level == "medium" else "media", to_json(note_meta), linked_voice_note["id"]))
    turn_id = new_id("voice_turn")
    turn_index = _next_turn_index(conn, session_id)
    response_payload: dict[str, Any] = {}
    state = "completed"
    audio_render_status = None
    if actor == "assistant":
        response_payload = {"mode": requested_reply_mode}
    execute(
        conn,
        "INSERT INTO voice_channel_turns (id, session_id, organization_id, bot_id, contact_id, conversation_id, message_id, linked_voice_note_id, turn_index, actor, modality, transcript_text, normalized_text, intent_family, urgency_level, urgency_score, requested_human, extracted_entities_json, route_json, policy_json, shared_memory_json, response_json, state, interruption_reason, audio_render_status, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)",
        (
            turn_id,
            session_id,
            session["organization_id"],
            session["bot_id"],
            session["contact_id"],
            session["conversation_id"],
            message["id"],
            linked_voice_note["id"] if linked_voice_note else None,
            turn_index,
            actor,
            modality,
            transcript,
            _normalize(transcript),
            route.get("intent_family"),
            urgency_level,
            urgency_score,
            1 if requested_human else 0,
            to_json(_extract_entities(transcript)),
            to_json(route),
            to_json(policy_evaluation),
            to_json(shared_memory),
            to_json(response_payload),
            state,
            audio_render_status,
            to_json(metadata or {}),
            utcnow_iso(),
            utcnow_iso(),
        ),
    )
    execute(
        conn,
        "UPDATE voice_channel_sessions SET state = ?, latest_intent_family = ?, latest_specialist_agent_key = ?, urgency_level = ?, urgency_score = ?, policy_profile_key = ?, policy_profile_version = ?, shared_memory_json = ?, updated_at = ? WHERE id = ?",
        (
            "thinking" if actor == "contact" else "speaking",
            route.get("intent_family"),
            route.get("specialist_agent_key"),
            urgency_level,
            urgency_score,
            policy_evaluation.get("policy_profile_key"),
            policy_evaluation.get("policy_profile_version"),
            to_json(shared_memory),
            utcnow_iso(),
            session_id,
        ),
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
            execute(conn, "UPDATE voice_channel_sessions SET state = 'handoff', handoff_channel = 'text', handoff_state = 'completed', updated_at = ? WHERE id = ?", (utcnow_iso(), session_id))
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
        assistant_turn_id = new_id("voice_turn")
        assistant_turn_index = _next_turn_index(conn, session_id)
        execute(
            conn,
            "INSERT INTO voice_channel_turns (id, session_id, organization_id, bot_id, contact_id, conversation_id, message_id, linked_voice_note_id, turn_index, actor, modality, transcript_text, normalized_text, intent_family, urgency_level, urgency_score, requested_human, extracted_entities_json, route_json, policy_json, shared_memory_json, response_json, state, interruption_reason, audio_render_status, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, 'assistant', ?, ?, ?, ?, ?, ?, 0, '{}', ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)",
            (
                assistant_turn_id,
                session_id,
                session["organization_id"],
                session["bot_id"],
                session["contact_id"],
                session["conversation_id"],
                assistant_message["id"],
                assistant_turn_index,
                requested_reply_mode,
                response_text,
                _normalize(response_text),
                route.get("intent_family"),
                urgency_level,
                urgency_score,
                to_json(route),
                to_json(policy_evaluation),
                to_json(shared_memory),
                to_json({"text": response_text, "render": render_result}),
                "queued_render" if render_result.get("status") in {"queued_render", "text_fallback"} else "speaking",
                render_result.get("status"),
                to_json({"generated_by": VOICE_SURFACE_VERSION}),
                utcnow_iso(),
                utcnow_iso(),
            ),
        )
        execute(conn, "UPDATE voice_channel_sessions SET state = ?, active_modality = ?, updated_at = ? WHERE id = ?", (("handoff" if handoff else "speaking"), requested_reply_mode, utcnow_iso(), session_id))
        assistant_turn = fetch_one(conn, "SELECT * FROM voice_channel_turns WHERE id = ?", (assistant_turn_id,))
    return {
        "session": get_voice_channel_session(conn, session_id=session_id),
        "input_turn": next((item for item in _load_turns(conn, session_id) if item["id"] == turn_id), None),
        "assistant_turn": next((item for item in _load_turns(conn, session_id) if assistant_turn and item["id"] == assistant_turn["id"]), None),
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
    execute(conn, "UPDATE voice_channel_sessions SET state = 'listening', updated_at = ? WHERE id = ?", (utcnow_iso(), session_id))
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
    handoff_id = new_id("voice_handoff")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO voice_channel_handoffs (id, session_id, organization_id, bot_id, contact_id, conversation_id, from_channel, to_channel, reason, summary_text, target_queue, status, metadata_json, created_at, accepted_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?)",
        (
            handoff_id,
            session_id,
            session["organization_id"],
            session["bot_id"],
            session["contact_id"],
            session["conversation_id"],
            session.get("channel") or "voice",
            to_channel,
            reason,
            summary_text,
            target_queue,
            to_json(metadata or {}),
            now,
            now,
            now,
        ),
    )
    execute(
        conn,
        "UPDATE voice_channel_sessions SET state = 'handoff', handoff_channel = ?, handoff_state = 'completed', updated_at = ? WHERE id = ?",
        (to_channel, now, session_id),
    )
    return fetch_one(conn, "SELECT * FROM voice_channel_handoffs WHERE id = ?", (handoff_id,))
