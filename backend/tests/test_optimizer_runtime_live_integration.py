from app.optimizer_runtime import (
    apply_candidate_spec_overrides,
    apply_execution_plan_overrides,
    apply_handoff_override,
    apply_specialist_route_override,
    followup_override,
    proactive_override,
)


def _context():
    return {
        "targets": {
            "response_variant": {"current_state": {"preferred_entity": {"entity_id": "conversion_push"}}},
            "cta": {"current_state": {"preferred_entity": {"entity_id": "guided"}}},
            "prompt_base": {"current_state": {"preferred_entity": {"entity_id": "prompt_sales_v2"}}},
            "routing_specialist": {"current_state": {"preferred_entity": {"entity_id": "collections"}}},
            "handoff_policy": {"current_state": {"preferred_entity": {"entity_id": "bot_first"}}},
            "preferred_channel": {"current_state": {"preferred_entity": {"entity_id": "instagram"}}},
            "timing": {"current_state": {"preferred_entity": {"entity_id": "timing_fast_15m"}}},
            "playbook_proactive": {"current_state": {"preferred_entity": {"entity_id": "playbook_payment_retry_recovery"}}},
            "collections_template": {"current_state": {"preferred_entity": {"entity_id": "tpl_collections_v9"}}},
        }
    }


def test_response_variant_and_plan_overrides_are_applied():
    specs = [
        {"variant_key": "balanced_default", "cta_style": "soft"},
        {"variant_key": "conversion_push", "cta_style": "strong"},
    ]
    reordered = apply_candidate_spec_overrides(specs, context=_context())
    assert reordered[0]["variant_key"] == "conversion_push"
    assert reordered[0]["cta_style"] == "guided"
    assert reordered[0]["prompt_base_override"] == "prompt_sales_v2"

    plan = apply_execution_plan_overrides({"response_contract": {"target_channel": "whatsapp"}}, context=_context())
    assert plan["response_contract"]["target_channel"] == "instagram"
    assert plan["response_contract"]["prompt_base_override"] == "prompt_sales_v2"


def test_routing_handoff_followup_and_proactive_overrides_are_applied():
    route = apply_specialist_route_override({"specialist_agent_key": "sales", "route_reason": []}, context=_context())
    assert route["specialist_agent_key"] == "collections"

    decision = apply_handoff_override({"action": "handoff", "reason": "default"}, context=_context(), classification={"requested_human": False})
    assert decision["action"] == "respond"

    followup = followup_override({"delay_minutes": 120, "message_template": "Hola"}, context=_context(), intent="payment")
    assert followup["delay_minutes"] == 15
    assert followup["channel"] == "instagram"
    assert followup["template_version_id"] == "tpl_collections_v9"

    proactive = proactive_override(
        context=_context(),
        playbook_key="playbook_payment_retry_recovery",
        priority_score=80,
        suggested_send_at="2026-04-18T12:00:00Z",
        channel="whatsapp",
        message_text="Pago pendiente",
    )
    assert proactive["priority_score"] > 80
    assert proactive["channel"] == "instagram"
    assert proactive["template_version_id"] == "tpl_collections_v9"
