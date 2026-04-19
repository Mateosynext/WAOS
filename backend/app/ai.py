from __future__ import annotations

import json
import re
import time
from typing import Any, Iterator

import httpx

from .config import settings
from .contact_intelligence import build_relationship_intelligence, merge_memory_json, relationship_snapshot
from .db import execute, fetch_all, fetch_one, has_column, table_exists
from .domain_events import emit_domain_event
from .policy_engine import DEFAULT_INTENT_KEYWORDS, evaluate_policy_action, resolve_intent_keywords
from .domains.language import default_language_templates, get_language_config
from .platform import append_technical_log, finish_execution_run, start_execution_run
from .telemetry_runtime import record_stage_metric
from .world_class import finish_trace_span, start_trace_span
from .repositories import create_audit_log, create_message
from .utils import add_minutes, from_json, hash_value, new_id, parse_iso, to_json, utcnow_iso
from .talent_runtime import generate_talent_reply, maybe_register_candidate_confirmation, talent_config_from_bot_config
from .runtime_settings import ai_optimization_settings, memory_runtime_settings
from .world_class import append_memory_episode, cache_efficiency_overview, choose_model, circuit_allow, circuit_record_failure, circuit_record_success, compress_prompt_payload, index_bot_knowledge, lookup_ai_cache, maybe_create_conversation_checkpoint, recent_checkpoints, record_ai_usage, search_knowledge_embeddings, search_knowledge_embeddings_cached, search_memory_episodes, search_memory_vectors, store_ai_cache, upsert_memory_vector, record_revenue_event
from .knowledge_runtime import search_governed_knowledge, sync_config_knowledge
from .response_ranking_runtime import style_response_candidate


INTENT_KEYWORDS = DEFAULT_INTENT_KEYWORDS


def keyword_match(text: str, words: list[str]) -> bool:
    lower = text.lower()
    return any(word in lower for word in words)

def _recent_inbound_batch(conn, *, conversation_id: str | None, fallback_text: str, window_seconds: int = 20, max_messages: int = 4) -> list[str]:
    if conn is None or not conversation_id:
        return [fallback_text]
    rows = fetch_all(
        conn,
        "SELECT body, created_at FROM messages WHERE conversation_id = ? AND direction = 'inbound' ORDER BY created_at DESC LIMIT ?",
        (conversation_id, max(2, max_messages)),
    )
    if not rows:
        return [fallback_text]
    latest = parse_iso(rows[0].get('created_at'))
    batched: list[str] = []
    for row in rows:
        created_at = parse_iso(row.get('created_at'))
        if latest and created_at and (latest - created_at).total_seconds() > max(1, int(window_seconds)):
            continue
        body = str(row.get('body') or '').strip()
        if body:
            batched.append(body)
    batched = list(reversed(batched))
    if not batched:
        return [fallback_text]
    if fallback_text.strip() and fallback_text.strip() not in batched:
        batched.append(fallback_text.strip())
    return batched[-max(1, max_messages):]


def _instant_knowledge_response(text: str, classification: dict[str, Any], bot_config: dict[str, Any], knowledge_hits: list[dict[str, Any]], language: str) -> dict[str, Any] | None:
    business = dict(bot_config.get('business_knowledge') or {})
    lower = text.lower()
    faq_threshold = float(ai_optimization_settings().get('faq_instant_match_threshold') or 0.92)
    for faq in business.get('faqs') or []:
        if not isinstance(faq, dict):
            continue
        question = str(faq.get('q') or '').strip().lower()
        answer = str(faq.get('a') or '').strip()
        if not question or not answer:
            continue
        q_tokens = {token for token in re.findall(r"\w+", question) if len(token) >= 4}
        t_tokens = {token for token in re.findall(r"\w+", lower) if len(token) >= 4}
        overlap = (len(q_tokens & t_tokens) / max(1, len(q_tokens))) if q_tokens else 0.0
        if question == lower or overlap >= 0.6:
            return {'text': answer, 'source': 'instant_knowledge', 'matched': {'knowledge_type': 'faq', 'question': faq.get('q'), 'score': round(overlap, 2)}}
    for hit in knowledge_hits:
        similarity = float(hit.get('similarity') or 0)
        content = str(hit.get('content_text') or '').strip()
        metadata = hit.get('metadata') or {}
        knowledge_type = str(hit.get('knowledge_type') or metadata.get('knowledge_type') or '')
        if knowledge_type == 'faq' and similarity >= faq_threshold and content:
            answer = content.split(':', 1)[-1].strip() if ':' in content else content
            return {'text': answer, 'source': 'instant_knowledge', 'matched': hit}
    if classification.get('intent') in {'faq', 'greeting', 'general'}:
        if any(token in lower for token in ['horario', 'hora', 'hours', 'abren', 'cierran', 'open', 'close']) and business.get('hours'):
            return {'text': _pair_by_language(language, f"Nuestro horario es {business.get('hours')}.", f"Our hours are {business.get('hours')}.") , 'source': 'instant_knowledge', 'matched': {'knowledge_type': 'hours'}}
        if any(token in lower for token in ['direccion', 'ubicacion', 'location', 'where', 'donde', 'address']) and business.get('location'):
            return {'text': _pair_by_language(language, f"Estamos en {business.get('location')}.", f"We are located at {business.get('location')}.") , 'source': 'instant_knowledge', 'matched': {'knowledge_type': 'location'}}
    return None


def stream_generated_text_chunks(text: str, *, chunk_size: int = 40) -> Iterator[str]:
    clean = str(text or '').strip()
    if not clean:
        return iter(())
    parts = [clean[i:i + max(10, chunk_size)] for i in range(0, len(clean), max(10, chunk_size))]
    return iter(parts)



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
    from .runtime_pipeline import understand_message

    understood = understand_message(text, memory, bot_config, conn=conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id)
    return understood["classification"]


def decide_action(*, conversation: dict, bot: dict, classification: dict, memory: dict, bot_config: dict | None = None) -> dict[str, Any]:
    bot_config = bot_config or {}
    now = parse_iso(utcnow_iso())
    paused_until = parse_iso(conversation.get("paused_until"))
    freeze_until = parse_iso(conversation.get("automation_freeze_until"))

    if bot["status"] != "active":
        return {"action": "no_reply", "reason": "bot_inactive"}
    if int(bot["ai_paused"]) == 1:
        return {"action": "no_reply", "reason": "bot_ai_paused"}
    if conversation["status"] in {"paused", "blocked", "closed"}:
        return {"action": "no_reply", "reason": f"conversation_{conversation['status']}"}
    if int(conversation["human_takeover"]) == 1 or int(conversation["ai_active"]) == 0:
        return {"action": "no_reply", "reason": "human_takeover"}
    if paused_until and now and now < paused_until:
        return {"action": "no_reply", "reason": "paused_until"}
    profile = relationship_snapshot(memory)
    talent_config = talent_config_from_bot_config(bot_config)
    if classification.get("profile_type") == "worker" and (talent_config.get("worker_recognition", {}) or {}).get("route_worker_to_human"):
        return {"action": "handoff", "reason": "worker_detected", "policy": "talent_worker_route"}
    policy_decision = evaluate_policy_action(conversation=conversation, classification=classification, memory=memory, bot_config=bot_config or {})
    if policy_decision:
        return policy_decision
    if classification.get("requested_human"):
        return {"action": "handoff", "reason": "requested_human"}

    next_score = max(0, min(100, int(memory.get("lead_score", 0)) + int(classification.get("score_delta", 0))))
    urgency_score = int(classification.get("urgency_score", profile.get("urgency_score", 0)) or 0)
    if classification.get("intent") == "complaint" and urgency_score >= 60:
        return {"action": "handoff", "reason": "complaint_high_urgency"}
    if next_score >= 90 and classification.get("intent") == "schedule":
        return {"action": "respond_and_schedule_followup", "reason": "hot_lead_schedule"}
    if urgency_score >= 85 and profile.get("relation_key") in {"family", "personal", "team"}:
        return {"action": "respond", "reason": "known_contact_critical"}
    if freeze_until and now and now < freeze_until:
        return {"action": "respond", "reason": "respond_during_freeze_no_job"}
    return {"action": "respond", "reason": "default"}


def _find_price(bot_config: dict) -> str | None:
    prices = bot_config.get("business_knowledge", {}).get("prices", [])
    if prices:
        first = prices[0]
        if isinstance(first, dict):
            return f"{first.get('name', 'Servicio')}: {first.get('price', '')}".strip(": ")
        return str(first)
    return None


