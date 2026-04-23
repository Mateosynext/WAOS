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


