from __future__ import annotations

from typing import Any

from .db import fetch_all, fetch_one, table_exists
from .repositories.optimizer import insert_runtime_optimizer_audit, list_active_experiments, list_control_rows, proposal_target_name
from .utils import from_json, new_id, to_json, utcnow_iso
from .world_class_ext import create_shadow_run

_TARGETS = {
    "prompt_base",
    "response_variant",
    "cta",
    "timing",
    "routing_specialist",
    "playbook_proactive",
    "handoff_policy",
    "preferred_channel",
    "collections_template",
    "reactivation_template",
    "scheduling_template",
}


def _load_control_rows(conn, *, organization_id: str, bot_id: str | None) -> list[dict[str, Any]]:
    return list_control_rows(conn, organization_id=organization_id, bot_id=bot_id)


def load_optimizer_runtime_context(conn, *, organization_id: str | None, bot_id: str | None) -> dict[str, Any]:
    if conn is None or not organization_id:
        return {"targets": {}, "experiments": {}}
    targets: dict[str, dict[str, Any]] = {}
    for row in _load_control_rows(conn, organization_id=organization_id, bot_id=bot_id):
        target_name = str(row.get("target_name") or "").strip()
        if not target_name or target_name not in _TARGETS or target_name in targets:
            continue
        current = from_json(row.get("current_state_json"), {})
        targets[target_name] = {**row, "current_state": current}
    experiments: dict[str, dict[str, Any]] = {}
    if table_exists(conn, "optimizer_experiments"):
        sql = (
            "SELECT * FROM optimizer_experiments WHERE organization_id = ? "
            "AND status IN ('running', 'planned', 'winner_selected') ORDER BY updated_at DESC"
        )
        params: list[Any] = [organization_id]
        if bot_id:
            sql = sql.replace(" ORDER BY", " AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY")
            params.append(bot_id)
        for row in list_active_experiments(conn, organization_id=organization_id, bot_id=bot_id):
            target_name = proposal_target_name(conn, row.get("proposal_id"))
            if target_name and target_name not in experiments:
                experiments[target_name] = {**row, "guardrails": from_json(row.get("guardrails_json"), {})}
    return {"targets": targets, "experiments": experiments}


def preferred_entity(context: dict[str, Any] | None, target_name: str) -> dict[str, Any]:
    state = ((context or {}).get("targets") or {}).get(target_name) or {}
    current = state.get("current_state") or {}
    return dict(current.get("preferred_entity") or {})


def preferred_entity_id(context: dict[str, Any] | None, target_name: str) -> str | None:
    entity = preferred_entity(context, target_name)
    value = entity.get("entity_id")
    return str(value) if value not in {None, ""} else None


def preferred_channel(context: dict[str, Any] | None) -> str | None:
    return preferred_entity_id(context, "preferred_channel")


def apply_specialist_route_override(route: dict[str, Any], *, context: dict[str, Any] | None) -> dict[str, Any]:
    preferred = preferred_entity_id(context, "routing_specialist")
    if not preferred:
        return route
    updated = dict(route or {})
    updated["specialist_agent_key"] = preferred
    updated["optimizer_override"] = {"target_name": "routing_specialist", "preferred_entity_id": preferred}
    reasons = list(updated.get("route_reason") or [])
    if "optimizer_preferred_specialist" not in reasons:
        reasons.append("optimizer_preferred_specialist")
    updated["route_reason"] = reasons
    return updated


def apply_handoff_override(decision: dict[str, Any], *, context: dict[str, Any] | None, classification: dict[str, Any] | None = None) -> dict[str, Any]:
    preferred = preferred_entity_id(context, "handoff_policy")
    if not preferred:
        return decision
    classification = classification or {}
    normalized = preferred.lower()
    updated = dict(decision or {})
    if normalized in {"human_first", "always_handoff", "handoff"} and classification.get("requested_human"):
        updated["action"] = "handoff"
        updated["reason"] = "optimizer_preferred_handoff"
        updated["policy"] = normalized
    elif normalized in {"bot_first", "avoid_handoff", "respond"} and updated.get("action") == "handoff" and not classification.get("requested_human"):
        updated["action"] = "respond"
        updated["reason"] = "optimizer_avoided_handoff"
        updated["policy"] = normalized
    updated["optimizer_override"] = {"target_name": "handoff_policy", "preferred_entity_id": preferred}
    return updated


