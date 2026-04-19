from __future__ import annotations

import re
from typing import Any

from .contact_intelligence import relationship_snapshot
from .knowledge_runtime import governed_knowledge_summary, search_governed_knowledge
from .response_ranking_runtime import (
    build_ranking_summary,
    build_response_candidate_specs,
    infer_reply_language,
    score_response_candidate,
)
from .multi_agent_runtime import (
    apply_specialist_plan,
    apply_supervisor_decision,
    build_shared_memory_context,
    route_intent_to_specialist,
    supervise_specialist_route,
)
from .optimizer_runtime import (
    apply_candidate_spec_overrides,
    apply_execution_plan_overrides,
    apply_handoff_override,
    apply_specialist_route_override,
    create_runtime_optimizer_audit,
    load_optimizer_runtime_context,
    maybe_record_shadow_selection,
)
from .growth_os_runtime import apply_growth_os_execution_focus, apply_growth_os_specialist_focus, active_growth_os_focus
from .self_state_runtime import (
    apply_self_state_decision,
    build_conversation_self_state,
    build_turn_self_state,
)


_PRICE_PATTERN = re.compile(r"(?:\$|usd|mxn|eur|precio|price)\s*[:=]?\s*[0-9][0-9,\.]*", re.IGNORECASE)
_HOURS_PATTERN = re.compile(r"\b(?:[01]?\d|2[0-3])(?::[0-5]\d)?\s*(?:am|pm|hrs?|h)?\b", re.IGNORECASE)


