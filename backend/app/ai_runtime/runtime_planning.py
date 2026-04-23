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
    from ..ai import decide_action

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


