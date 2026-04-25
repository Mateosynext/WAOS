from __future__ import annotations

from typing import Any

from ..contact_intelligence import relationship_snapshot
from ..db import fetch_all
from ..domains.language import get_language_config
from ..knowledge_runtime import sync_config_knowledge
from ..platform import start_execution_run
from ..utils import from_json
from ..world_class import index_bot_knowledge

def load_pipeline_context(
    conn,
    *,
    incoming_message: dict[str, Any],
    conversation: dict[str, Any],
    bot: dict[str, Any],
    memory: dict[str, Any],
    correlation_id: str | None,
) -> dict[str, Any]:
    message_metadata = from_json(incoming_message.get("metadata_json"), {}) if incoming_message.get("metadata_json") else {}
    effective_correlation_id = correlation_id or incoming_message.get("correlation_id") or message_metadata.get("correlation_id")
    trace_seed = message_metadata.get("trace_id") or effective_correlation_id
    bot_config = from_json(bot["config_draft_json"], {})
    index_bot_knowledge(conn, organization_id=conversation["organization_id"], bot_id=bot["id"], bot_config=bot_config)
    sync_config_knowledge(conn, organization_id=conversation["organization_id"], bot_id=bot["id"], bot_config=bot_config)
    recent_messages = fetch_all(
        conn,
        "SELECT direction, body, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation["id"],),
    )
    recent_voice_notes = fetch_all(
        conn,
        "SELECT transcript, summary, detected_language, intent, urgency_level, emotion, transcription_confidence, audio_quality, background_noise_level, processing_status, reply_mode, created_at FROM voice_notes WHERE bot_id = ? AND conversation_id = ? ORDER BY created_at DESC LIMIT 3",
        (bot["id"], conversation["id"]),
    )
    language_config = get_language_config(conn, conversation["organization_id"], bot["id"])
    classification_input = {
        "message": incoming_message["body"],
        "memory": memory,
        "relationship_intelligence": relationship_snapshot(memory),
        "bot_identity": bot_config.get("identity", {}),
        "objective": bot_config.get("objective", {}),
        "language_context": {
            "default_language": language_config.get("default_language"),
            "supported_languages": language_config.get("supported_languages", []),
        },
        "voice_context": [
            {
                "summary": item.get("summary"),
                "detected_language": item.get("detected_language"),
                "intent": item.get("intent"),
                "urgency_level": item.get("urgency_level"),
                "emotion": item.get("emotion"),
            }
            for item in recent_voice_notes
        ],
    }
    run = start_execution_run(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        version_id=bot.get("published_version_id"),
        conversation_id=conversation["id"],
        message_id=incoming_message["id"],
        job_id=None,
        source_type="inbound_message",
        queue_name="runtime.inbound",
        input_payload=classification_input,
        trace_id=trace_seed,
        correlation_id=effective_correlation_id,
    )
    return {
        "message_metadata": message_metadata,
        "effective_correlation_id": effective_correlation_id,
        "bot_config": bot_config,
        "recent_messages": recent_messages,
        "recent_voice_notes": recent_voice_notes,
        "language_config": language_config,
        "classification_input": classification_input,
        "run": run,
    }