def _find_faq_answer(text: str, bot_config: dict) -> str | None:
    faqs = bot_config.get("business_knowledge", {}).get("faqs", [])
    lower = text.lower()
    for faq in faqs:
        if isinstance(faq, dict):
            q = faq.get("q", "").lower()
            if q and any(term in lower for term in re.findall(r"\w+", q)[:3]):
                return faq.get("a")
    if any(token in lower for token in ["horario", "hours", "open", "opening"]):
        return bot_config.get("business_knowledge", {}).get("hours")
    if any(token in lower for token in ["ubic", "donde", "direcc", "where", "location", "address"]):
        return bot_config.get("business_knowledge", {}).get("location")
    return None


def _supported_languages(bot_config: dict, language_config: dict[str, Any] | None = None) -> list[str]:
    multilingual = (bot_config.get("v7_modules", {}) or {}).get("multilingual", {}) or {}
    configured = multilingual.get("supported_languages") or []
    if language_config:
        configured = list(configured) + list(language_config.get("supported_languages") or [])
    configured = [str(item).lower() for item in configured if item]
    if not configured:
        configured = [str(bot_config.get("identity", {}).get("language") or "es").lower(), "en"]
    unique: list[str] = []
    for item in configured + ["es", "en"]:
        if item not in unique:
            unique.append(item)
    return unique


def _detect_contact_language(text: str, recent_messages: list[dict[str, Any]] | None = None, bot_config: dict | None = None, voice_context: list[dict[str, Any]] | None = None, language_config: dict[str, Any] | None = None) -> str:
    supported = _supported_languages(bot_config or {}, language_config)
    samples = [text.lower()]
    for message in recent_messages or []:
        body = str(message.get("body") or "").strip().lower()
        if body:
            samples.append(body)
    for note in voice_context or []:
        detected = str(note.get("detected_language") or "").lower().strip()
        if detected in supported:
            return detected
        transcript = str(note.get("transcript") or note.get("summary") or "").lower().strip()
        if transcript:
            samples.append(transcript)
    combined = " ".join(samples)
    english_markers = ["hello", "hi", "hey", "price", "pricing", "book", "booking", "hours", "where", "location", "need", "help", "can you", "please", "follow up"]
    spanish_markers = ["hola", "precio", "cotizacion", "agendar", "horario", "donde", "necesito", "ayuda", "puedes", "por favor", "seguimiento"]
    english_score = sum(1 for marker in english_markers if marker in combined)
    spanish_score = sum(1 for marker in spanish_markers if marker in combined)
    if english_score > spanish_score and "en" in supported:
        return "en"
    if spanish_score >= english_score and "es" in supported:
        return "es"
    default_language = str((language_config or {}).get("default_language") or (bot_config or {}).get("identity", {}).get("language") or "es").lower()
    return default_language if default_language in supported else supported[0]