def apply_candidate_spec_overrides(specs: list[dict[str, Any]], *, context: dict[str, Any] | None) -> list[dict[str, Any]]:
    preferred_variant = preferred_entity_id(context, "response_variant")
    preferred_cta = preferred_entity_id(context, "cta")
    prompt_base = preferred_entity_id(context, "prompt_base")
    ranked: list[dict[str, Any]] = []
    for spec in specs:
        item = dict(spec)
        if preferred_cta:
            item["cta_style"] = preferred_cta
        if prompt_base:
            item["prompt_base_override"] = prompt_base
        item["optimizer_preferred"] = bool(preferred_variant and preferred_variant == item.get("variant_key"))
        ranked.append(item)
    if preferred_variant:
        ranked.sort(key=lambda item: (0 if item.get("variant_key") == preferred_variant else 1, ))
    return ranked


def apply_execution_plan_overrides(execution_plan: dict[str, Any], *, context: dict[str, Any] | None) -> dict[str, Any]:
    updated = dict(execution_plan or {})
    response_contract = dict(updated.get("response_contract") or {})
    rendering_hints = dict(updated.get("rendering_hints") or {})
    channel = preferred_channel(context)
    if channel:
        response_contract["target_channel"] = channel
    cta = preferred_entity_id(context, "cta")
    if cta:
        rendering_hints["optimizer_cta_style"] = cta
    prompt_base = preferred_entity_id(context, "prompt_base")
    if prompt_base:
        response_contract["prompt_base_override"] = prompt_base
    updated["response_contract"] = response_contract
    updated["rendering_hints"] = rendering_hints
    if context and context.get("targets"):
        updated["optimizer_context"] = {key: value.get("current_state") for key, value in (context.get("targets") or {}).items()}
    return updated


def followup_override(rule: dict[str, Any], *, context: dict[str, Any] | None, intent: str) -> dict[str, Any]:
    updated = dict(rule or {})
    channel = preferred_channel(context)
    if channel:
        updated["channel"] = channel
    timing = preferred_entity_id(context, "timing")
    if timing:
        current_delay = int(updated.get("delay_minutes") or 0)
        if any(token in timing for token in ["fast", "15", "30", "soon"]):
            updated["delay_minutes"] = 15 if current_delay <= 0 else min(current_delay, 15)
        elif any(token in timing for token in ["slow", "later", "120", "180"]):
            updated["delay_minutes"] = max(current_delay, 120)
        updated["timing_policy_id"] = timing
    template_target = {
        "payment": "collections_template",
        "pricing": "collections_template",
        "general": "reactivation_template",
        "faq": "reactivation_template",
        "schedule": "scheduling_template",
    }.get(intent)
    if template_target:
        template_id = preferred_entity_id(context, template_target)
        if template_id:
            updated["template_version_id"] = template_id
            updated.setdefault("message_template", f"optimizer_template::{template_id}")
    return updated


def proactive_override(*, context: dict[str, Any] | None, playbook_key: str, priority_score: float, suggested_send_at: str, channel: str, message_text: str) -> dict[str, Any]:
    updated_priority = float(priority_score)
    preferred_playbook = preferred_entity_id(context, "playbook_proactive")
    preferred_channel_id = preferred_channel(context)
    timing = preferred_entity_id(context, "timing")
    if preferred_playbook:
        if preferred_playbook == playbook_key:
            updated_priority += 12.0
        else:
            updated_priority -= 6.0
    if timing and "15" in timing:
        updated_send_at = suggested_send_at
    else:
        updated_send_at = suggested_send_at
    template_target = "collections_template" if "payment" in playbook_key else ("reactivation_template" if any(token in playbook_key for token in ["reactivation", "churn", "repeat_purchase"]) else ("scheduling_template" if "appointment" in playbook_key else None))
    template_version_id = preferred_entity_id(context, template_target) if template_target else None
    return {
        "priority_score": round(updated_priority, 2),
        "suggested_send_at": updated_send_at,
        "channel": preferred_channel_id or channel,
        "message_text": message_text,
        "template_version_id": template_version_id,
        "preferred_playbook": preferred_playbook,
    }


def maybe_record_shadow_selection(
    conn,
    *,
    context: dict[str, Any] | None,
    organization_id: str | None,
    bot_id: str | None,
    conversation_id: str | None,
    target_name: str,
    production_output: Any,
    candidate_output: Any,
) -> None:
    if conn is None or not organization_id:
        return
    experiment = ((context or {}).get("experiments") or {}).get(target_name) or {}
    experiment_key = experiment.get("experiment_key")
    if not experiment_key:
        return
    create_shadow_run(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=conversation_id,
        experiment_key=experiment_key,
        production_output=production_output,
        candidate_output=candidate_output,
    )


def create_runtime_optimizer_audit(
    conn,
    *,
    organization_id: str | None,
    bot_id: str | None,
    target_name: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    insert_runtime_optimizer_audit(conn, organization_id=organization_id, bot_id=bot_id, target_name=target_name, event_type=event_type, payload=payload)
