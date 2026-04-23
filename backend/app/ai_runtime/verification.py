from __future__ import annotations

import re
from typing import Any

from ..contact_intelligence import relationship_snapshot
from ..knowledge_runtime import governed_knowledge_summary, search_governed_knowledge
from ..response_ranking_runtime import (
    build_ranking_summary,
    build_response_candidate_specs,
    infer_reply_language,
    score_response_candidate,
)
from ..multi_agent_runtime import (
    apply_specialist_plan,
    apply_supervisor_decision,
    build_shared_memory_context,
    route_intent_to_specialist,
    supervise_specialist_route,
)
from ..optimizer_runtime import (
    apply_candidate_spec_overrides,
    apply_execution_plan_overrides,
    apply_handoff_override,
    apply_specialist_route_override,
    create_runtime_optimizer_audit,
    load_optimizer_runtime_context,
    maybe_record_shadow_selection,
)
from ..growth_os_runtime import apply_growth_os_execution_focus, apply_growth_os_specialist_focus, active_growth_os_focus
from ..self_state_runtime import (
    apply_self_state_decision,
    build_conversation_self_state,
    build_turn_self_state,
)


_PRICE_PATTERN = re.compile(r"(?:\$|usd|mxn|eur|precio|price)\s*[:=]?\s*[0-9][0-9,\.]*", re.IGNORECASE)
_HOURS_PATTERN = re.compile(r"\b(?:[01]?\d|2[0-3])(?::[0-5]\d)?\s*(?:am|pm|hrs?|h)?\b", re.IGNORECASE)



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


