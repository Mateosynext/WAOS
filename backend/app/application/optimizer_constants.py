from __future__ import annotations

DEFAULT_TARGETS: dict[str, tuple[str, ...]] = {
    "prompt_base": ("prompt_version", "prompt_run", "specialist_prompt"),
    "response_variant": ("response_variant",),
    "cta": ("template", "template_version", "nba_policy"),
    "timing": ("timing_policy", "channel"),
    "routing_specialist": ("specialist_agent", "routing_rule", "agent_routing_run"),
    "playbook_proactive": ("playbook", "playbook_version"),
    "handoff_policy": ("handoff", "escalation_policy", "policy_profile"),
    "preferred_channel": ("channel",),
    "collections_template": ("template", "template_version"),
    "reactivation_template": ("template", "template_version"),
    "scheduling_template": ("template", "template_version"),
}

AUTO_ENTITY_TYPES = {entity for items in DEFAULT_TARGETS.values() for entity in items}