def _detect_customer_tone(text: str, recent_messages: list[dict[str, Any]] | None = None, voice_context: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    combined_parts = [text.lower()]
    for message in recent_messages or []:
        body = str(message.get("body") or "").lower().strip()
        if body:
            combined_parts.append(body)
    combined = " ".join(combined_parts)
    formal = any(token in combined for token in ["buen día", "buen dia", "buenas tardes", "por favor", "could you", "please", "good morning"])
    humorous = any(token in combined for token in ["jaja", "jajaja", "jeje", "haha", "lol", "lmao", "trastes", "arregla la vida"])
    overwhelmed = _looks_overwhelmed(combined)
    direct = len(text.split()) <= 5 or any(token in combined for token in ["price", "precio", "book", "agenda", "quote", "cotiza"])
    voice_emotions = [str(note.get("emotion") or "").lower() for note in (voice_context or [])]
    voice_urgency = [str(note.get("urgency_level") or "").lower() for note in (voice_context or [])]
    emotion = "neutral"
    if "negativa" in voice_emotions or "negative" in voice_emotions:
        emotion = "negative"
    elif "positiva" in voice_emotions or "positive" in voice_emotions:
        emotion = "positive"
    if overwhelmed:
        emotion = "negative"
    return {
        "style": "formal" if formal and not humorous else "casual",
        "humor_open": humorous,
        "overwhelmed": overwhelmed,
        "direct": direct,
        "emotion": emotion,
        "urgency": "high" if any(item in {"alta", "high"} for item in voice_urgency) else "normal",
    }


def _pair_by_language(language: str, es: str, en: str) -> str:
    return en if language == "en" else es


def _language_voice_layer(language: str, language_config: dict[str, Any] | None = None) -> dict[str, Any]:
    templates = (language_config or {}).get("templates") or default_language_templates()
    default_language = str((language_config or {}).get("default_language") or "es").lower()
    selected = templates.get(language) or templates.get(default_language) or templates.get("es") or {}
    return {
        "language": language,
        "welcome": selected.get("welcome"),
        "human_handoff": selected.get("human_handoff"),
        "voice_profile": selected.get("voice_profile", {}),
        "tone_matrix": selected.get("tone_matrix", {}),
        "phrase_bank": selected.get("phrase_bank", {}),
    }


def _tone_mode(tone_context: dict[str, Any] | None = None) -> str:
    tone_context = tone_context or {}
    if tone_context.get("overwhelmed"):
        return "overwhelmed"
    if tone_context.get("humor_open"):
        return "playful"
    if tone_context.get("style") == "formal":
        return "formal"
    if tone_context.get("direct"):
        return "direct"
    return "casual"


def _tone_phrase(language: str, tone_context: dict[str, Any] | None, language_config: dict[str, Any] | None, slot: str) -> str:
    layer = _language_voice_layer(language, language_config)
    matrix = layer.get("tone_matrix", {})
    mode = _tone_mode(tone_context)
    selected = matrix.get(mode) or matrix.get("casual") or {}
    value = str(selected.get(slot) or "").strip()
    if value:
        return value
    fallback = {
        "ack": _pair_by_language(language, "te sigo", "I got you"),
        "bridge": _pair_by_language(language, "te lo aterrizo fácil", "here is the simple version"),
        "close": _pair_by_language(language, "si quieres, lo vemos a tu caso", "if you want, I can make it specific to your setup"),
    }
    return fallback.get(slot, "")


def _looks_like_humor_or_odd_question(text: str) -> bool:
    lower = text.lower()
    humor_markers = [
        "jaja",
        "jajaja",
        "jeje",
        "haha",
        "lol",
        "trastes",
        "arregla la vida",
        "fix my life",
        "3 am",
        "guaderia",
        "guarderia",
        "clon",
        "clone",
        "monte",
        "soñe",
        "sone",
        "o que",
        "or what",
    ]
    return any(marker in lower for marker in humor_markers) or text.strip().endswith("?")


def _looks_overwhelmed(text: str) -> bool:
    lower = text.lower()
    stress_markers = [
        "ahogado",
        "hasta el cuello",
        "harto",
        "caos",
        "prendido fuego",
        "incendio",
        "me quiero ir al monte",
        "satur",
        "cansado",
        "quema",
        "no doy abasto",
        "overwhelmed",
        "burned out",
        "too much",
        "drowning",
        "swamped",
        "chaos",
    ]
    return any(marker in lower for marker in stress_markers)


def _build_general_reframe(
    text: str,
    bot_config: dict,
    business: str,
    language: str,
    tone_context: dict[str, Any] | None = None,
    voice_context: list[dict[str, Any]] | None = None,
    language_config: dict[str, Any] | None = None,
) -> str:
    services = bot_config.get("business_knowledge", {}).get("services", [])
    service_hint = services[0] if services else ("this" if language == "en" else "esto")
    lower = text.lower()
    tone_context = tone_context or {}
    voice_context = voice_context or []
    voice_note = voice_context[0] if voice_context else {}
    voice_summary = str(voice_note.get("summary") or "").strip()
    ack = _tone_phrase(language, tone_context, language_config, "ack")
    bridge = _tone_phrase(language, tone_context, language_config, "bridge")
    close_hint = _tone_phrase(language, tone_context, language_config, "close")
    if _looks_overwhelmed(text) or tone_context.get("overwhelmed"):
        base = _pair_by_language(
            language,
            f"{ack}, {bridge}. WAOS te ayuda a responder mejor, dar seguimiento y no dejar conversaciones tiradas.",
            f"{ack}. {bridge}. WAOS helps you reply better, follow up, and keep conversations from getting dropped.",
        )
        close = _pair_by_language(
            language,
            close_hint or "¿Qué te está drenando más ahorita: responder, cotizar, agendar o seguir clientes?",
            close_hint or "What is draining you the most right now: replying, quoting, booking, or following up?",
        )
        return f"{base} {close}".strip()
    if _looks_like_humor_or_odd_question(text):
        opener = _pair_by_language(
            language,
            ack if any(token in lower for token in ["jaja", "jeje"]) else "te sigo",
            ack if any(token in lower for token in ["haha", "lol", "lmao"]) else "I got you",
        )
        body = _pair_by_language(
            language,
            f"{bridge}. Aunque la pregunta venga medio rara, ahí también se ve el problema real del negocio: no conviene que una venta se enfríe por falta de respuesta o seguimiento. WAOS entra justo ahí para contestar con criterio, mover la conversación y ayudarte a vender sin que todo dependa de ti.",
            f"{bridge}. Even when the question comes in a little sideways, it still points to the real business issue: you do not want a sale cooling off because nobody handled the replies or follow-up. That is exactly where WAOS comes in to answer with judgment, move the conversation, and help you sell without everything depending on you.",
        )
        close = _pair_by_language(
            language,
            close_hint or "¿En tu caso dónde se atora más: respuestas, seguimiento o cierre?",
            close_hint or "In your case, where does it get stuck more: replies, follow-up, or closing?",
        )
        return f"{opener}. {body} {close}".strip()
    context_line = ""
    if voice_summary:
        context_line = _pair_by_language(
            language,
            f" También traigo contexto reciente de un audio: {voice_summary}.",
            f" I also have recent context from a voice note: {voice_summary}.",
        )
    base = _pair_by_language(
        language,
        f"{ack}. {bridge}. Te ayudo con {business}.",
        f"{ack}. {bridge}. I can help with {business}.",
    )
    value = _pair_by_language(
        language,
        "WAOS te puede ayudar a responder mejor, ordenar conversaciones y mover gente hacia el siguiente paso.",
        "WAOS can help you reply better, organize conversations, and move people to the next step.",
    )
    close = _pair_by_language(
        language,
        close_hint or f"¿Quieres que te lo aterrice a {service_hint} o al proceso que hoy más se te atora?",
        close_hint or f"Do you want me to map it to {service_hint} or to the part of your process that gets stuck the most today?",
    )
    return f"{base}{context_line} {value} {close}".strip()


def heuristic_generate(
    text: str,
    classification: dict,
    bot_config: dict,
    memory: dict,
    recent_messages: list[dict[str, Any]] | None = None,
    voice_context: list[dict[str, Any]] | None = None,
    language_config: dict[str, Any] | None = None,
) -> str:
    talent_reply = generate_talent_reply(text, classification, bot_config, memory)
    if talent_reply:
        return talent_reply
    identity = bot_config.get("identity", {})
    business = identity.get("business_name", "the business")
    services = bot_config.get("business_knowledge", {}).get("services", [])
    hours = bot_config.get("business_knowledge", {}).get("hours", "")
    location = bot_config.get("business_knowledge", {}).get("location", "")
    promotions = bot_config.get("business_knowledge", {}).get("promotions", [])
    promo = promotions[0] if promotions else ""
    language = _detect_contact_language(text, recent_messages, bot_config, voice_context, language_config)
    tone_context = _detect_customer_tone(text, recent_messages, voice_context)

    intent = classification.get("intent")
    profile = relationship_snapshot(memory)
    known_contact = bool(profile.get("known_contact"))
    relation_label = str(profile.get("relation_label") or "")
    urgency_level = str(classification.get("urgency_level") or profile.get("urgency_level") or "normal").lower()
    if intent == "greeting":
        services_text = ", ".join(services[:3]) if services else _pair_by_language(language, "nuestros servicios", "our services")
        ack = _tone_phrase(language, tone_context, language_config, "ack")
        bridge = _tone_phrase(language, tone_context, language_config, "bridge")
        if known_contact and relation_label in {"familia", "conocido"}:
            return _pair_by_language(
                language,
                f"{ack}. Qué gusto leerte. Ya te ubico como {relation_label} y te ayudo rápido. ¿Qué necesitas hoy?",
                f"{ack}. Good to hear from you again. I already recognize you, and I can help quickly. What do you need today?",
            )
        return _pair_by_language(
            language,
            f"{ack}. Soy {identity.get('bot_name', 'tu asistente')} de {business}. Te ayudo con {services_text} y {bridge}. ¿Qué te gustaría resolver hoy?",
            f"{ack}. I'm {identity.get('bot_name', 'your assistant')} from {business}. I can help with {services_text}, and {bridge}. What would you like to solve today?",
        )
    if intent == "pricing":
        price = _find_price(bot_config)
        if price:
            return _pair_by_language(
                language,
                f"Claro. Tengo este dato disponible: {price}. Si te ayuda, tambien puedo revisar disponibilidad para agendar.{(' Además, ' + str(promo)) if promo and language == 'es' else ''}",
                f"Sure. I have this available right now: {price}. If it helps, I can also check availability and get the next step moving.{(' Also, ' + str(promo)) if promo and language == 'en' else ''}",
            )
        return _pair_by_language(
            language,
            "Con gusto te ayudo con precios. En este momento no tengo una tarifa exacta configurada para compartirte por este chat, pero puedo ayudarte a avanzar o pasarte con un asesor.",
            "Happy to help with pricing. I do not have an exact rate configured to share in this chat right now, but I can still help you move forward or hand you off to an advisor.",
        )
    if intent == "schedule":
        hours_text = _pair_by_language(language, f" Nuestro horario es {hours}." if hours else "", f" Our hours are {hours}." if hours else "")
        return _pair_by_language(
            language,
            f"Perfecto, te ayudo a agendar.{hours_text} ¿Que dia u horario te funciona mejor?",
            f"Perfect, I can help you book it.{hours_text} What day or time works best for you?",
        )
    if intent == "faq":
        answer = _find_faq_answer(text, bot_config)
        if answer:
            close = _pair_by_language(language, " Si quieres, de una vez te ayudo a agendar, comparar opciones o resolver la siguiente duda.", " If you want, I can also help you book, compare options, or solve the next question right away.")
            return f"{answer}{close}".strip()
        return _build_general_reframe(text, bot_config, business, language, tone_context, voice_context, language_config)
    if intent == "complaint":
        return _pair_by_language(
            language,
            "Si te creo, eso ya merece que lo vea alguien del equipo con mas contexto. Voy a escalar tu caso con una persona para que te atiendan bien.",
            "I hear you. That already deserves a person from the team with more context. I am going to escalate your case so someone can handle it properly.",
        )
    if intent == "human":
        return _pair_by_language(
            language,
            "Claro, te paso con un asesor humano para que lo vean contigo.",
            "Of course, I can hand you off to a human advisor so they can review it with you.",
        )
    if classification.get("objection") == "price":
        return _pair_by_language(
            language,
            "Si, el precio pesa. Si quieres, te ayudo a ver la opcion que mejor te cuadre o revisar si aplica alguna promocion.",
            "Yes, price matters. If you want, I can help you find the option that fits best or check whether any promotion applies.",
        )
    if urgency_level in {"high", "critical"} and known_contact and relation_label in {"familia", "conocido"}:
        return _pair_by_language(
            language,
            "Ya lo vi y te doy prioridad. Cuéntame en una línea qué necesitas para moverlo rápido.",
            "I saw it and I am prioritizing it. Tell me in one line what you need so I can move it fast.",
        )
    if location:
        return _pair_by_language(
            language,
            f"Con gusto te ayudo con {business}. Estamos en {location}. Y si la duda viene medio rara tambien te la aterrizo. ¿Buscas precio, horario, agendar o seguimiento?",
            f"Happy to help with {business}. We are located at {location}. And if the question comes in sideways, I can still ground it for you. Are you looking for pricing, hours, booking, or follow-up?",
        )
    return _build_general_reframe(text, bot_config, business, language, tone_context, voice_context, language_config)


def call_openai_generation(
    conn,
    *,
    organization_id: str | None,
    bot_id: str | None,
    conversation_id: str | None,
    input_text: str,
    classification: dict[str, Any],
    prompt_payload: dict[str, Any],
) -> str | None:
    if not settings.openai_api_key or conn is None:
        return None
    optimization = ai_optimization_settings()
    compressed_payload, compression = compress_prompt_payload(prompt_payload, char_budget=int(optimization.get('generation_char_budget') or 2600))
    cached = lookup_ai_cache(conn, organization_id=organization_id, bot_id=bot_id, cache_type='generation', payload=compressed_payload, min_similarity=float(optimization.get('semantic_cache_similarity_generation') or 0.94))
    if cached:
        metadata = cached.get('metadata') or {}
        response_text = cached.get('row', {}).get('response_text') or metadata.get('response_text')
        if response_text:
            record_ai_usage(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, model=metadata.get('model') or settings.openai_model, operation='generation', prompt_tokens=0, completion_tokens=0, latency_ms=0, cache_hit=True, fallback_source='semantic_cache', metadata={'cache_match': cached.get('match'), 'similarity': cached.get('similarity')})
            return response_text

    allowed, breaker, _policy = circuit_guard(
        conn,
        provider='openai',
        circuit_key=f'generation:{bot_id or "global"}',
        organization_id=organization_id,
        metadata={'module': 'ai.generation', 'bot_id': bot_id, 'conversation_id': conversation_id},
    )
    if not allowed:
        record_ai_usage(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, model=settings.openai_model, operation='generation', prompt_tokens=0, completion_tokens=0, latency_ms=0, cache_hit=False, fallback_source='circuit_open', metadata={'breaker': breaker})
        return None

    selected_model = choose_model(str(optimization.get('complex_model') or settings.openai_model), operation='generation', input_text=input_text, classification=classification)
    payload = {
        'model': selected_model,
        'instructions': (
            'Eres un agente de WhatsApp de negocio. Responde breve, clara y natural. '
            'Por ahora puedes hablar en español y en inglés, y debes responder en el idioma del cliente usando texto y, si existe, el contexto reciente de voz. '
            'Usa una voz nativa por idioma: en español suena cercano, claro y con barrio bien presentado; en inglés suena natural, sharp y nada traducido raro. '
            'Entiende el tono de voz del cliente (formal, casual, urgente, cansado, bromista) y adaptate sin perder una voz cercana, profesional y comercial. '
            'Nunca te quedes seco si el cliente bromea, pregunta algo raro, cambia de tema o se desahoga. '
            'Valida el momento, usa humor ligero solo cuando sume, reencauza al negocio y deja siempre un siguiente paso. '
            'No inventes precios, politicas ni disponibilidad no configuradas. '
            'Si falta un dato, dilo con honestidad y redirige a algo util y comercial. '
            'Nunca suenes tecnico, robotico ni corporativo.'
        ),
        'input': [
            {
                'role': 'user',
                'content': [{'type': 'input_text', 'text': to_json(compressed_payload)}],
            }
        ],
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
        output_text = data.get('output_text')
        if output_text:
            usage = data.get('usage') or {}
            prompt_tokens = int(usage.get('input_tokens') or usage.get('prompt_tokens') or max(1, len(to_json(compressed_payload)) // 4))
            completion_tokens = int(usage.get('output_tokens') or usage.get('completion_tokens') or max(1, len(output_text) // 4))
            record_ai_usage(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, model=selected_model, operation='generation', prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, latency_ms=latency_ms, cache_hit=False, metadata={'compression': compression, 'intent': classification.get('intent')})
            store_ai_cache(conn, organization_id=organization_id, bot_id=bot_id, cache_scope='bot', cache_type='generation', payload=compressed_payload, response_text=output_text, response_json={'model': selected_model}, ttl_seconds=max(300, settings.runtime_cache_ttl_seconds * 30))
            record_provider_success(
                conn,
                provider='openai',
                circuit_key=f'generation:{bot_id or "global"}',
                organization_id=organization_id,
                metadata={'module': 'ai.generation', 'latency_ms': latency_ms, 'model': selected_model, 'bot_id': bot_id},
            )
            return output_text
    except Exception as exc:
        record_provider_failure(
            conn,
            provider='openai',
            circuit_key=f'generation:{bot_id or "global"}',
            error_text=str(exc),
            organization_id=organization_id,
            metadata={'module': 'ai.generation', 'bot_id': bot_id, 'conversation_id': conversation_id},
        )
        return None
    return None

def generate_response(
    text: str,
    classification: dict,
    bot_config: dict,
    memory: dict,
    recent_messages: list[dict],
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
) -> tuple[str, dict[str, Any]]:
    recent_voice_notes = recent_voice_notes or []
    optimization = ai_optimization_settings()
    memory_profile = memory_runtime_settings()
    language = _detect_contact_language(text, recent_messages, bot_config, recent_voice_notes, language_config)
    tone_context = _detect_customer_tone(text, recent_messages, recent_voice_notes)
    recalled_memory = search_memory_vectors(conn, organization_id=organization_id or '', contact_id=contact_id, bot_id=bot_id, query=text, limit=4) if conn and organization_id else []
    episodic_recall = search_memory_episodes(
        conn,
        organization_id=organization_id or '',
        contact_id=contact_id,
        bot_id=bot_id,
        query=text,
        include_cross_bot=bool(memory_profile.get('cross_bot_intelligence_enabled', True)),
        limit=int(memory_profile.get('episode_search_limit') or 5),
        hours_window=int(memory_profile.get('session_window_hours') or 72),
    ) if conn and organization_id and memory_profile.get('episodic_memory_enabled', True) else []
    knowledge_hits = search_knowledge_embeddings_cached(
        conn,
        organization_id=organization_id or '',
        bot_id=bot_id or '',
        query=text,
        limit=4,
        ttl_seconds=int(optimization.get('knowledge_search_cache_ttl_seconds') or 21600),
    ) if conn and organization_id and bot_id else []
    governed_hits = search_governed_knowledge(conn, organization_id=organization_id or '', bot_id=bot_id or '', query=text, intent=classification.get('intent'), limit=4) if conn and organization_id and bot_id else []
    checkpoints = recent_checkpoints(conn, conversation_id=conversation_id, limit=2) if conn and conversation_id else []
    prompt_payload = {
        'message': text,
        'classification': classification,
        'identity': bot_config.get('identity', {}),
        'personality': bot_config.get('personality', {}),
        'objective': bot_config.get('objective', {}),
        'business_knowledge': bot_config.get('business_knowledge', {}),
        'rules': bot_config.get('rules', {}),
        'memory': memory,
        'relationship_intelligence': relationship_snapshot(memory),
        'language_context': {
            'default_language': (language_config or {}).get('default_language') or bot_config.get('identity', {}).get('language') or 'es',
            'supported_languages': _supported_languages(bot_config, language_config),
            'detected_language': language,
            'reply_in_detected_language': True,
        },
        'language_voice_layer': _language_voice_layer(language, language_config),
        'tone_of_voice_context': tone_context,
        'recent_conversation_context': [{"direction": m["direction"], "body": m["body"]} for m in recent_messages[-8:]],
        'recent_voice_context': [
            {
                'summary': note.get('summary'),
                'transcript': note.get('transcript'),
                'detected_language': note.get('detected_language'),
                'intent': note.get('intent'),
                'urgency_level': note.get('urgency_level'),
                'emotion': note.get('emotion'),
            }
            for note in recent_voice_notes[:3]
        ],
        'memory_recall': [item.get('content_text') for item in recalled_memory],
        'episodic_memory': [item.get('summary_text') for item in episodic_recall],
        'retrieved_knowledge': [item.get('content_text') for item in knowledge_hits],
        'governed_knowledge': [item.get('content_text') for item in governed_hits],
        'governed_traceability': [item.get('traceability') for item in governed_hits],
        'conversation_checkpoints': [{'summary_text': item.get('summary_text'), 'facts': item.get('facts')} for item in checkpoints],
        'execution_plan': execution_plan or {},
        'grounded_context': grounded_context or {},
        'response_ranking_candidate': candidate_spec or {},
    }
    fallback_chain: list[str] = []
    talent_reply = generate_talent_reply(text, classification, bot_config, memory)
    if talent_reply:
        fallback_chain.append('talent')
        prompt_payload['generator_source'] = 'talent'
        prompt_payload['generator_fallback_chain'] = fallback_chain
        talent_reply = style_response_candidate(
            response_text=talent_reply,
            candidate_spec=candidate_spec,
            language=language,
            classification=classification,
            bot_config=bot_config,
            execution_plan=execution_plan or {},
        )
        return talent_reply, prompt_payload
    instant_reply = _instant_knowledge_response(text, classification, bot_config, knowledge_hits, language)
    if instant_reply:
        fallback_chain.append('instant_knowledge')
        prompt_payload['instant_knowledge_match'] = instant_reply.get('matched')
        prompt_payload['generator_source'] = 'instant_knowledge'
        prompt_payload['generator_fallback_chain'] = fallback_chain
        instant_text = style_response_candidate(
            response_text=str(instant_reply.get('text') or ''),
            candidate_spec=candidate_spec,
            language=language,
            classification=classification,
            bot_config=bot_config,
            execution_plan=execution_plan or {},
        )
        return instant_text, prompt_payload
    response = call_openai_generation(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, input_text=text, classification=classification, prompt_payload=prompt_payload)
    if response:
        fallback_chain.append('openai')
        prompt_payload['generator_source'] = 'openai'
        prompt_payload['generator_fallback_chain'] = fallback_chain
        response = style_response_candidate(
            response_text=response,
            candidate_spec=candidate_spec,
            language=language,
            classification=classification,
            bot_config=bot_config,
            execution_plan=execution_plan or {},
        )
        return response, prompt_payload
    fallback_chain.extend(['openai', 'heuristic'])
    response = heuristic_generate(
        text,
        classification,
        bot_config,
        memory,
        recent_messages=recent_messages,
        voice_context=recent_voice_notes,
        language_config=language_config,
    )
    prompt_payload['generator_source'] = 'heuristic'
    prompt_payload['generator_fallback_chain'] = fallback_chain
    response = style_response_candidate(
        response_text=response,
        candidate_spec=candidate_spec,
        language=language,
        classification=classification,
        bot_config=bot_config,
        execution_plan=execution_plan or {},
    )
    return response, prompt_payload

def update_memory(conn, *, organization_id: str, contact_id: str, bot_id: str, incoming_text: str, classification: dict, contact: dict | None = None, recent_messages: list[dict[str, Any]] | None = None, conversation_id: str | None = None, source_message_id: str | None = None) -> dict:
    memory = fetch_one(conn, "SELECT * FROM contact_memory WHERE contact_id = ? AND bot_id = ?", (contact_id, bot_id))
    old_score = int(memory.get("lead_score", 0)) if memory else 0
    new_score = max(0, min(100, old_score + int(classification.get("score_delta", 0))))
    summary_parts = []
    if memory and memory.get("summary"):
        summary_parts.append(memory["summary"])
    summary_parts.append(f"Último mensaje: {incoming_text[:140]}")
    summary = " | ".join(summary_parts[-3:])
    objection = classification.get("objection") or ""
    interest = classification.get("interest") or (memory.get("interest") if memory else None)
    relation_profile = build_relationship_intelligence(
        memory=memory,
        classification=classification,
        incoming_text=incoming_text,
        contact=contact,
        recent_messages=recent_messages,
    )
    next_action = "owner_attention" if relation_profile.get("attention_tier") == "owner_now" else ("priority_followup" if relation_profile.get("urgency_level") in {"critical", "high"} else ("human_handoff" if classification.get("requested_human") else "reply"))
    followup_at = add_minutes(utcnow_iso(), 30) if relation_profile.get("urgency_level") == "critical" else (add_minutes(utcnow_iso(), 120) if classification.get("intent") in {"pricing", "schedule", "payment", "followup"} else None)
    memory_payload = merge_memory_json(memory, relation_profile)
    memory_version = "v2"
    memory_etag = hash_value(to_json(memory_payload))
    now = utcnow_iso()
    base_sql = """
        UPDATE contact_memory
        SET lead_stage = ?, lead_score = ?, interest = ?, objections = ?, summary = ?, next_action = ?, followup_at = ?, memory_json = ?, last_updated_at = ?
    """
    params = [
        classification.get("lead_stage") or "contacted",
        new_score,
        interest,
        objection,
        summary,
        next_action,
        followup_at,
        to_json(memory_payload),
        now,
    ]
    if has_column(conn, "contact_memory", "memory_version"):
        base_sql += ", memory_version = ?"
        params.append(memory_version)
    if has_column(conn, "contact_memory", "memory_etag"):
        base_sql += ", memory_etag = ?"
        params.append(memory_etag)
    if has_column(conn, "contact_memory", "operational_state_json"):
        base_sql += ", operational_state_json = ?"
        params.append(to_json({
            "intent_detected": classification.get("intent"),
            "urgency_level": relation_profile.get("urgency_level"),
            "urgency_score": relation_profile.get("urgency_score"),
            "next_action": next_action,
            "classifier_source": classification.get("_classifier_source") or "heuristic",
            "generator_source": classification.get("_generator_source"),
            "updated_at": now,
        }))
    for column, value in [
        ("urgency_level", relation_profile.get("urgency_level") or "normal"),
        ("urgency_score", int(relation_profile.get("urgency_score", 0) or 0)),
        ("known_contact", 1 if relation_profile.get("known_contact") else 0),
        ("current_intent", classification.get("intent") or relation_profile.get("current_intent")),
        ("current_mode", classification.get("current_mode") or relation_profile.get("current_mode")),
        ("last_classifier_source", classification.get("_classifier_source") or "heuristic"),
        ("last_generator_source", classification.get("_generator_source")),
    ]:
        if has_column(conn, "contact_memory", column):
            base_sql += f", {column} = ?"
            params.append(value)
    base_sql += " WHERE contact_id = ? AND bot_id = ?"
    params.extend([contact_id, bot_id])
    execute(conn, base_sql, params)
    updated = fetch_one(conn, "SELECT * FROM contact_memory WHERE contact_id = ? AND bot_id = ?", (contact_id, bot_id))
    memory_text = " | ".join([str(summary or ''), str(interest or ''), str(objection or ''), str(next_action or '')]).strip()
    if memory_text:
        upsert_memory_vector(conn, organization_id=organization_id, contact_id=contact_id, bot_id=bot_id, scope='contact_memory', content_text=memory_text, metadata={'lead_stage': classification.get('lead_stage'), 'intent': classification.get('intent'), 'next_action': next_action}, score=float(new_score))
    memory_profile = memory_runtime_settings()
    if memory_profile.get('episodic_memory_enabled', True):
        append_memory_episode(
            conn,
            organization_id=organization_id,
            contact_id=contact_id,
            bot_id=bot_id if not memory_profile.get('cross_bot_intelligence_enabled', True) else None,
            conversation_id=conversation_id,
            source_message_id=source_message_id,
            episode_type=str(classification.get('intent') or 'conversation_turn'),
            summary_text=memory_text or incoming_text[:220],
            metadata={
                'intent': classification.get('intent'),
                'lead_stage': classification.get('lead_stage'),
                'next_action': next_action,
                'cross_bot': bool(memory_profile.get('cross_bot_intelligence_enabled', True)),
                'bot_scope': 'cross_bot' if memory_profile.get('cross_bot_intelligence_enabled', True) else 'bot_only',
                'classifier_source': classification.get('_classifier_source') or 'heuristic',
            },
            score=float(new_score),
        )
    return updated


def maybe_schedule_followups(conn, *, organization_id: str, bot_id: str, conversation_id: str, contact_id: str, classification: dict, decision: dict, bot_config: dict) -> list[dict]:
    scheduled = []
    if decision["action"] not in {"respond", "respond_and_schedule_followup"}:
        return scheduled

    optimizer_context = load_optimizer_runtime_context(conn, organization_id=organization_id, bot_id=bot_id)
    rules = list(bot_config.get("followups", {}).get("rules", []) or [])
    intent = str(classification.get('intent') or 'general')
    lower_intent = intent.lower()
    if not any(str(rule.get('type')) == 'smart_scheduling' for rule in rules) and lower_intent == 'schedule':
        rules.append({'type': 'smart_scheduling', 'delay_minutes': 30, 'max_attempts': 2, 'message_template': '¿Te aparto un horario tentativo y si te funciona lo confirmamos aquí mismo?'})
    if not any(str(rule.get('type')) == 'abandoned_quote' for rule in rules) and lower_intent in {'pricing', 'payment'}:
        rules.append({'type': 'abandoned_quote', 'delay_minutes': 120, 'max_attempts': 2, 'message_template': 'Te dejo esto abierto por si quieres retomar. Si te sirve, revisamos opción, promoción o forma de pago y lo cerramos contigo.'})
    if not any(str(rule.get('type')) == 'payment_recovery' for rule in rules) and lower_intent == 'payment':
        rules.append({'type': 'payment_recovery', 'delay_minutes': 45, 'max_attempts': 3, 'message_template': 'Veo tu pago pendiente. Si quieres, te ayudo a retomarlo o te mando otra opción para completarlo.'})
    if not any(str(rule.get('type')) == 'winback' for rule in rules) and lower_intent in {'general', 'faq'}:
        rules.append({'type': 'winback', 'delay_minutes': 1440, 'max_attempts': 1, 'message_template': 'Solo vuelvo a escribirte para no dejar esto en el aire. Si te interesa, lo retomamos en dos mensajes.'})

    selected_types = {'no_response'}
    if lower_intent == 'pricing':
        selected_types.update({'post_quote', 'abandoned_quote'})
    if lower_intent == 'payment':
        selected_types.update({'payment_recovery', 'abandoned_quote'})
    if lower_intent == 'schedule':
        selected_types.update({'smart_scheduling'})
    if lower_intent in {'general', 'faq'}:
        selected_types.update({'winback'})

    for rule in rules:
        rule_type = str(rule.get("type") or '')
        if rule_type not in selected_types:
            continue
        rule = followup_override(rule, context=optimizer_context, intent=lower_intent)
        dedupe_key = f"{conversation_id}:{rule_type}"
        exists = fetch_one(
            conn,
            """
            SELECT id FROM automation_jobs
            WHERE dedupe_key = ? AND status IN ('queued', 'locked', 'retry', 'scheduled')
            """,
            (dedupe_key,),
        )
        if exists:
            continue
        delay = int(rule.get("delay_minutes", 120))
        job_id = new_id("job")
        scheduled_for = add_minutes(utcnow_iso(), delay)
        template = rule.get('message_template') or 'Solo dando seguimiento a tu consulta.'
        execute(
            conn,
            """
            INSERT INTO automation_jobs
            (id, organization_id, bot_id, conversation_id, contact_id, rule_id, job_type, dedupe_key, scheduled_for, status, attempts, payload_json, priority, created_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, 'queued', 0, ?, ?, ?)
            """,
            (
                job_id,
                organization_id,
                bot_id,
                conversation_id,
                contact_id,
                rule_type,
                dedupe_key,
                scheduled_for,
                to_json(
                    {
                        'message_template': template,
                        'max_attempts': rule.get('max_attempts', 2),
                        'recommendation_type': rule_type,
                        'classification_intent': lower_intent,
                        'channel': rule.get('channel') or 'whatsapp',
                        'timing_policy_id': rule.get('timing_policy_id'),
                        'template_version_id': rule.get('template_version_id'),
                    }
                ),
                90 if rule_type in {'payment_recovery', 'smart_scheduling'} else (80 if rule_type in {'abandoned_quote', 'post_quote'} else 45),
                utcnow_iso(),
            ),
        )
        record_revenue_event(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, contact_id=contact_id, event_type=rule_type, recommendation={'scheduled_for': scheduled_for, 'delay_minutes': delay, 'template': template}, expected_value=float(classification.get('urgency_score') or 0))
        scheduled.append(fetch_one(conn, "SELECT * FROM automation_jobs WHERE id = ?", (job_id,)))
    return scheduled

def run_ai_pipeline(conn, *, incoming_message: dict, conversation: dict, bot: dict, contact: dict, memory: dict, correlation_id: str | None = None) -> dict[str, Any]:
    pipeline_started = time.perf_counter()
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
        "voice_context": [{"summary": item.get("summary"), "detected_language": item.get("detected_language"), "intent": item.get("intent"), "urgency_level": item.get("urgency_level"), "emotion": item.get("emotion")} for item in recent_voice_notes],
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
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="runtime",
        message="Inbound accepted by runtime pipeline",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details={"message_id": incoming_message["id"]},
    )
    orchestration_span_id = new_id("span")
    start_trace_span(
        conn,
        trace_id=run["trace_id"],
        span_id=orchestration_span_id,
        parent_span_id=None,
        name="pipeline.orchestration",
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        execution_run_id=run["id"],
        correlation_id=effective_correlation_id,
        attributes={"stage": "orchestration", "source_type": "inbound_message"},
    )
    orchestration_started = time.perf_counter()

    from .agent_runtime import orchestrate_runtime_turn

    orchestrated = orchestrate_runtime_turn(
        text=incoming_message["body"],
        conversation=conversation,
        bot=bot,
        memory=memory,
        bot_config=bot_config,
        recent_messages=recent_messages,
        conn=conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        contact_id=contact["id"],
        conversation_id=conversation["id"],
        recent_voice_notes=recent_voice_notes,
        language_config=language_config,
    )
    understanding = orchestrated["understanding"]
    classification = understanding["classification"]
    grounded_context = orchestrated["grounded_context"]
    specialist_route = orchestrated.get("specialist_route") or {}
    shared_memory = orchestrated.get("shared_memory") or {}
    execution_plan = orchestrated["plan"]
    decision = orchestrated["decision"]
    supervisor = orchestrated.get("supervisor") or {}
    generated = orchestrated.get("generated")
    verification = orchestrated.get("verification")
    candidate_ranking = orchestrated.get("candidate_ranking") or {}
    memory_curation = orchestrated.get("memory_curation") or {}
    post_send_evaluation = orchestrated.get("post_send_evaluation") or {}
    self_state = orchestrated.get("self_state") or {"turn": {}, "conversation": {}}
    finish_trace_span(conn, trace_id=run["trace_id"], span_id=orchestration_span_id, status="ok", attributes={"duration_ms": int((time.perf_counter() - orchestration_started) * 1000), "stage": "orchestration"})
    record_stage_metric(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        trace_id=run["trace_id"],
        correlation_id=effective_correlation_id,
        vertical=bot.get("vertical"),
        source_type="inbound_message",
        stage_name="pipeline.orchestration",
        duration_ms=int((time.perf_counter() - orchestration_started) * 1000),
        metrics={"intent": (understanding.get("classification") or {}).get("intent")},
    )

    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="classifier",
        message="Message classified",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details=classification,
    )
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="planner",
        message="Execution plan prepared",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details={"intent": execution_plan.get("intent"), "objectives": execution_plan.get("objectives"), "risk_flags": execution_plan.get("risk_flags"), "tool_orchestration": execution_plan.get("tool_orchestration")},
    )
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="grounding",
        message="Grounded context assembled",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details={"source_count": grounded_context.get("source_count"), "coverage": grounded_context.get("coverage"), "grounding_mode": grounded_context.get("grounding_mode")},
    )
    decision_input = {
        "conversation_state": {
            "status": conversation["status"],
            "human_takeover": conversation["human_takeover"],
            "ai_active": conversation["ai_active"],
        },
        "classification": classification,
        "memory": {
            "lead_stage": memory.get("lead_stage"),
            "lead_score": memory.get("lead_score"),
        },
        "plan": execution_plan,
        "grounded_context": {
            "source_count": grounded_context.get("source_count"),
            "coverage": grounded_context.get("coverage"),
        },
        "self_state": self_state,
    }
    emit_domain_event(conn, event_name="message_classified", organization_id=conversation["organization_id"], bot_id=bot["id"], conversation_id=conversation["id"], message_id=incoming_message["id"], correlation_id=correlation_id, payload={"intent": classification.get("intent"), "source": classification.get("_classifier_source")})
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="decision",
        message="Action decided",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details=decision,
    )
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="agent_router",
        message="Intent routed to specialist agent",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details={"route": specialist_route, "supervisor": supervisor},
    )

    ai_run_id = new_id("airun")
    generator_input = {
        "execution_plan": execution_plan,
        "grounded_context": grounded_context,
        "memory_curation": memory_curation,
    }
    generator_output = None
    response_message = None
    error = None

    try:
        from .self_state_runtime import maybe_trigger_self_state_playbook, persist_self_state

        persist_self_state(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            conversation_id=conversation["id"],
            contact_id=contact["id"],
            message_id=incoming_message["id"],
            turn_self_state=self_state.get("turn") or {},
            conversation_self_state=self_state.get("conversation") or {},
        )

        if decision["action"] == "handoff":
            execute(
                conn,
                """
                UPDATE conversations
                SET status = 'human_takeover', human_takeover = 1, ai_active = 0, automation_freeze_until = ?, updated_at = ?
                WHERE id = ?
                """,
                (add_minutes(utcnow_iso(), 30), utcnow_iso(), conversation["id"]),
            )
            emit_domain_event(conn, event_name="handoff_triggered", organization_id=conversation["organization_id"], bot_id=bot["id"], conversation_id=conversation["id"], message_id=incoming_message["id"], correlation_id=correlation_id, payload={"reason": decision.get("reason"), "action": decision.get("action")})
            response_message = create_message(
                conn,
                organization_id=conversation["organization_id"],
                conversation_id=conversation["id"],
                contact_id=contact["id"],
                bot_id=bot["id"],
                direction="outbound",
                kind="text",
                source="system",
                body="He marcado esta conversación para atención humana.",
                status="internal",
                metadata={"reason": decision["reason"], "trace_id": run["trace_id"], "execution_id": run["execution_id"]},
            )
        elif decision["action"] in {"respond", "respond_and_schedule_followup", "verify", "request_missing_data"}:
            response_stage_started = time.perf_counter()
            response_span_id = new_id("span")
            start_trace_span(
                conn,
                trace_id=run["trace_id"],
                span_id=response_span_id,
                parent_span_id=None,
                name="pipeline.response",
                organization_id=conversation["organization_id"],
                bot_id=bot["id"],
                conversation_id=conversation["id"],
                execution_run_id=run["id"],
                correlation_id=effective_correlation_id,
                attributes={"stage": "response"},
            )
            response_text = (generated or {}).get("text") or ""
            generator_input = {
                **generator_input,
                "payload": (generated or {}).get("payload") or {},
                "verification": verification or {},
                "candidate_ranking": candidate_ranking,
                "post_send_evaluation": post_send_evaluation,
                "self_state": self_state,
            }
            classification["_generator_source"] = (generated or {}).get("source")
            classification["_verifier_status"] = (verification or {}).get("status")
            generator_output = {
                "text": response_text,
                "raw_text": (generated or {}).get("raw_text"),
                "source": (generated or {}).get("source"),
                "selected_variant": (candidate_ranking or {}).get("selected_variant"),
                "candidate_ranking": candidate_ranking,
                "verification": verification or {},
                "post_send_evaluation": post_send_evaluation,
            }
            append_technical_log(
                conn,
                organization_id=conversation["organization_id"],
                bot_id=bot["id"],
                execution_run_id=run["id"],
                conversation_id=conversation["id"],
                level="info",
                category="generator",
                message="Response generated",
                trace_id=run["trace_id"],
                execution_id=run["execution_id"],
                details={"preview": response_text[:160], "source": (generated or {}).get("source")},
            )
            append_technical_log(
                conn,
                organization_id=conversation["organization_id"],
                bot_id=bot["id"],
                execution_run_id=run["id"],
                conversation_id=conversation["id"],
                level="info",
                category="ranker",
                message="Multi-candidate ranking completed",
                trace_id=run["trace_id"],
                execution_id=run["execution_id"],
                details=(candidate_ranking or {}).get("summary") or {"candidate_count": 0},
            )
            append_technical_log(
                conn,
                organization_id=conversation["organization_id"],
                bot_id=bot["id"],
                execution_run_id=run["id"],
                conversation_id=conversation["id"],
                level="info",
                category="verifier",
                message="Reply verified before send",
                trace_id=run["trace_id"],
                execution_id=run["execution_id"],
                details=verification or {"status": "not_required"},
            )
            append_technical_log(
                conn,
                organization_id=conversation["organization_id"],
                bot_id=bot["id"],
                execution_run_id=run["id"],
                conversation_id=conversation["id"],
                level="info",
                category="evaluation",
                message="Post-send evaluation completed",
                trace_id=run["trace_id"],
                execution_id=run["execution_id"],
                details=post_send_evaluation,
            )
            response_message = create_message(
                conn,
                organization_id=conversation["organization_id"],
                conversation_id=conversation["id"],
                contact_id=contact["id"],
                bot_id=bot["id"],
                direction="outbound",
                kind="text",
                source="ai",
                body=response_text,
                status="simulated",
                metadata={"provider": "simulated", "trace_id": run["trace_id"], "execution_id": run["execution_id"], "correlation_id": correlation_id, "verification": verification or {}, "candidate_ranking": (candidate_ranking or {}).get("summary") or {}, "post_send_evaluation": post_send_evaluation},
                correlation_id=correlation_id,
            )
            emit_domain_event(conn, event_name="reply_generated", organization_id=conversation["organization_id"], bot_id=bot["id"], conversation_id=conversation["id"], message_id=response_message.get("id"), correlation_id=correlation_id, payload={"source": (generated or {}).get("source"), "action": decision.get("action"), "verification_status": (verification or {}).get("status")})
            execute(
                conn,
                "UPDATE conversations SET status = 'ai_active', last_ai_at = ?, updated_at = ? WHERE id = ?",
                (utcnow_iso(), utcnow_iso(), conversation["id"]),
            )
            response_duration_ms = int((time.perf_counter() - response_stage_started) * 1000)
            finish_trace_span(conn, trace_id=run["trace_id"], span_id=response_span_id, status="ok", attributes={"duration_ms": response_duration_ms, "stage": "response"})
            record_stage_metric(
                conn,
                organization_id=conversation["organization_id"],
                bot_id=bot["id"],
                conversation_id=conversation["id"],
                trace_id=run["trace_id"],
                correlation_id=effective_correlation_id,
                vertical=bot.get("vertical"),
                source_type="inbound_message",
                stage_name="pipeline.response",
                duration_ms=response_duration_ms,
                metrics={"generator_source": (generated or {}).get("source")},
            )
        elif decision["action"] == "trigger_playbook":
            playbook_result = maybe_trigger_self_state_playbook(
                conn,
                organization_id=conversation["organization_id"],
                bot_id=bot["id"],
                contact_id=contact["id"],
                conversation_id=conversation["id"],
                decision=decision,
            )
            generator_output = {"playbook_result": playbook_result, "self_state": self_state}
            response_message = create_message(
                conn,
                organization_id=conversation["organization_id"],
                conversation_id=conversation["id"],
                contact_id=contact["id"],
                bot_id=bot["id"],
                direction="outbound",
                kind="text",
                source="ai",
                body="Estoy activando el siguiente mejor playbook para dar continuidad sin perder el contexto.",
                status="simulated",
                metadata={"provider": "simulated", "trace_id": run["trace_id"], "execution_id": run["execution_id"], "correlation_id": correlation_id, "playbook_result": playbook_result, "self_state": self_state},
                correlation_id=correlation_id,
            )
        elif decision["action"] == "execute_tool":
            generator_output = {"tool_plan": (self_state.get("turn") or {}).get("tool_plan"), "self_state": self_state}
            response_message = create_message(
                conn,
                organization_id=conversation["organization_id"],
                conversation_id=conversation["id"],
                contact_id=contact["id"],
                bot_id=bot["id"],
                direction="outbound",
                kind="text",
                source="ai",
                body="Ya tengo identificado el siguiente paso operativo y estoy preparando la ejecución con los datos confirmados.",
                status="simulated",
                metadata={"provider": "simulated", "trace_id": run["trace_id"], "execution_id": run["execution_id"], "correlation_id": correlation_id, "tool_plan": (self_state.get("turn") or {}).get("tool_plan"), "self_state": self_state},
                correlation_id=correlation_id,
            )
        elif decision["action"] == "wait":
            generator_output = {"self_state": self_state}
            response_message = create_message(
                conn,
                organization_id=conversation["organization_id"],
                conversation_id=conversation["id"],
                contact_id=contact["id"],
                bot_id=bot["id"],
                direction="outbound",
                kind="text",
                source="system",
                body="La conversación quedó en espera por estado operacional.",
                status="internal",
                metadata={"trace_id": run["trace_id"], "execution_id": run["execution_id"], "correlation_id": correlation_id, "self_state": self_state},
                correlation_id=correlation_id,
            )

        append_technical_log(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            execution_run_id=run["id"],
            conversation_id=conversation["id"],
            level="info",
            category="memory_curator",
            message="Memory curation prepared",
            trace_id=run["trace_id"],
            execution_id=run["execution_id"],
            details=memory_curation,
        )
        updated_memory = update_memory(
            conn,
            organization_id=conversation["organization_id"],
            contact_id=contact["id"],
            bot_id=bot["id"],
            incoming_text=incoming_message["body"],
            classification=classification,
            contact=contact,
            recent_messages=recent_messages,
            conversation_id=conversation["id"],
            source_message_id=incoming_message["id"],
        )
        maybe_create_conversation_checkpoint(conn, organization_id=conversation["organization_id"], conversation_id=conversation["id"], bot_id=bot["id"], recent_messages=recent_messages + [{"direction": incoming_message.get("direction"), "body": incoming_message.get("body")}], classification=classification, memory=updated_memory or memory)
        candidate_confirmation = maybe_register_candidate_confirmation(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            conversation_id=conversation["id"],
            contact_id=contact["id"],
            classification=classification,
            memory=updated_memory or memory,
            bot_config=bot_config,
        )
        jobs = maybe_schedule_followups(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            conversation_id=conversation["id"],
            contact_id=contact["id"],
            classification=classification,
            decision=decision,
            bot_config=bot_config,
        )
        for job in jobs:
            emit_domain_event(conn, event_name="followup_scheduled", organization_id=conversation["organization_id"], bot_id=bot["id"], conversation_id=conversation["id"], message_id=incoming_message["id"], correlation_id=correlation_id, payload={"job_id": job.get("id"), "job_type": job.get("job_type")})
        if candidate_confirmation:
            emit_domain_event(conn, event_name="talent_candidate_confirmed", organization_id=conversation["organization_id"], bot_id=bot["id"], conversation_id=conversation["id"], message_id=incoming_message["id"], correlation_id=correlation_id, payload={"candidate_id": candidate_confirmation.get("id"), "vacancy_id": candidate_confirmation.get("vacancy_id")})
        if decision.get("action") == "handoff":
            emit_domain_event(conn, event_name="handoff_triggered", organization_id=conversation["organization_id"], bot_id=bot["id"], conversation_id=conversation["id"], message_id=incoming_message["id"], correlation_id=correlation_id, payload={"reason": decision.get("reason"), "policy": decision.get("policy")})
        status = "completed"
    except Exception as exc:
        error = str(exc)
        updated_memory = memory
        jobs = []
        decision = {"action": "error", "reason": "pipeline_exception"}
        status = "failed"
        append_technical_log(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            execution_run_id=run["id"],
            conversation_id=conversation["id"],
            level="error",
            category="runtime",
            message="Pipeline exception",
            trace_id=run["trace_id"],
            execution_id=run["execution_id"],
            details={"error": error},
        )

    from .multi_agent_runtime import persist_agent_route_run, record_specialist_exposure

    specialist_route_row = persist_agent_route_run(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        contact_id=contact["id"],
        message_id=incoming_message["id"],
        text=incoming_message["body"],
        classification=classification,
        route=specialist_route,
        shared_memory=shared_memory,
        execution_plan=execution_plan,
        supervisor=supervisor,
        status=status,
    )
    if status == "completed" and decision.get("action") in {"respond", "respond_and_schedule_followup", "handoff"}:
        record_specialist_exposure(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            conversation_id=conversation["id"],
            contact_id=contact["id"],
            message_id=(response_message or {}).get("id") if response_message else incoming_message.get("id"),
            route=specialist_route,
            flow_id=specialist_route.get("specialist_agent_key"),
            prompt_run_id=run["id"],
            metadata={
                "agent_routing_run_id": (specialist_route_row or {}).get("id"),
                "decision_action": decision.get("action"),
                "supervisor_needs_review": bool(supervisor.get("needs_review")),
                "assigned_variant": (candidate_ranking or {}).get("selected_variant"),
                "candidate_count": int((candidate_ranking or {}).get("candidate_count") or 0),
                "ranking_version": (candidate_ranking or {}).get("ranker_version"),
            },
        )

    if has_column(conn, "message_ai_runs", "correlation_id"):
        execute(
            conn,
            """
            INSERT INTO message_ai_runs
            (id, organization_id, message_id, conversation_id, bot_id, classifier_input, classifier_output, decision_input, decision_output, generator_input, generator_output, action_taken, error, created_at, correlation_id, classifier_source, decision_policy, generator_source, fallback_chain_json, selected_variant, candidate_count, ranking_version, ranking_summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ai_run_id,
                conversation["organization_id"],
                incoming_message["id"],
                conversation["id"],
                bot["id"],
                to_json(classification_input),
                to_json(classification),
                to_json(decision_input),
                to_json(decision),
                to_json(generator_input),
                to_json(generator_output or {}),
                decision.get("action"),
                error,
                utcnow_iso(),
                effective_correlation_id,
                classification.get("_classifier_source"),
                decision.get("policy") or "heuristic",
                classification.get("_generator_source"),
                to_json(classification.get("_fallback_chain") or []),
                (candidate_ranking or {}).get("selected_variant"),
                int((candidate_ranking or {}).get("candidate_count") or 0),
                (candidate_ranking or {}).get("ranker_version"),
                to_json((candidate_ranking or {}).get("summary") or {}),
            ),
        )
    else:
        execute(
            conn,
            """
            INSERT INTO message_ai_runs
            (id, organization_id, message_id, conversation_id, bot_id, classifier_input, classifier_output, decision_input, decision_output, generator_input, generator_output, action_taken, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ai_run_id,
                conversation["organization_id"],
                incoming_message["id"],
                conversation["id"],
                bot["id"],
                to_json(classification_input),
                to_json(classification),
                to_json(decision_input),
                to_json(decision),
                to_json(generator_input),
                to_json(generator_output or {}),
                decision.get("action"),
                error,
                utcnow_iso(),
            ),
        )
    if table_exists(conn, "response_candidate_rankings") and decision.get("action") in {"respond", "respond_and_schedule_followup"}:
        for item in (candidate_ranking or {}).get("candidates") or []:
            execute(
                conn,
                """
                INSERT INTO response_candidate_rankings (
                    id, organization_id, message_ai_run_id, message_id, conversation_id, bot_id, candidate_index, variant_key,
                    tone, cta_style, length, framing, source, response_text, verification_status, verification_json,
                    score_total, score_json, selected, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("resp_rank"),
                    conversation["organization_id"],
                    ai_run_id,
                    incoming_message["id"],
                    conversation["id"],
                    bot["id"],
                    int(item.get("candidate_index") or 0),
                    item.get("variant_key"),
                    item.get("tone"),
                    item.get("cta_style"),
                    item.get("length"),
                    item.get("framing"),
                    item.get("source"),
                    item.get("text"),
                    (item.get("verification") or {}).get("status"),
                    to_json(item.get("verification") or {}),
                    float(item.get("score_total") or 0.0),
                    to_json(item.get("score") or {}),
                    1 if item.get("selected") else 0,
                    utcnow_iso(),
                ),
            )

    if table_exists(conn, "message_operational_reasoning"):
        execute(
            conn,
            "INSERT INTO message_operational_reasoning (id, organization_id, message_id, conversation_id, bot_id, intent_detected, urgency_level, urgency_score, takeover_reason, policy_applied, classifier_source, generator_source, summary_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id("mreason"),
                conversation["organization_id"],
                incoming_message["id"],
                conversation["id"],
                bot["id"],
                classification.get("intent"),
                classification.get("urgency_level"),
                int(classification.get("urgency_score", 0) or 0),
                decision.get("reason") if decision.get("action") == "handoff" else None,
                decision.get("policy") or "heuristic",
                classification.get("_classifier_source"),
                classification.get("_generator_source"),
                to_json({
                    "intention_detected": classification.get("intent"),
                    "urgency": {"level": classification.get("urgency_level"), "score": classification.get("urgency_score")},
                    "takeover_reason": decision.get("reason") if decision.get("action") == "handoff" else None,
                    "policy_applied": decision.get("policy") or "heuristic",
                    "planner": execution_plan,
                    "grounded_context": {"source_count": grounded_context.get("source_count"), "coverage": grounded_context.get("coverage")},
                    "verification": verification or {},
                    "candidate_ranking": candidate_ranking,
                    "post_send_evaluation": post_send_evaluation,
                    "memory_curation": memory_curation,
                    "self_state": self_state,
                }),
                utcnow_iso(),
            ),
        )
    finished_run = finish_execution_run(
        conn,
        run_id=run["id"],
        status=status,
        output_payload={
            "classification": classification,
            "decision": decision,
            "plan": execution_plan,
            "grounded_context": {"source_count": grounded_context.get("source_count"), "coverage": grounded_context.get("coverage")},
            "verification": verification or {},
            "candidate_ranking": candidate_ranking,
            "post_send_evaluation": post_send_evaluation,
            "self_state": self_state,
            "response_message_id": response_message.get("id") if response_message else None,
            "jobs": [job.get("id") for job in jobs],
        },
        error_payload={"error": error} if error else {},
    )
    total_duration_ms = int((time.perf_counter() - pipeline_started) * 1000)
    record_stage_metric(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        trace_id=run["trace_id"],
        correlation_id=effective_correlation_id,
        vertical=bot.get("vertical"),
        source_type="inbound_message",
        stage_name="pipeline.total",
        duration_ms=total_duration_ms,
        status="ok" if status == "completed" else "error",
        metrics={"action": decision.get("action"), "verification_status": (verification or {}).get("status")},
    )
    create_audit_log(
        conn,
        organization_id=conversation["organization_id"],
        actor_user_id=None,
        actor_type="system",
        entity_type="message",
        entity_id=incoming_message["id"],
        action="ai.pipeline_executed",
        metadata={"action": decision.get("action"), "error": error, "execution_run_id": run["id"], "verification_status": (verification or {}).get("status"), "quality_score": post_send_evaluation.get("quality_score")},
    )
    return {
        "classification": classification,
        "grounded_context": grounded_context,
        "plan": execution_plan,
        "decision": decision,
        "verification": verification,
        "post_send_evaluation": post_send_evaluation,
        "self_state": self_state,
        "response_message": response_message,
        "updated_memory": updated_memory,
        "jobs": jobs,
        "error": error,
        "execution_run": finished_run,
    }
