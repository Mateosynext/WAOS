from __future__ import annotations

from backend.app.agent_runtime import orchestrate_runtime_turn
from backend.app.db import get_connection, init_db
from backend.app.migrations import apply_migrations
from backend.app.self_state_runtime import apply_self_state_decision, persist_self_state


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


def test_runtime_orchestration_emits_turn_and_conversation_self_state() -> None:
    conversation = {
        "id": "conv_self_1",
        "status": "ai_active",
        "human_takeover": 0,
        "ai_active": 1,
        "paused_until": None,
        "automation_freeze_until": None,
    }
    bot = {"id": "bot_self_1", "status": "active", "ai_paused": 0}
    result = orchestrate_runtime_turn(
        text="Hola, ¿me compartes precio y horario?",
        conversation=conversation,
        bot=bot,
        memory={"lead_stage": "contacted", "lead_score": 10},
        bot_config=_bot_config(),
        recent_messages=[],
        conn=None,
        organization_id=None,
        bot_id="bot_self_1",
        contact_id="ct_self_1",
        conversation_id="conv_self_1",
        recent_voice_notes=[],
        language_config={"default_language": "es", "supported_languages": ["es", "en"]},
    )
    turn = result["self_state"]["turn"]
    conversation_state = result["self_state"]["conversation"]
    assert turn["state_version"] == "self_state_v1"
    assert conversation_state["state_version"] == "self_state_v1"
    assert 0.0 <= turn["confidence"] <= 1.0
    assert turn["next_best_action"] in {"respond", "verify", "request_missing_data", "execute_tool", "trigger_playbook", "escalate", "wait"}
    assert "self_state" in result["decision"]


def test_self_state_can_promote_missing_data_or_handoff_actions() -> None:
    base_decision = {"action": "respond", "reason": "default"}
    updated = apply_self_state_decision(
        decision=base_decision,
        turn_self_state={"confidence": 0.41, "next_best_action": "request_missing_data", "tool_plan": None},
        conversation_self_state={"next_best_action": "request_missing_data"},
    )
    assert updated["action"] == "request_missing_data"

    escalated = apply_self_state_decision(
        decision=base_decision,
        turn_self_state={"confidence": 0.22, "next_best_action": "escalate", "tool_plan": None},
        conversation_self_state={"next_best_action": "escalate"},
    )
    assert escalated["action"] == "handoff"


def test_self_state_persistence_writes_turn_and_conversation_rows() -> None:
    init_db()
    conn = get_connection()
    apply_migrations(conn)
    persist_self_state(
        conn,
        organization_id="org_self",
        bot_id="bot_self",
        conversation_id="conv_self_db",
        contact_id="ct_self_db",
        message_id="msg_self_db",
        turn_self_state={
            "confidence": 0.77,
            "uncertainty_reason": ["insufficient_operational_grounding"],
            "evidence_coverage": 0.5,
            "execution_readiness": 0.61,
            "risk_if_send": "medium",
            "need_verification": True,
            "need_tool": False,
            "need_human": False,
            "next_best_action": "verify",
            "learning_opportunity": ["expand_grounded_knowledge_for_intent"],
        },
        conversation_self_state={
            "confidence": 0.74,
            "uncertainty_reason": ["insufficient_operational_grounding"],
            "evidence_coverage": 0.5,
            "execution_readiness": 0.61,
            "risk_if_send": "medium",
            "need_verification": True,
            "need_tool": False,
            "need_human": False,
            "next_best_action": "verify",
            "learning_opportunity": ["expand_grounded_knowledge_for_intent"],
        },
    )
    turn_count = conn.execute("SELECT COUNT(*) FROM runtime_self_state_turns WHERE conversation_id = ?", ("conv_self_db",)).fetchone()[0]
    conv_row = conn.execute("SELECT next_best_action, need_verification FROM runtime_self_state_conversations WHERE conversation_id = ?", ("conv_self_db",)).fetchone()
    assert turn_count == 1
    assert conv_row[0] == "verify"
    assert int(conv_row[1]) == 1
