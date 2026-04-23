from __future__ import annotations

from typing import Any

from ..contact_intelligence import relationship_snapshot
from ..knowledge_runtime import search_governed_knowledge
from ..runtime_settings import ai_optimization_settings, memory_runtime_settings
from ..world_class import recent_checkpoints, search_knowledge_embeddings_cached, search_memory_episodes, search_memory_vectors
from .generation_language import _detect_contact_language, _detect_customer_tone, _language_voice_layer, _supported_languages


def build_generation_bundle(
    text: str,
    classification: dict[str, Any],
    bot_config: dict[str, Any],
    memory: dict[str, Any],
    recent_messages: list[dict[str, Any]],
    *,
    conn=None,
    organization_id: str | None = None,
    bot_id: str | None = None,
    contact_id: str | None = None,
    conversation_id: str | None = None,
    recent_voice_notes: list[dict[str, Any]] | None = None,
    language_config: dict[str, Any] | None = None,
    execution_plan: dict[str, Any] | None = None,
    grounded_context: dict[str, Any] | None = None,
    candidate_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recent_voice_notes = recent_voice_notes or []
    optimization = ai_optimization_settings()
    memory_profile = memory_runtime_settings()
    language = _detect_contact_language(text, recent_messages, bot_config, recent_voice_notes, language_config)
    tone_context = _detect_customer_tone(text, recent_messages, recent_voice_notes)
    recalled_memory = search_memory_vectors(conn, organization_id=organization_id or "", contact_id=contact_id, bot_id=bot_id, query=text, limit=4) if conn and organization_id else []
    episodic_recall = search_memory_episodes(
        conn,
        organization_id=organization_id or "",
        contact_id=contact_id,
        bot_id=bot_id,
        query=text,
        include_cross_bot=bool(memory_profile.get("cross_bot_intelligence_enabled", True)),
        limit=int(memory_profile.get("episode_search_limit") or 5),
        hours_window=int(memory_profile.get("session_window_hours") or 72),
    ) if conn and organization_id and memory_profile.get("episodic_memory_enabled", True) else []
    knowledge_hits = search_knowledge_embeddings_cached(
        conn,
        organization_id=organization_id or "",
        bot_id=bot_id or "",
        query=text,
        limit=4,
        ttl_seconds=int(optimization.get("knowledge_search_cache_ttl_seconds") or 21600),
    ) if conn and organization_id and bot_id else []
    governed_hits = search_governed_knowledge(
        conn,
        organization_id=organization_id or "",
        bot_id=bot_id or "",
        query=text,
        intent=classification.get("intent"),
        limit=4,
    ) if conn and organization_id and bot_id else []
    checkpoints = recent_checkpoints(conn, conversation_id=conversation_id, limit=2) if conn and conversation_id else []
    prompt_payload = {
        "message": text,
        "classification": classification,
        "identity": bot_config.get("identity", {}),
        "personality": bot_config.get("personality", {}),
        "objective": bot_config.get("objective", {}),
        "business_knowledge": bot_config.get("business_knowledge", {}),
        "rules": bot_config.get("rules", {}),
        "memory": memory,
        "relationship_intelligence": relationship_snapshot(memory),
        "language_context": {
            "default_language": (language_config or {}).get("default_language") or bot_config.get("identity", {}).get("language") or "es",
            "supported_languages": _supported_languages(bot_config, language_config),
            "detected_language": language,
            "reply_in_detected_language": True,
        },
        "language_voice_layer": _language_voice_layer(language, language_config),
        "tone_of_voice_context": tone_context,
        "recent_conversation_context": [{"direction": m["direction"], "body": m["body"]} for m in recent_messages[-8:]],
        "recent_voice_context": [
            {
                "summary": note.get("summary"),
                "transcript": note.get("transcript"),
                "detected_language": note.get("detected_language"),
                "intent": note.get("intent"),
                "urgency_level": note.get("urgency_level"),
                "emotion": note.get("emotion"),
            }
            for note in recent_voice_notes[:3]
        ],
        "memory_recall": [item.get("content_text") for item in recalled_memory],
        "episodic_memory": [item.get("summary_text") for item in episodic_recall],
        "retrieved_knowledge": [item.get("content_text") for item in knowledge_hits],
        "governed_knowledge": [item.get("content_text") for item in governed_hits],
        "governed_traceability": [item.get("traceability") for item in governed_hits],
        "conversation_checkpoints": [{"summary_text": item.get("summary_text"), "facts": item.get("facts")} for item in checkpoints],
        "execution_plan": execution_plan or {},
        "grounded_context": grounded_context or {},
        "response_ranking_candidate": candidate_spec or {},
    }
    return {
        "language": language,
        "tone_context": tone_context,
        "knowledge_hits": knowledge_hits,
        "prompt_payload": prompt_payload,
    }
