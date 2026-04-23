from __future__ import annotations

import time
from typing import Any

import httpx

from ..circuit_breaker import circuit_guard, record_provider_failure, record_provider_success
from ..config import settings
from ..runtime_settings import ai_optimization_settings
from ..utils import to_json
from ..world_class import choose_model, compress_prompt_payload, lookup_ai_cache, record_ai_usage, store_ai_cache


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
    compressed_payload, compression = compress_prompt_payload(
        prompt_payload,
        char_budget=int(optimization.get("generation_char_budget") or 2600),
    )
    cached = lookup_ai_cache(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        cache_type="generation",
        payload=compressed_payload,
        min_similarity=float(optimization.get("semantic_cache_similarity_generation") or 0.94),
    )
    if cached:
        metadata = cached.get("metadata") or {}
        response_text = cached.get("row", {}).get("response_text") or metadata.get("response_text")
        if response_text:
            record_ai_usage(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                conversation_id=conversation_id,
                model=metadata.get("model") or settings.openai_model,
                operation="generation",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0,
                cache_hit=True,
                fallback_source="semantic_cache",
                metadata={"cache_match": cached.get("match"), "similarity": cached.get("similarity")},
            )
            return response_text

    allowed, breaker, _policy = circuit_guard(
        conn,
        provider="openai",
        circuit_key=f"generation:{bot_id or 'global'}",
        organization_id=organization_id,
        metadata={"module": "ai.generation", "bot_id": bot_id, "conversation_id": conversation_id},
    )
    if not allowed:
        record_ai_usage(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            model=settings.openai_model,
            operation="generation",
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=0,
            cache_hit=False,
            fallback_source="circuit_open",
            metadata={"breaker": breaker},
        )
        return None

    selected_model = choose_model(
        str(optimization.get("complex_model") or settings.openai_model),
        operation="generation",
        input_text=input_text,
        classification=classification,
    )
    payload = {
        "model": selected_model,
        "instructions": (
            "Eres un agente de WhatsApp de negocio. Responde breve, clara y natural. "
            "Por ahora puedes hablar en español y en inglés, y debes responder en el idioma del cliente usando texto y, si existe, el contexto reciente de voz. "
            "Usa una voz nativa por idioma: en español suena cercano, claro y con barrio bien presentado; en inglés suena natural, sharp y nada traducido raro. "
            "Entiende el tono de voz del cliente (formal, casual, urgente, cansado, bromista) y adaptate sin perder una voz cercana, profesional y comercial. "
            "Nunca te quedes seco si el cliente bromea, pregunta algo raro, cambia de tema o se desahoga. "
            "Valida el momento, usa humor ligero solo cuando sume, reencauza al negocio y deja siempre un siguiente paso. "
            "No inventes precios, politicas ni disponibilidad no configuradas. "
            "Si falta un dato, dilo con honestidad y redirige a algo util y comercial. "
            "Nunca suenes tecnico, robotico ni corporativo."
        ),
        "input": [{"role": "user", "content": [{"type": "input_text", "text": to_json(compressed_payload)}]}],
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
            usage = data.get("usage") or {}
            prompt_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or max(1, len(to_json(compressed_payload)) // 4))
            completion_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or max(1, len(output_text) // 4))
            record_ai_usage(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                conversation_id=conversation_id,
                model=selected_model,
                operation="generation",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                cache_hit=False,
                metadata={"compression": compression, "intent": classification.get("intent")},
            )
            store_ai_cache(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                cache_scope="bot",
                cache_type="generation",
                payload=compressed_payload,
                response_text=output_text,
                response_json={"model": selected_model},
                ttl_seconds=max(300, settings.runtime_cache_ttl_seconds * 30),
            )
            record_provider_success(
                conn,
                provider="openai",
                circuit_key=f"generation:{bot_id or 'global'}",
                organization_id=organization_id,
                metadata={"module": "ai.generation", "latency_ms": latency_ms, "model": selected_model, "bot_id": bot_id},
            )
            return output_text
    except Exception as exc:
        record_provider_failure(
            conn,
            provider="openai",
            circuit_key=f"generation:{bot_id or 'global'}",
            error_text=str(exc),
            organization_id=organization_id,
            metadata={"module": "ai.generation", "bot_id": bot_id, "conversation_id": conversation_id},
        )
        return None
    return None
