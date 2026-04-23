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
from .runtime_generation import render_runtime_reply
from .verification import verify_runtime_reply


_PRICE_PATTERN = re.compile(r"(?:\$|usd|mxn|eur|precio|price)\s*[:=]?\s*[0-9][0-9,\.]*", re.IGNORECASE)
_HOURS_PATTERN = re.compile(r"\b(?:[01]?\d|2[0-3])(?::[0-5]\d)?\s*(?:am|pm|hrs?|h)?\b", re.IGNORECASE)



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


