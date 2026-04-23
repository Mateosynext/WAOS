from __future__ import annotations

import json
import re
import time
from typing import Any, Iterator

import httpx

from ..config import settings
from ..contact_intelligence import build_relationship_intelligence, merge_memory_json, relationship_snapshot
from ..db import execute, fetch_all, fetch_one, has_column, table_exists
from ..domain_events import emit_domain_event
from ..policy_engine import DEFAULT_INTENT_KEYWORDS, evaluate_policy_action, resolve_intent_keywords
from ..domains.language import default_language_templates, get_language_config
from ..platform import append_technical_log, finish_execution_run, start_execution_run
from ..telemetry_runtime import record_stage_metric
from ..world_class import finish_trace_span, start_trace_span
from ..repositories import create_audit_log, create_message
from ..utils import add_minutes, from_json, hash_value, new_id, parse_iso, to_json, utcnow_iso
from ..talent_runtime import generate_talent_reply, maybe_register_candidate_confirmation, talent_config_from_bot_config
from ..runtime_settings import ai_optimization_settings, memory_runtime_settings
from ..world_class import append_memory_episode, cache_efficiency_overview, choose_model, circuit_allow, circuit_record_failure, circuit_record_success, compress_prompt_payload, index_bot_knowledge, lookup_ai_cache, maybe_create_conversation_checkpoint, recent_checkpoints, record_ai_usage, search_knowledge_embeddings, search_knowledge_embeddings_cached, search_memory_episodes, search_memory_vectors, store_ai_cache, upsert_memory_vector, record_revenue_event
from ..knowledge_runtime import search_governed_knowledge, sync_config_knowledge
from ..response_ranking_runtime import style_response_candidate


INTENT_KEYWORDS = DEFAULT_INTENT_KEYWORDS



def keyword_match(text: str, words: list[str]) -> bool:
    lower = text.lower()
    return any(word in lower for word in words)


def heuristic_classify(text: str, memory: dict, bot_config: dict) -> dict[str, Any]:
    lower = text.lower()
    intent = "general"
    for candidate, words in resolve_intent_keywords(bot_config).items():
        if keyword_match(lower, words):
            intent = candidate
            break

    if intent == "human":
        requested_human = True
    else:
        requested_human = keyword_match(lower, bot_config.get("handoff", {}).get("sensitive_keywords", []))

    if intent == "schedule":
        stage = "qualified"
        score_delta = 25
    elif intent == "pricing":
        stage = "qualified"
        score_delta = 20
    elif intent in {"faq", "greeting"}:
        stage = memory.get("lead_stage") or "contacted"
        score_delta = 5
    elif intent == "complaint":
        stage = memory.get("lead_stage") or "contacted"
        score_delta = -10
        requested_human = True
    else:
        stage = memory.get("lead_stage") or "contacted"
        score_delta = 0

    objection = ""
    if any(token in lower for token in ["caro", "precio", "price", "pricing", "cost", "expensive"]):
        objection = "price"
    elif any(token in lower for token in ["después", "despues", "luego", "later", "not now", "another time"]):
        objection = "timing"
    elif any(token in lower for token in ["confianza", "seguro", "trust", "safe", "legit"]):
        objection = "trust"

    sentiment = "neutral"
    if intent == "complaint":
        sentiment = "negative"
    elif intent in {"schedule", "pricing"}:
        sentiment = "positive"

    interest = None
    for service in bot_config.get("business_knowledge", {}).get("services", []):
        if service.lower() in lower:
            interest = service
            break

    return {
        "intent": intent,
        "lead_stage": stage,
        "objection": objection,
        "score_delta": score_delta,
        "requested_human": requested_human,
        "sentiment": sentiment,
        "interest": interest,
        "urgency_level": "high" if requested_human or intent == "complaint" else ("medium" if intent in {"pricing", "schedule", "payment", "support", "followup"} else "normal"),
        "urgency_score": 70 if requested_human or intent == "complaint" else (45 if intent in {"pricing", "schedule", "payment", "support", "followup"} else 10),
    }


