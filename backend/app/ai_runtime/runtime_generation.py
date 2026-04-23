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
    from ..ai import generate_response

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


