from __future__ import annotations

from typing import Any

from .base import ConnectionLike
from ..db import execute, fetch_all, fetch_one
from ..utils import from_json, new_id, to_json, utcnow_iso


def _materialize_session(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    payload = dict(row) if not isinstance(row, dict) else dict(row)
    payload["shared_memory"] = from_json(payload.get("shared_memory_json"), {})
    payload["metadata"] = from_json(payload.get("metadata_json"), {})
    return payload


def _materialize_turn(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    payload = dict(row) if not isinstance(row, dict) else dict(row)
    payload["entities"] = from_json(payload.get("extracted_entities_json"), {})
    payload["route"] = from_json(payload.get("route_json"), {})
    payload["policy"] = from_json(payload.get("policy_json"), {})
    payload["shared_memory"] = from_json(payload.get("shared_memory_json"), {})
    payload["response"] = from_json(payload.get("response_json"), {})
    payload["metadata"] = from_json(payload.get("metadata_json"), {})
    return payload


def _materialize_handoff(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    payload = dict(row) if not isinstance(row, dict) else dict(row)
    payload["metadata"] = from_json(payload.get("metadata_json"), {})
    return payload


def next_turn_index(conn: ConnectionLike, session_id: str) -> int:
    row = fetch_one(conn, "SELECT COALESCE(MAX(turn_index), 0) AS value FROM voice_channel_turns WHERE session_id = ?", (session_id,))
    return int((row or {}).get("value") or 0) + 1


def load_session(conn: ConnectionLike, session_id: str) -> dict[str, Any] | None:
    return _materialize_session(fetch_one(conn, "SELECT * FROM voice_channel_sessions WHERE id = ?", (session_id,)))


def list_session_rows(
    conn: ConnectionLike,
    *,
    organization_id: str,
    bot_id: str | None = None,
    contact_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
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
    return [dict(row) if not isinstance(row, dict) else row for row in rows]


def load_turns(conn: ConnectionLike, session_id: str) -> list[dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM voice_channel_turns WHERE session_id = ? ORDER BY turn_index ASC", (session_id,))
    return [_materialize_turn(row) for row in rows if row]


def get_turn(conn: ConnectionLike, turn_id: str) -> dict[str, Any] | None:
    return _materialize_turn(fetch_one(conn, "SELECT * FROM voice_channel_turns WHERE id = ?", (turn_id,)))


def load_handoffs(conn: ConnectionLike, session_id: str) -> list[dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM voice_channel_handoffs WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
    return [_materialize_handoff(row) for row in rows if row]


def get_handoff(conn: ConnectionLike, handoff_id: str) -> dict[str, Any] | None:
    return _materialize_handoff(fetch_one(conn, "SELECT * FROM voice_channel_handoffs WHERE id = ?", (handoff_id,)))


def load_recent_contact_memory(conn: ConnectionLike, *, organization_id: str, bot_id: str, contact_id: str) -> dict[str, Any]:
    return fetch_one(
        conn,
        "SELECT * FROM contact_memory WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY last_updated_at DESC LIMIT 1",
        (organization_id, bot_id, contact_id),
    ) or {}


def list_recent_conversation_messages(conn: ConnectionLike, *, conversation_id: str, limit: int = 6) -> list[dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?", (conversation_id, limit))
    return [dict(row) if not isinstance(row, dict) else row for row in rows]


def load_bot(conn: ConnectionLike, *, bot_id: str) -> dict[str, Any]:
    return fetch_one(conn, "SELECT * FROM bots WHERE id = ?", (bot_id,)) or {}


def create_session(
    conn: ConnectionLike,
    *,
    organization_id: str,
    bot_id: str,
    contact_id: str,
    conversation_id: str,
    channel: str,
    requested_modality: str,
    shared_memory: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session_id = new_id("voice_session")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO voice_channel_sessions (id, organization_id, bot_id, contact_id, conversation_id, channel, state, requested_modality, active_modality, turn_taking_mode, barge_in_enabled, continuity_mode, stt_provider, tts_provider, latest_intent_family, latest_specialist_agent_key, urgency_level, urgency_score, policy_profile_key, policy_profile_version, handoff_channel, handoff_state, shared_memory_json, metadata_json, started_at, updated_at, ended_at) VALUES (?, ?, ?, ?, ?, ?, 'listening', ?, ?, 'full_duplex_guarded', 1, 'shared_runtime_memory', ?, ?, NULL, NULL, 'normal', 0, NULL, NULL, NULL, 'none', ?, ?, ?, ?, NULL)",
        (
            session_id,
            organization_id,
            bot_id,
            contact_id,
            conversation_id,
            channel,
            requested_modality,
            requested_modality,
            "voice_stt_runtime",
            "voice_tts_runtime",
            to_json(shared_memory),
            to_json(metadata or {}),
            now,
            now,
        ),
    )
    return load_session(conn, session_id) or {}


def update_voice_note_urgency(conn: ConnectionLike, *, voice_note_id: str, urgency_level: str, metadata: dict[str, Any]) -> None:
    mapped = "alta" if urgency_level == "high" else "media"
    execute(conn, "UPDATE voice_notes SET urgency_level = ?, metadata_json = ? WHERE id = ?", (mapped, to_json(metadata), voice_note_id))


def create_turn(
    conn: ConnectionLike,
    *,
    session_id: str,
    organization_id: str,
    bot_id: str,
    contact_id: str | None,
    conversation_id: str,
    message_id: str,
    linked_voice_note_id: str | None,
    turn_index: int,
    actor: str,
    modality: str,
    transcript_text: str,
    normalized_text: str,
    intent_family: str | None,
    urgency_level: str,
    urgency_score: int,
    requested_human: bool,
    extracted_entities: dict[str, Any],
    route: dict[str, Any],
    policy: dict[str, Any],
    shared_memory: dict[str, Any],
    response: dict[str, Any],
    state: str,
    audio_render_status: str | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    turn_id = new_id("voice_turn")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO voice_channel_turns (id, session_id, organization_id, bot_id, contact_id, conversation_id, message_id, linked_voice_note_id, turn_index, actor, modality, transcript_text, normalized_text, intent_family, urgency_level, urgency_score, requested_human, extracted_entities_json, route_json, policy_json, shared_memory_json, response_json, state, interruption_reason, audio_render_status, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)",
        (
            turn_id,
            session_id,
            organization_id,
            bot_id,
            contact_id,
            conversation_id,
            message_id,
            linked_voice_note_id,
            turn_index,
            actor,
            modality,
            transcript_text,
            normalized_text,
            intent_family,
            urgency_level,
            urgency_score,
            1 if requested_human else 0,
            to_json(extracted_entities),
            to_json(route),
            to_json(policy),
            to_json(shared_memory),
            to_json(response),
            state,
            audio_render_status,
            to_json(metadata or {}),
            now,
            now,
        ),
    )
    return get_turn(conn, turn_id) or {}


def update_session_after_turn(
    conn: ConnectionLike,
    *,
    session_id: str,
    state: str,
    intent_family: str | None,
    specialist_agent_key: str | None,
    urgency_level: str,
    urgency_score: int,
    policy_profile_key: str | None,
    policy_profile_version: str | None,
    shared_memory: dict[str, Any],
) -> None:
    execute(
        conn,
        "UPDATE voice_channel_sessions SET state = ?, latest_intent_family = ?, latest_specialist_agent_key = ?, urgency_level = ?, urgency_score = ?, policy_profile_key = ?, policy_profile_version = ?, shared_memory_json = ?, updated_at = ? WHERE id = ?",
        (
            state,
            intent_family,
            specialist_agent_key,
            urgency_level,
            urgency_score,
            policy_profile_key,
            policy_profile_version,
            to_json(shared_memory),
            utcnow_iso(),
            session_id,
        ),
    )


def update_session_state(conn: ConnectionLike, *, session_id: str, state: str, active_modality: str | None = None) -> None:
    if active_modality is None:
        execute(conn, "UPDATE voice_channel_sessions SET state = ?, updated_at = ? WHERE id = ?", (state, utcnow_iso(), session_id))
        return
    execute(conn, "UPDATE voice_channel_sessions SET state = ?, active_modality = ?, updated_at = ? WHERE id = ?", (state, active_modality, utcnow_iso(), session_id))


def mark_session_handoff(conn: ConnectionLike, *, session_id: str, to_channel: str) -> None:
    execute(
        conn,
        "UPDATE voice_channel_sessions SET state = 'handoff', handoff_channel = ?, handoff_state = 'completed', updated_at = ? WHERE id = ?",
        (to_channel, utcnow_iso(), session_id),
    )


def interrupt_active_assistant_turn(conn: ConnectionLike, *, session: dict[str, Any], reason: str) -> dict[str, Any] | None:
    active = fetch_one(
        conn,
        "SELECT * FROM voice_channel_turns WHERE session_id = ? AND actor = 'assistant' AND state IN ('queued_render', 'speaking', 'completed', 'delivered') ORDER BY turn_index DESC LIMIT 1",
        (session["id"],),
    )
    if not active:
        return None
    metadata = from_json(active.get("metadata_json"), {})
    if metadata.get("interrupted"):
        return _materialize_turn(dict(active) if not isinstance(active, dict) else active)
    metadata["interrupted"] = True
    metadata["interruption_reason"] = reason
    execute(
        conn,
        "UPDATE voice_channel_turns SET state = 'interrupted', interruption_reason = ?, metadata_json = ?, updated_at = ? WHERE id = ?",
        (reason, to_json(metadata), utcnow_iso(), active["id"]),
    )
    execute(conn, "UPDATE voice_channel_sessions SET state = 'listening', updated_at = ? WHERE id = ?", (utcnow_iso(), session["id"]))
    return get_turn(conn, active["id"])


def create_handoff(
    conn: ConnectionLike,
    *,
    session: dict[str, Any],
    to_channel: str,
    reason: str,
    summary_text: str | None,
    target_queue: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    handoff_id = new_id("voice_handoff")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO voice_channel_handoffs (id, session_id, organization_id, bot_id, contact_id, conversation_id, from_channel, to_channel, reason, summary_text, target_queue, status, metadata_json, created_at, accepted_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?)",
        (
            handoff_id,
            session["id"],
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
    mark_session_handoff(conn, session_id=session["id"], to_channel=to_channel)
    return get_handoff(conn, handoff_id) or {}