def call_openai_classification(
    conn,
    *,
    organization_id: str | None,
    bot_id: str | None,
    conversation_id: str | None,
    text: str,
    bot_config: dict,
    memory: dict,
) -> dict[str, Any] | None:
    if not settings.openai_api_key or conn is None:
        return None

    schema = {
        "name": "waos_classifier",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string"},
                "lead_stage": {"type": "string"},
                "objection": {"type": "string"},
                "score_delta": {"type": "integer"},
                "requested_human": {"type": "boolean"},
                "sentiment": {"type": "string"},
                "interest": {"type": "string"},
                "urgency_level": {"type": "string"},
                "urgency_score": {"type": "integer"},
            },
            "required": [
                "intent",
                "lead_stage",
                "objection",
                "score_delta",
                "requested_human",
                "sentiment",
                "interest",
                "urgency_level",
                "urgency_score",
            ],
            "additionalProperties": False,
        },
    }
    optimization = ai_optimization_settings()
    memory_profile = memory_runtime_settings()
    batch_messages = _recent_inbound_batch(
        conn,
        conversation_id=conversation_id,
        fallback_text=text,
        window_seconds=int(optimization.get('micro_batch_window_seconds') or 20),
        max_messages=int(optimization.get('micro_batch_max_messages') or 4),
    ) if optimization.get('micro_batch_enabled', True) else [text]
    cached_knowledge = search_knowledge_embeddings_cached(
        conn,
        organization_id=organization_id or '',
        bot_id=bot_id or '',
        query=text,
        limit=4,
        ttl_seconds=int(optimization.get('knowledge_search_cache_ttl_seconds') or 21600),
    ) if organization_id and bot_id else []
    episodic_recall = search_memory_episodes(
        conn,
        organization_id=organization_id or '',
        contact_id=memory.get('_contact_id'),
        bot_id=bot_id,
        query=text,
        include_cross_bot=bool(memory_profile.get('cross_bot_intelligence_enabled', True)),
        limit=int(memory_profile.get('episode_search_limit') or 4),
        hours_window=int(memory_profile.get('session_window_hours') or 72),
    ) if organization_id else []
    base_payload = {
        "message": text,
        "message_batch": batch_messages,
        "memory": memory,
        "relationship_intelligence": relationship_snapshot(memory),
        "bot_identity": bot_config.get("identity", {}),
        "objective": bot_config.get("objective", {}),
        "services": bot_config.get("business_knowledge", {}).get("services", []),
        "language_context": memory.get("_language_context", {}),
        "voice_context": memory.get("_recent_voice_context", []),
        "retrieved_knowledge": [item.get("content_text") for item in cached_knowledge],
        "episodic_memory": [item.get("summary_text") for item in episodic_recall],
        "memory_recall": [item.get("content_text") for item in search_memory_vectors(conn, organization_id=organization_id or '', contact_id=memory.get('_contact_id'), bot_id=bot_id, query=text, limit=3)] if organization_id else [],
    }
    compressed_payload, compression = compress_prompt_payload(base_payload, char_budget=int(optimization.get('classification_char_budget') or 2200))
    cached = lookup_ai_cache(conn, organization_id=organization_id, bot_id=bot_id, cache_type='classification', payload=compressed_payload, min_similarity=float(optimization.get('semantic_cache_similarity_classification') or 0.96))
    if cached:
        metadata = cached.get('metadata') or {}
        response_json = metadata.get('response_json') or {}
        record_ai_usage(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, model=metadata.get('model') or settings.openai_model, operation='classification', prompt_tokens=0, completion_tokens=0, latency_ms=0, cache_hit=True, fallback_source='semantic_cache', metadata={'cache_match': cached.get('match'), 'similarity': cached.get('similarity')})
        return response_json or None

    allowed, breaker, _policy = circuit_guard(
        conn,
        provider='openai',
        circuit_key=f'classification:{bot_id or "global"}',
        organization_id=organization_id,
        metadata={'module': 'ai.classification', 'bot_id': bot_id, 'conversation_id': conversation_id},
    )
    if not allowed:
        record_ai_usage(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, model=settings.openai_model, operation='classification', prompt_tokens=0, completion_tokens=0, latency_ms=0, cache_hit=False, fallback_source='circuit_open', metadata={'breaker': breaker})
        return None

    selected_model = choose_model(str(optimization.get('fast_model') or settings.openai_model), operation='classification', input_text=text)
    payload = {
        "model": selected_model,
        "instructions": (
            "Clasifica un mensaje de WhatsApp comercial. "
            "No generes respuesta al cliente. "
            "Responde solo con el JSON solicitado."
        ),
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": to_json(compressed_payload)}],
            }
        ],
        "text": {"format": {"type": "json_schema", "name": schema["name"], "schema": schema["schema"], "strict": True}},
    }
    started = time.perf_counter()
    try:
        response = httpx.post(
            f"{settings.openai_base_url}/responses",
            headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=20.0,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        data = response.json()
        output_text = data.get("output_text")
        if output_text:
            import json as _json

            parsed = _json.loads(output_text)
            usage = data.get('usage') or {}
            prompt_tokens = int(usage.get('input_tokens') or usage.get('prompt_tokens') or max(1, len(to_json(compressed_payload)) // 4))
            completion_tokens = int(usage.get('output_tokens') or usage.get('completion_tokens') or max(1, len(output_text) // 4))
            record_ai_usage(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, model=selected_model, operation='classification', prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, latency_ms=latency_ms, cache_hit=False, metadata={'compression': compression})
            store_ai_cache(conn, organization_id=organization_id, bot_id=bot_id, cache_scope='bot', cache_type='classification', payload=compressed_payload, response_json=parsed, ttl_seconds=max(300, settings.runtime_cache_ttl_seconds * 30))
            record_provider_success(
                conn,
                provider='openai',
                circuit_key=f'classification:{bot_id or "global"}',
                organization_id=organization_id,
                metadata={'module': 'ai.classification', 'latency_ms': latency_ms, 'model': selected_model, 'bot_id': bot_id},
            )
            return parsed
    except Exception as exc:
        record_provider_failure(
            conn,
            provider='openai',
            circuit_key=f'classification:{bot_id or "global"}',
            error_text=str(exc),
            organization_id=organization_id,
            metadata={'module': 'ai.classification', 'bot_id': bot_id, 'conversation_id': conversation_id},
        )
        return None
    return None


def classify_message(text: str, memory: dict, bot_config: dict, *, conn=None, organization_id: str | None = None, bot_id: str | None = None, conversation_id: str | None = None) -> dict[str, Any]:
    from ..runtime_pipeline import understand_message

    understood = understand_message(text, memory, bot_config, conn=conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id)
    return understood["classification"]


