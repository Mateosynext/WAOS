from __future__ import annotations

from backend.app.agent_runtime import (
    build_grounded_context,
    orchestrate_runtime_turn,
    plan_runtime_execution,
    verify_runtime_reply,
)



def _bot_config(*, with_prices: bool = True, with_hours: bool = True) -> dict:
    business_knowledge = {
        "services": ["Citas", "Cotizaciones"],
        "faqs": [{"q": "¿Dónde están?", "a": "Estamos en Av. Reforma 100."}],
        "location": "Av. Reforma 100",
    }
    if with_prices:
        business_knowledge["prices"] = [{"name": "Consulta", "price": "$799 MXN"}]
    if with_hours:
        business_knowledge["hours"] = "Lunes a viernes de 9:00 a 18:00"
    return {
        "identity": {"business_name": "WAOS Clinic", "language": "es"},
        "business_knowledge": business_knowledge,
        "objective": {"primary": "book_more"},
        "personality": {"tone": "clear"},
        "rules": {},
        "handoff": {"sensitive_keywords": ["humano", "asesor"]},
    }



def test_planner_builds_explicit_tool_orchestration_for_pricing() -> None:
    classification = {
        "intent": "pricing",
        "requested_human": False,
        "urgency_score": 35,
    }
    grounded = build_grounded_context(text="Quiero precio", memory={}, bot_config=_bot_config(), conn=None)
    plan = plan_runtime_execution(
        text="Quiero precio",
        conversation={"human_takeover": 0},
        bot={"status": "active"},
        classification=classification,
        memory={"lead_stage": "contacted"},
        bot_config=_bot_config(),
        grounded_context=grounded,
    )
    assert plan["planner_version"] == "agentic_runtime_v1"
    assert plan["response_contract"]["requires_grounding"] is True
    assert any(item["tool"] == "grounded_context" for item in plan["tool_orchestration"])
    assert "factual_support_for_operational_claims" in plan["verification_checks"]



def test_verifier_rewrites_unsupported_pricing_claim() -> None:
    bot_config = _bot_config(with_prices=False)
    grounded = build_grounded_context(text="precio", memory={}, bot_config=bot_config, conn=None)
    plan = plan_runtime_execution(
        text="precio",
        conversation={"human_takeover": 0},
        bot={"status": "active"},
        classification={"intent": "pricing", "requested_human": False, "urgency_score": 20},
        memory={},
        bot_config=bot_config,
        grounded_context=grounded,
    )
    verification = verify_runtime_reply(
        text="precio",
        response_text="Claro, el precio es $3,999 MXN y lo puedes pagar hoy.",
        classification={"intent": "pricing"},
        grounded_context=grounded,
        bot_config=bot_config,
        execution_plan=plan,
    )
    assert verification["status"] == "rewritten"
    assert "3999" not in verification["response_text"]
    assert "confirmar" in verification["response_text"].lower()



def test_orchestrate_runtime_turn_exposes_separate_agentic_stages() -> None:
    conversation = {
        "id": "conv_1",
        "status": "ai_active",
        "human_takeover": 0,
        "ai_active": 1,
        "paused_until": None,
        "automation_freeze_until": None,
    }
    bot = {
        "id": "bot_1",
        "status": "active",
        "ai_paused": 0,
    }
    result = orchestrate_runtime_turn(
        text="Hola, ¿me compartes precio y horario?",
        conversation=conversation,
        bot=bot,
        memory={"lead_stage": "contacted", "lead_score": 10},
        bot_config=_bot_config(),
        recent_messages=[],
        conn=None,
        organization_id=None,
        bot_id="bot_1",
        contact_id="ct_1",
        conversation_id="conv_1",
        recent_voice_notes=[],
        language_config={"default_language": "es", "supported_languages": ["es", "en"]},
    )
    assert set(result.keys()) >= {
        "understanding",
        "grounded_context",
        "plan",
        "decision",
        "verification",
        "memory_curation",
        "post_send_evaluation",
    }
    assert result["plan"]["planner_version"] == "agentic_runtime_v1"
    assert result["decision"]["decision_layer"] == "policy_aware_executor"
    assert result["verification"]["verifier_version"] == "agentic_runtime_verifier_v1"
    assert result["memory_curation"]["curator_version"] == "memory_curator_v1"
    assert result["post_send_evaluation"]["evaluator_version"] == "post_send_evaluator_v1"
