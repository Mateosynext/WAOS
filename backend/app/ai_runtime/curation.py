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


