from __future__ import annotations

from typing import Any, Iterator

from ..db import fetch_all
from ..response_ranking_runtime import style_response_candidate
from ..utils import parse_iso
from .generation_context import build_generation_bundle
from .generation_heuristics import (
    _build_general_reframe,
    _find_faq_answer,
    _find_price,
    _instant_knowledge_response,
    heuristic_generate,
)
from .generation_language import (
    _detect_contact_language,
    _detect_customer_tone,
    _language_voice_layer,
    _looks_like_humor_or_odd_question,
    _looks_overwhelmed,
    _pair_by_language,
    _supported_languages,
    _tone_mode,
    _tone_phrase,
)
from .generation_openai import call_openai_generation


def _recent_inbound_batch(
    conn,
    *,
    conversation_id: str | None,
    fallback_text: str,
    window_seconds: int = 20,
    max_messages: int = 4,
) -> list[str]:
    if conn is None or not conversation_id:
        return [fallback_text]
    rows = fetch_all(
        conn,
        "SELECT body, created_at FROM messages WHERE conversation_id = ? AND direction = 'inbound' ORDER BY created_at DESC LIMIT ?",
        (conversation_id, max(2, max_messages)),
    )
    if not rows:
        return [fallback_text]
    latest = parse_iso(rows[0].get("created_at"))
    batched: list[str] = []
    for row in rows:
        created_at = parse_iso(row.get("created_at"))
        if latest and created_at and (latest - created_at).total_seconds() > max(1, int(window_seconds)):
            continue
        body = str(row.get("body") or "").strip()
        if body:
            batched.append(body)
    batched = list(reversed(batched))
    if not batched:
        return [fallback_text]
    if fallback_text.strip() and fallback_text.strip() not in batched:
        batched.append(fallback_text.strip())
    return batched[-max(1, max_messages):]


def stream_generated_text_chunks(text: str, *, chunk_size: int = 40) -> Iterator[str]:
    clean = str(text or "").strip()
    if not clean:
        return iter(())
    parts = [clean[i : i + max(10, chunk_size)] for i in range(0, len(clean), max(10, chunk_size))]
    return iter(parts)


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
    bundle = build_generation_bundle(
        text,
        classification,
        bot_config,
        memory,
        recent_messages,
        conn=conn,
        organization_id=organization_id,
        bot_id=bot_id,
        contact_id=contact_id,
        conversation_id=conversation_id,
        recent_voice_notes=recent_voice_notes,
        language_config=language_config,
        execution_plan=execution_plan,
        grounded_context=grounded_context,
        candidate_spec=candidate_spec,
    )
    language = str(bundle["language"])
    knowledge_hits = list(bundle["knowledge_hits"])
    prompt_payload = dict(bundle["prompt_payload"])

    fallback_chain: list[str] = []
    instant_reply = _instant_knowledge_response(text, classification, bot_config, knowledge_hits, language)
    if instant_reply:
        fallback_chain.append("instant_knowledge")
        prompt_payload["instant_knowledge_match"] = instant_reply.get("matched")
        prompt_payload["generator_source"] = "instant_knowledge"
        prompt_payload["generator_fallback_chain"] = fallback_chain
        instant_text = style_response_candidate(
            response_text=str(instant_reply.get("text") or ""),
            candidate_spec=candidate_spec,
            language=language,
            classification=classification,
            bot_config=bot_config,
            execution_plan=execution_plan or {},
        )
        return instant_text, prompt_payload

    response = call_openai_generation(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=conversation_id,
        input_text=text,
        classification=classification,
        prompt_payload=prompt_payload,
    )
    if response:
        fallback_chain.append("openai")
        prompt_payload["generator_source"] = "openai"
        prompt_payload["generator_fallback_chain"] = fallback_chain
        response = style_response_candidate(
            response_text=response,
            candidate_spec=candidate_spec,
            language=language,
            classification=classification,
            bot_config=bot_config,
            execution_plan=execution_plan or {},
        )
        return response, prompt_payload

    fallback_chain.extend(["openai", "heuristic"])
    response = heuristic_generate(
        text,
        classification,
        bot_config,
        memory,
        recent_messages=recent_messages,
        voice_context=recent_voice_notes,
        language_config=language_config,
    )
    prompt_payload["generator_source"] = "heuristic"
    prompt_payload["generator_fallback_chain"] = fallback_chain
    response = style_response_candidate(
        response_text=response,
        candidate_spec=candidate_spec,
        language=language,
        classification=classification,
        bot_config=bot_config,
        execution_plan=execution_plan or {},
    )
    return response, prompt_payload