def _safe_lookup(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return []


def _normalize_topic(topic: str) -> str:
    value = str(topic or "").strip().lower()
    synonyms = {
        "quote": "pricing",
        "cotizacion": "pricing",
        "booking": "schedule",
        "faq": "faq",
        "support": "support",
        "payment": "payment",
        "direccion": "location",
        "ubicacion": "location",
        "horario": "schedule",
    }
    return synonyms.get(value, value)


def _source_record(*, source_type: str, label: str, content_text: str, supports: list[str], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "label": label,
        "content_text": str(content_text or "").strip(),
        "supports": [_normalize_topic(item) for item in supports if item],
        "metadata": metadata or {},
    }


def _business_knowledge_sources(bot_config: dict[str, Any]) -> list[dict[str, Any]]:
    business = (bot_config or {}).get("business_knowledge", {}) or {}
    sources: list[dict[str, Any]] = []
    services = business.get("services") or []
    if services:
        sources.append(
            _source_record(
                source_type="business_knowledge",
                label="services",
                content_text=", ".join(str(item) for item in services[:8]),
                supports=["faq", "general", "support"],
            )
        )
    prices = business.get("prices") or []
    if prices:
        rendered_prices: list[str] = []
        for item in prices[:6]:
            if isinstance(item, dict):
                rendered_prices.append(f"{item.get('name', 'Servicio')}: {item.get('price', '')}".strip(": "))
            else:
                rendered_prices.append(str(item))
        sources.append(
            _source_record(
                source_type="business_knowledge",
                label="prices",
                content_text=" | ".join(rendered_prices),
                supports=["pricing", "payment"],
            )
        )
    hours = str(business.get("hours") or "").strip()
    if hours:
        sources.append(
            _source_record(
                source_type="business_knowledge",
                label="hours",
                content_text=hours,
                supports=["schedule", "faq"],
            )
        )
    location = str(business.get("location") or "").strip()
    if location:
        sources.append(
            _source_record(
                source_type="business_knowledge",
                label="location",
                content_text=location,
                supports=["location", "faq"],
            )
        )
    faqs = business.get("faqs") or []
    faq_lines: list[str] = []
    for item in faqs[:6]:
        if isinstance(item, dict) and (item.get("q") or item.get("a")):
            faq_lines.append(f"Q: {item.get('q', '')} A: {item.get('a', '')}".strip())
    if faq_lines:
        sources.append(
            _source_record(
                source_type="business_knowledge",
                label="faqs",
                content_text=" | ".join(faq_lines),
                supports=["faq", "support", "location"],
            )
        )
    return [item for item in sources if item.get("content_text")]


def _support_status_for_topic(sources: list[dict[str, Any]], topic: str) -> str:
    relevant = [item for item in sources if topic in (item.get("supports") or [])]
    if not relevant:
        return "missing"
    statuses = [str((item.get("metadata") or {}).get("freshness_status") or "fresh") for item in relevant]
    if "fresh" in statuses:
        return "fresh"
    if "aging" in statuses:
        return "aging"
    if "stale" in statuses:
        return "stale"
    return "unknown"


def build_grounded_context(
    *,
    text: str,
    memory: dict[str, Any],
    bot_config: dict[str, Any],
    conn=None,
    organization_id: str | None = None,
    bot_id: str | None = None,
    contact_id: str | None = None,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    from .world_class import recent_checkpoints, search_knowledge_embeddings, search_memory_vectors

    sources: list[dict[str, Any]] = []
    governed_hits: list[dict[str, Any]] = []
    if conn is not None and organization_id and bot_id:
        governed_hits = _safe_lookup(
            search_governed_knowledge,
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            query=text,
            intent=(memory or {}).get("current_intent") or None,
            limit=6,
        )
        for item in governed_hits:
            trace = dict(item.get("traceability") or {})
            sources.append(
                _source_record(
                    source_type="governed_knowledge",
                    label=item.get("title") or item.get("source_key") or "knowledge_document",
                    content_text=item.get("content_text") or "",
                    supports=item.get("supports") or [],
                    metadata={
                        "domain": item.get("domain"),
                        "score": item.get("score"),
                        "freshness_status": item.get("freshness_status"),
                        "traceability": trace,
                    },
                )
            )

    config_sources = _business_knowledge_sources(bot_config)
    if not governed_hits:
        sources.extend(config_sources)
    else:
        sources.extend(config_sources[:2])

    if conn is not None and organization_id:
        memory_hits = _safe_lookup(
            search_memory_vectors,
            conn,
            organization_id=organization_id,
            contact_id=contact_id,
            bot_id=bot_id,
            query=text,
            limit=4,
        )
        for item in memory_hits:
            sources.append(
                _source_record(
                    source_type="memory_vector",
                    label="memory_recall",
                    content_text=item.get("content_text") or "",
                    supports=["general", "support", "schedule", "pricing"],
                    metadata={"score": item.get("score")},
                )
            )
    if conn is not None and organization_id and bot_id:
        knowledge_hits = _safe_lookup(
            search_knowledge_embeddings,
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            query=text,
            limit=4,
        )
        for item in knowledge_hits:
            sources.append(
                _source_record(
                    source_type="knowledge_embedding",
                    label="knowledge_recall",
                    content_text=item.get("content_text") or "",
                    supports=["faq", "support", "pricing", "schedule", "payment"],
                    metadata={"source_key": item.get("source_key")},
                )
            )
    if conn is not None and conversation_id:
        checkpoints = _safe_lookup(recent_checkpoints, conn, conversation_id=conversation_id, limit=2)
        for item in checkpoints:
            summary = str(item.get("summary_text") or "").strip()
            if summary:
                sources.append(
                    _source_record(
                        source_type="conversation_checkpoint",
                        label="checkpoint",
                        content_text=summary,
                        supports=["general", "support", "followup"],
                        metadata={"facts": item.get("facts")},
                    )
                )

    limited_sources = sources[:16]
    coverage = {
        "pricing": any("pricing" in item.get("supports", []) for item in limited_sources),
        "schedule": any("schedule" in item.get("supports", []) for item in limited_sources),
        "location": any("location" in item.get("supports", []) for item in limited_sources),
        "faq": any("faq" in item.get("supports", []) for item in limited_sources),
        "support": any("support" in item.get("supports", []) for item in limited_sources),
        "payment": any("payment" in item.get("supports", []) for item in limited_sources),
        "memory": any(item.get("source_type") == "memory_vector" for item in limited_sources),
        "knowledge": any(item.get("source_type") == "knowledge_embedding" for item in limited_sources),
        "governed_knowledge": any(item.get("source_type") == "governed_knowledge" for item in limited_sources),
        "checkpoints": any(item.get("source_type") == "conversation_checkpoint" for item in limited_sources),
    }
    support_status = {
        topic: _support_status_for_topic(limited_sources, topic)
        for topic in ["pricing", "schedule", "location", "faq", "support", "payment"]
    }
    governed_summary = governed_knowledge_summary(governed_hits)
    return {
        "sources": limited_sources,
        "coverage": coverage,
        "support_status": support_status,
        "source_count": len(limited_sources),
        "grounding_mode": "governed_multi_source" if governed_hits else ("multi_source" if len(limited_sources) > 1 else ("single_source" if limited_sources else "none")),
        "verifiable": bool(limited_sources),
        "relationship": relationship_snapshot(memory),
        "knowledge_summary": governed_summary,
        "traceability": governed_summary.get("traceability", []),
        "freshness_status": governed_summary.get("overall_freshness", "fresh" if limited_sources else "none"),
    }


def plan_runtime_execution(
    *,
    text: str,
    conversation: dict[str, Any],
    bot: dict[str, Any],
    classification: dict[str, Any],
    memory: dict[str, Any],
    bot_config: dict[str, Any],
    grounded_context: dict[str, Any],
) -> dict[str, Any]:
    intent = str(classification.get("intent") or "general")
    coverage = grounded_context.get("coverage", {})
    support_status = grounded_context.get("support_status", {})
    profile = relationship_snapshot(memory)
    objectives_by_intent = {
        "pricing": ["answer_pricing", "avoid_unverified_rates", "move_to_next_step"],
        "schedule": ["capture_availability", "confirm_hours_if_available", "advance_booking"],
        "faq": ["answer_grounded_question", "avoid_invention", "offer_next_step"],
        "complaint": ["deescalate", "protect_trust", "handoff_when_needed"],
        "support": ["clarify_issue", "ground_response", "route_if_risky"],
        "payment": ["clarify_payment_state", "avoid_false_confirmation", "advance_resolution"],
        "human": ["honor_human_request", "handoff_cleanly"],
        "general": ["understand_need", "respond_helpfully", "collect_next_signal"],
    }
    tools: list[dict[str, Any]] = []
    if grounded_context.get("source_count"):
        tools.append({"tool": "grounded_context", "mode": grounded_context.get("grounding_mode"), "required": True})
    if coverage.get("governed_knowledge"):
        tools.append({"tool": "governed_knowledge", "mode": "retrieve_ranked_traceable", "required": intent in {"pricing", "schedule", "faq", "payment", "support"}})
        tools.append({"tool": "freshness_evaluator", "mode": grounded_context.get("freshness_status"), "required": intent in {"pricing", "schedule", "payment", "support"}})
    if coverage.get("memory"):
        tools.append({"tool": "memory_vectors", "mode": "recall", "required": False})
    if coverage.get("knowledge"):
        tools.append({"tool": "knowledge_embeddings", "mode": "retrieve", "required": False})
    if coverage.get("checkpoints"):
        tools.append({"tool": "conversation_checkpoints", "mode": "summarize", "required": False})
    if intent in {"pricing", "schedule", "faq", "payment", "support"} and not any(item.get("tool") == "grounded_context" for item in tools):
        tools.append({"tool": "grounded_context", "mode": "missing_but_desired", "required": False})

    risk_flags: list[str] = []
    if classification.get("requested_human"):
        risk_flags.append("requested_human")
    if intent in {"complaint", "payment", "support"}:
        risk_flags.append("high_consequence_intent")
    if intent == "pricing" and support_status.get("pricing") in {"missing", "stale"}:
        risk_flags.append("pricing_without_grounding" if support_status.get("pricing") == "missing" else "pricing_stale_grounding")
    if intent == "schedule" and support_status.get("schedule") in {"missing", "stale"}:
        risk_flags.append("schedule_without_hours" if support_status.get("schedule") == "missing" else "schedule_stale_grounding")
    if int(classification.get("urgency_score", 0) or 0) >= 70:
        risk_flags.append("high_urgency")
    if conversation.get("human_takeover"):
        risk_flags.append("human_takeover_present")
    if profile.get("known_contact"):
        risk_flags.append("known_contact")

    verification_checks = ["non_empty_response", "policy_consistency", "grounding_support", "tone_and_language"]
    if intent in {"pricing", "faq", "schedule", "payment", "support"}:
        verification_checks.append("factual_support_for_operational_claims")
        verification_checks.append("freshness_check_for_governed_knowledge")
    return {
        "planner_version": "agentic_runtime_v1",
        "intent": intent,
        "objectives": objectives_by_intent.get(intent, objectives_by_intent["general"]),
        "tool_orchestration": tools,
        "response_contract": {
            "requires_grounding": intent in {"pricing", "faq", "schedule", "payment", "support"},
            "requires_fresh_knowledge": intent in {"pricing", "schedule", "payment", "legal"},
            "requires_verification": True,
            "prefer_handoff": "requested_human" in risk_flags or intent == "complaint",
            "target_channel": "whatsapp",
        },
        "verification_checks": verification_checks,
        "risk_flags": risk_flags,
        "memory_curation": {
            "write_summary": True,
            "write_facts": intent in {"pricing", "schedule", "payment", "support", "followup"},
        },
        "rendering_hints": {
            "max_turns_to_reference": 8,
            "should_offer_next_step": intent in {"pricing", "schedule", "faq", "general", "support"},
            "keep_reply_compact": True,
            "mirror_customer_language": True,
        },
        "planner_notes": {
            "message_preview": str(text or "")[:140],
            "bot_status": bot.get("status"),
            "lead_stage": memory.get("lead_stage"),
            "support_status": support_status,
            "knowledge_freshness": grounded_context.get("freshness_status"),
        },
    }


def select_runtime_action(
    *,
    conversation: dict[str, Any],
    bot: dict[str, Any],
    classification: dict[str, Any],
    memory: dict[str, Any],
    bot_config: dict[str, Any],
    execution_plan: dict[str, Any],
) -> dict[str, Any]:
    from .ai import decide_action

    decision = decide_action(
        conversation=conversation,
        bot=bot,
        classification=classification,
        memory=memory,
        bot_config=bot_config,
    )
    return {
        **decision,
        "decision_layer": "policy_aware_executor",
        "planner_version": execution_plan.get("planner_version"),
        "verification_required": bool((execution_plan.get("response_contract") or {}).get("requires_verification")),
        "tool_orchestration": execution_plan.get("tool_orchestration") or [],
    }


def render_runtime_reply(
    text: str,
    classification: dict[str, Any],
    bot_config: dict[str, Any],
    memory: dict[str, Any],
    recent_messages: list[dict[str, Any]],
    *,
    execution_plan: dict[str, Any],
    grounded_context: dict[str, Any],
    conn=None,
    organization_id: str | None = None,
    bot_id: str | None = None,
    contact_id: str | None = None,
    conversation_id: str | None = None,
    recent_voice_notes: list[dict[str, Any]] | None = None,
    language_config: dict[str, Any] | None = None,
    candidate_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .ai import generate_response

    response_text, payload = generate_response(
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
    return {
        "text": response_text,
        "payload": payload,
        "source": payload.get("generator_source") or "heuristic",
        "fallback_chain": payload.get("generator_fallback_chain") or ["heuristic"],
        "candidate_spec": payload.get("response_ranking_candidate") or candidate_spec or {},
    }


def _contains_location_claim(response_text: str) -> bool:
    lower = response_text.lower()
    return "estamos en" in lower or "ubicados en" in lower or "located at" in lower or "we are at" in lower


def _infer_language(text: str, response_text: str, bot_config: dict[str, Any]) -> str:
    combined = f"{text} {response_text}".lower()
    english_markers = ["price", "book", "hours", "where", "help", "please"]
    spanish_markers = ["precio", "agendar", "horario", "donde", "ayuda", "por favor"]
    english_score = sum(1 for item in english_markers if item in combined)
    spanish_score = sum(1 for item in spanish_markers if item in combined)
    if english_score > spanish_score:
        return "en"
    if spanish_score > english_score:
        return "es"
    return str((bot_config.get("identity") or {}).get("language") or "es").lower()


def _verified_fallback(language: str, intent: str, bot_config: dict[str, Any]) -> str:
    business = str((bot_config.get("identity") or {}).get("business_name") or "nuestro equipo").strip()
    if intent == "pricing":
        return (
            "Te ayudo con precios. Para darte un dato correcto prefiero confirmar la tarifa antes de inventarte una cifra. "
            "Si quieres, avanzamos con tu necesidad y después te comparto el precio preciso."
            if language != "en"
            else "I can help with pricing. To give you a correct answer, I would rather confirm the rate than invent a number. "
            "If you want, we can move forward with your need and then share the precise price."
        )
    if intent == "schedule":
        return (
            "Te ayudo a agendar. Para no darte un horario incorrecto, mejor confirmo disponibilidad exacta y mientras me dices qué día u hora te conviene más."
            if language != "en"
            else "I can help you book it. To avoid giving you the wrong hours, I would rather confirm exact availability while you tell me what day or time works best."
        )
    if intent == "faq":
        return (
            f"Te ayudo con eso. Para responderte bien prefiero basarme en información confirmada de {business}. Cuéntame el detalle y te doy la respuesta más precisa posible."
            if language != "en"
            else f"I can help with that. To answer well, I would rather rely on confirmed information from {business}. Share the detail and I will give you the most precise answer I can."
        )
    return (
        "Te ayudo con gusto. Prefiero responder con información verificada para no confundirte. Cuéntame un poco más y lo resolvemos bien."
        if language != "en"
        else "Happy to help. I would rather answer with verified information so I do not mislead you. Tell me a bit more and we will sort it out properly."
    )


def verify_runtime_reply(
    *,
    text: str,
    response_text: str,
    classification: dict[str, Any],
    grounded_context: dict[str, Any],
    bot_config: dict[str, Any],
    execution_plan: dict[str, Any],
) -> dict[str, Any]:
    intent = str(classification.get("intent") or "general")
    coverage = grounded_context.get("coverage", {}) or {}
    support_status = grounded_context.get("support_status", {}) or {}
    checks: list[dict[str, Any]] = []
    issues: list[str] = []
    final_text = str(response_text or "").strip()
    language = _infer_language(text, final_text, bot_config)

    non_empty = bool(final_text)
    checks.append({"check": "non_empty_response", "passed": non_empty})
    if not non_empty:
        issues.append("empty_response")

    if final_text:
        pricing_claim = bool(_PRICE_PATTERN.search(final_text))
        pricing_ok = (not pricing_claim) or support_status.get("pricing") in {"fresh", "aging"}
        checks.append({"check": "pricing_claim_grounded", "passed": pricing_ok})
        if pricing_claim and support_status.get("pricing") in {"missing", "unknown"}:
            issues.append("unsupported_pricing_claim")
        if pricing_claim and support_status.get("pricing") == "stale":
            issues.append("stale_pricing_claim")

        location_claim = _contains_location_claim(final_text)
        location_ok = (not location_claim) or support_status.get("location") in {"fresh", "aging"} or bool(coverage.get("location"))
        checks.append({"check": "location_claim_grounded", "passed": location_ok})
        if location_claim and not location_ok:
            issues.append("unsupported_location_claim")

        lower = final_text.lower()
        schedule_claim = ("horario" in lower or "hours" in lower) and bool(_HOURS_PATTERN.search(final_text))
        schedule_ok = (not schedule_claim) or support_status.get("schedule") in {"fresh", "aging"}
        checks.append({"check": "schedule_claim_grounded", "passed": schedule_ok})
        if schedule_claim and support_status.get("schedule") in {"missing", "unknown"}:
            issues.append("unsupported_schedule_claim")
        if schedule_claim and support_status.get("schedule") == "stale":
            issues.append("stale_schedule_claim")

    if len(final_text) > 1200:
        issues.append("response_too_long")
        checks.append({"check": "compact_reply", "passed": False})
    else:
        checks.append({"check": "compact_reply", "passed": True})

    requires_grounding = bool(((execution_plan.get("response_contract") or {}).get("requires_grounding")))
    requires_fresh = bool(((execution_plan.get("response_contract") or {}).get("requires_fresh_knowledge")))
    if requires_grounding and not grounded_context.get("verifiable") and intent in {"pricing", "faq", "schedule", "payment", "support"}:
        checks.append({"check": "grounded_generation_available", "passed": False})
        issues.append("no_grounding_available")
    else:
        checks.append({"check": "grounded_generation_available", "passed": True})
    freshness_status = str(grounded_context.get("freshness_status") or "unknown")
    freshness_ok = (not requires_fresh) or freshness_status in {"fresh", "aging", "none"}
    checks.append({"check": "knowledge_freshness", "passed": freshness_ok})
    if requires_fresh and freshness_status == "stale":
        issues.append("stale_governed_knowledge")

    status = "approved"
    if issues:
        final_text = _verified_fallback(language, intent, bot_config)
        status = "rewritten"

    return {
        "status": status,
        "checks": checks,
        "issues": issues,
        "response_text": final_text,
        "verifier_version": "agentic_runtime_verifier_v1",
        "grounded_sources": [
            {"source_type": item.get("source_type"), "label": item.get("label"), "supports": item.get("supports"), "metadata": item.get("metadata")} for item in (grounded_context.get("sources") or [])[:8]
        ],
    }



def generate_ranked_runtime_reply(
    *,
    text: str,
    classification: dict[str, Any],
    bot_config: dict[str, Any],
    memory: dict[str, Any],
    recent_messages: list[dict[str, Any]],
    execution_plan: dict[str, Any],
    grounded_context: dict[str, Any],
    specialist_route: dict[str, Any] | None = None,
    conn=None,
    organization_id: str | None = None,
    bot_id: str | None = None,
    contact_id: str | None = None,
    conversation_id: str | None = None,
    recent_voice_notes: list[dict[str, Any]] | None = None,
    language_config: dict[str, Any] | None = None,
    optimizer_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate_specs = build_response_candidate_specs(
        classification=classification,
        execution_plan=execution_plan,
        specialist_route=specialist_route or {},
    )
    candidate_specs = apply_candidate_spec_overrides(candidate_specs, context=optimizer_context)
    candidates: list[dict[str, Any]] = []
    default_language = str((language_config or {}).get("default_language") or (bot_config.get("identity") or {}).get("language") or "es")

    for index, spec in enumerate(candidate_specs, start=1):
        generated = render_runtime_reply(
            text,
            classification,
            bot_config,
            memory,
            recent_messages,
            execution_plan=execution_plan,
            grounded_context=grounded_context,
            conn=conn,
            organization_id=organization_id,
            bot_id=bot_id,
            contact_id=contact_id,
            conversation_id=conversation_id,
            recent_voice_notes=recent_voice_notes,
            language_config=language_config,
            candidate_spec=spec,
        )
        language = infer_reply_language(text, generated["text"], default_language)
        verification = verify_runtime_reply(
            text=text,
            response_text=generated["text"],
            classification=classification,
            grounded_context=grounded_context,
            bot_config=bot_config,
            execution_plan=execution_plan,
        )
        scoring = score_response_candidate(
            response_text=verification["response_text"],
            candidate_spec=spec,
            classification=classification,
            verification=verification,
            grounded_context=grounded_context,
        )
        candidates.append(
            {
                "candidate_index": index,
                "variant_key": spec.get("variant_key"),
                "candidate_label": spec.get("candidate_label"),
                "tone": spec.get("tone"),
                "cta_style": spec.get("cta_style"),
                "length": spec.get("length"),
                "framing": spec.get("framing"),
                "language": language,
                "text": verification["response_text"],
                "raw_text": generated.get("text"),
                "source": generated.get("source"),
                "fallback_chain": generated.get("fallback_chain") or [],
                "verification": verification,
                "score_total": scoring.get("score_total"),
                "score": scoring,
                "selected": False,
            }
        )

    selected = max(
        candidates,
        key=lambda item: (
            float(item.get("score_total") or 0.0),
            float(((item.get("score") or {}).get("subscores") or {}).get("risk") or 0.0),
            float(((item.get("score") or {}).get("subscores") or {}).get("clarity") or 0.0),
            -int(item.get("candidate_index") or 999),
        ),
    )
    for item in candidates:
        item["selected"] = item is selected

    optimizer_preferred = next((item for item in candidates if item.get("optimizer_preferred")), None)
    if optimizer_preferred and optimizer_preferred is not selected:
        maybe_record_shadow_selection(
            conn,
            context=optimizer_context,
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            target_name="response_variant",
            production_output={"selected_variant": selected.get("variant_key"), "text": selected.get("text")},
            candidate_output={"selected_variant": optimizer_preferred.get("variant_key"), "text": optimizer_preferred.get("text")},
        )

    selected_generated = {
        "text": selected["text"],
        "raw_text": selected["raw_text"],
        "payload": {
            "generator_source": selected.get("source"),
            "generator_fallback_chain": selected.get("fallback_chain") or [],
            "response_ranking_candidate": {
                "variant_key": selected.get("variant_key"),
                "candidate_label": selected.get("candidate_label"),
                "tone": selected.get("tone"),
                "cta_style": selected.get("cta_style"),
                "length": selected.get("length"),
                "framing": selected.get("framing"),
            },
        },
        "source": selected.get("source"),
        "fallback_chain": selected.get("fallback_chain") or [],
        "candidate_spec": {
            "variant_key": selected.get("variant_key"),
            "candidate_label": selected.get("candidate_label"),
            "tone": selected.get("tone"),
            "cta_style": selected.get("cta_style"),
            "length": selected.get("length"),
            "framing": selected.get("framing"),
        },
        "verification_status": (selected.get("verification") or {}).get("status"),
        "optimizer_preferred_variant": (optimizer_preferred or {}).get("variant_key"),
    }
    ranking = {
        "ranker_version": "response_ranker_v1",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "selected_variant": selected.get("variant_key"),
        "selected_candidate_index": selected.get("candidate_index"),
        "summary": build_ranking_summary(candidates, selected),
        "optimizer_preferred_variant": (optimizer_preferred or {}).get("variant_key"),
    }
    return selected_generated, selected.get("verification") or {}, ranking

def curate_runtime_memory(
    *,
    text: str,
    classification: dict[str, Any],
    memory: dict[str, Any],
    grounded_context: dict[str, Any],
) -> dict[str, Any]:
    durable_facts: list[dict[str, Any]] = []
    interest = classification.get("interest")
    if interest:
        durable_facts.append({"fact": f"interest:{interest}", "source": "classification"})
    objection = classification.get("objection")
    if objection:
        durable_facts.append({"fact": f"objection:{objection}", "source": "classification"})
    if classification.get("requested_human"):
        durable_facts.append({"fact": "requested_human", "source": "classification"})
    urgency = classification.get("urgency_level")
    if urgency in {"high", "critical"}:
        durable_facts.append({"fact": f"urgency:{urgency}", "source": "classification"})
    if grounded_context.get("coverage", {}).get("memory"):
        durable_facts.append({"fact": "memory_recalled_for_turn", "source": "grounded_context"})
    return {
        "curator_version": "memory_curator_v1",
        "should_write_memory": bool(durable_facts) or bool(text.strip()),
        "durable_facts": durable_facts,
        "existing_stage": memory.get("lead_stage"),
    }


def evaluate_runtime_outcome(
    *,
    decision: dict[str, Any],
    verification: dict[str, Any] | None,
    grounded_context: dict[str, Any],
    generated: dict[str, Any] | None,
    candidate_ranking: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quality_score = 1.0
    if verification:
        quality_score -= min(0.6, 0.15 * len(verification.get("issues") or []))
    if not grounded_context.get("verifiable"):
        quality_score -= 0.1
    if decision.get("action") == "handoff":
        quality_score = max(quality_score, 0.8)
    ranking_summary = (candidate_ranking or {}).get("summary") or {}
    selection_margin = float(ranking_summary.get("selection_margin") or 0.0)
    if (candidate_ranking or {}).get("candidate_count"):
        quality_score += min(0.08, selection_margin / 2.0)
    quality_score = round(max(0.0, min(1.0, quality_score)), 3)
    return {
        "evaluator_version": "post_send_evaluator_v1",
        "quality_score": quality_score,
        "grounded": bool(grounded_context.get("verifiable")),
        "verification_status": (verification or {}).get("status") if verification else "not_required",
        "action": decision.get("action"),
        "generator_source": (generated or {}).get("source"),
        "selected_variant": (candidate_ranking or {}).get("selected_variant"),
        "candidate_count": int((candidate_ranking or {}).get("candidate_count") or 0),
        "selection_margin": round(selection_margin, 4),
    }


def orchestrate_runtime_turn(
    *,
    text: str,
    conversation: dict[str, Any],
    bot: dict[str, Any],
    memory: dict[str, Any],
    bot_config: dict[str, Any],
    recent_messages: list[dict[str, Any]],
    conn=None,
    organization_id: str | None = None,
    bot_id: str | None = None,
    contact_id: str | None = None,
    conversation_id: str | None = None,
    recent_voice_notes: list[dict[str, Any]] | None = None,
    language_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .runtime_pipeline import understand_message

    enriched_memory = {
        **memory,
        "_language_context": language_config or {},
        "_recent_voice_context": recent_voice_notes or [],
        "_contact_id": contact_id,
    }
    understanding = understand_message(
        text,
        enriched_memory,
        bot_config,
        conn=conn,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=conversation_id,
    )
    classification = understanding["classification"]
    optimizer_context = load_optimizer_runtime_context(conn, organization_id=organization_id, bot_id=bot_id)
    growth_os_focus = active_growth_os_focus(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        contact_id=contact_id,
        conversation_id=conversation_id,
        bot_config=bot_config,
    ) if conn is not None and organization_id and bot_id else {"enabled": False, "focus_target": None}
    grounded_context = build_grounded_context(
        text=text,
        memory=memory,
        bot_config=bot_config,
        conn=conn,
        organization_id=organization_id,
        bot_id=bot_id,
        contact_id=contact_id,
        conversation_id=conversation_id,
    )
    specialist_route = route_intent_to_specialist(
        text=text,
        classification=classification,
        memory=memory,
        conversation=conversation,
        bot_config=bot_config,
    )
    specialist_route = apply_specialist_route_override(specialist_route, context=optimizer_context)
    specialist_route = apply_growth_os_specialist_focus(specialist_route, focus=growth_os_focus)
    shared_memory = build_shared_memory_context(
        conn=conn,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=conversation_id,
        contact_id=contact_id,
        memory=memory,
        recent_messages=recent_messages,
    )
    execution_plan = plan_runtime_execution(
        text=text,
        conversation=conversation,
        bot=bot,
        classification=classification,
        memory=memory,
        bot_config=bot_config,
        grounded_context=grounded_context,
    )
    execution_plan = apply_execution_plan_overrides(execution_plan, context=optimizer_context)
    execution_plan = apply_growth_os_execution_focus(execution_plan, focus=growth_os_focus)
    execution_plan = apply_specialist_plan(execution_plan, specialist_route, shared_memory)
    supervisor = supervise_specialist_route(
        route=specialist_route,
        classification=classification,
        conversation=conversation,
        shared_memory=shared_memory,
        execution_plan=execution_plan,
    )
    decision = select_runtime_action(
        conversation=conversation,
        bot=bot,
        classification=classification,
        memory=memory,
        bot_config=bot_config,
        execution_plan=execution_plan,
    )
    decision = apply_supervisor_decision(decision, route=specialist_route, supervisor=supervisor)
    decision = apply_handoff_override(decision, context=optimizer_context, classification=classification)
    turn_self_state = build_turn_self_state(
        text=text,
        conversation=conversation,
        classification=classification,
        grounded_context=grounded_context,
        execution_plan=execution_plan,
        decision=decision,
        specialist_route=specialist_route,
        memory=enriched_memory,
        growth_focus=growth_os_focus,
    )
    conversation_self_state = build_conversation_self_state(
        conversation=conversation,
        memory=memory,
        turn_self_state=turn_self_state,
    )
    decision = apply_self_state_decision(
        decision=decision,
        turn_self_state=turn_self_state,
        conversation_self_state=conversation_self_state,
    )
    if growth_os_focus.get("focus_target"):
        decision["growth_os_focus"] = growth_os_focus

    generated = None
    verification = None
    candidate_ranking: dict[str, Any] = {
        "ranker_version": "response_ranker_v1",
        "candidate_count": 0,
        "candidates": [],
        "selected_variant": None,
        "summary": {
            "ranker_version": "response_ranker_v1",
            "candidate_count": 0,
            "selected_variant": None,
            "selected_score": 0.0,
            "runner_up_score": 0.0,
            "selection_margin": 0.0,
        },
    }
    if decision.get("action") in {"respond", "respond_and_schedule_followup", "verify", "request_missing_data"}:
        generated, verification, candidate_ranking = generate_ranked_runtime_reply(
            text=text,
            classification=classification,
            bot_config=bot_config,
            memory=memory,
            recent_messages=recent_messages,
            execution_plan=execution_plan,
            grounded_context=grounded_context,
            specialist_route=specialist_route,
            conn=conn,
            organization_id=organization_id,
            bot_id=bot_id,
            contact_id=contact_id,
            conversation_id=conversation_id,
            recent_voice_notes=recent_voice_notes,
            language_config=language_config,
            optimizer_context=optimizer_context,
        )
    memory_curation = curate_runtime_memory(
        text=text,
        classification=classification,
        memory=memory,
        grounded_context=grounded_context,
    )
    evaluation = evaluate_runtime_outcome(
        decision=decision,
        verification=verification,
        grounded_context=grounded_context,
        generated=generated,
        candidate_ranking=candidate_ranking,
    )
    return {
        "understanding": understanding,
        "grounded_context": grounded_context,
        "specialist_route": specialist_route,
        "shared_memory": shared_memory,
        "plan": execution_plan,
        "decision": decision,
        "supervisor": supervisor,
        "generated": generated,
        "verification": verification,
        "candidate_ranking": candidate_ranking,
        "memory_curation": memory_curation,
        "post_send_evaluation": evaluation,
        "optimizer_context": optimizer_context,
        "growth_os_focus": growth_os_focus,
        "self_state": {"turn": turn_self_state, "conversation": conversation_self_state},
    }
