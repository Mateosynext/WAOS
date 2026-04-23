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



from .grounding import build_grounded_context
from .runtime_planning import plan_runtime_execution, select_runtime_action
from .ranking import generate_ranked_runtime_reply
from .curation import curate_runtime_memory
from .evaluation import evaluate_runtime_outcome

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
    from ..runtime_pipeline import understand_message

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


