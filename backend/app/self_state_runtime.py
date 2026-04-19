from __future__ import annotations

from typing import Any

from .db import execute, fetch_one, table_exists
from .proactive_reasoning_runtime import evaluate_proactive_candidates, materialize_proactive_candidate
from .growth_os_runtime import active_growth_os_focus
from .utils import new_id, to_json, utcnow_iso

_HIGH_CONSEQUENCE_INTENTS = {"pricing", "schedule", "payment", "support", "complaint"}
_TOOL_READY_INTENTS = {"schedule", "payment"}
_PLAYBOOK_INTENTS = {"followup", "payment", "support", "general"}


def _required_evidence_topics(intent: str) -> list[str]:
    mapping = {
        "pricing": ["pricing", "knowledge"],
        "schedule": ["schedule", "knowledge"],
        "payment": ["payment", "knowledge"],
        "support": ["support", "knowledge"],
        "faq": ["faq", "knowledge"],
        "complaint": ["support"],
        "general": [],
    }
    return mapping.get(intent, [])


def _coverage_ratio(grounded_context: dict[str, Any], intent: str) -> float:
    required = _required_evidence_topics(intent)
    if not required:
        return 1.0 if grounded_context.get("source_count") else 0.6
    coverage = grounded_context.get("coverage") or {}
    hit_count = 0
    for topic in required:
        if topic == "knowledge":
            if coverage.get("governed_knowledge") or coverage.get("knowledge"):
                hit_count += 1
        elif coverage.get(topic):
            hit_count += 1
    return round(hit_count / max(1, len(required)), 3)


def _risk_band(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _tool_plan(intent: str, classification: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any] | None:
    if intent == "schedule":
        return {
            "action": "book_appointment",
            "reason": "schedule_intent_ready",
            "payload_hint": {
                "contact_id": memory.get("_contact_id"),
                "requested_slot": classification.get("requested_slot") or classification.get("time_window") or "customer_to_confirm",
                "interest": classification.get("interest") or memory.get("interest"),
            },
        }
    if intent == "payment":
        return {
            "action": "create_payment_link",
            "reason": "payment_intent_ready",
            "payload_hint": {
                "contact_id": memory.get("_contact_id"),
                "amount": classification.get("amount") or memory.get("last_quoted_amount"),
                "currency": memory.get("currency") or "MXN",
            },
        }
    return None

def _growth_focus_tool_plan(growth_focus: dict[str, Any] | None, memory: dict[str, Any]) -> dict[str, Any] | None:
    target = (growth_focus or {}).get("focus_target") or {}
    objective = str(target.get("objective") or "")
    contact_id = target.get("contact_id") or memory.get("_contact_id")
    if objective in {"recover_failed_payment", "recover_pending_payment"}:
        return {
            "action": "create_payment_link",
            "reason": "growth_os_payment_focus",
            "payload_hint": {
                "contact_id": contact_id,
                "conversation_id": target.get("conversation_id"),
                "currency": memory.get("currency") or "MXN",
                "amount": memory.get("last_quoted_amount"),
            },
        }
    return None

def build_turn_self_state(
    *,
    text: str,
    conversation: dict[str, Any],
    classification: dict[str, Any],
    grounded_context: dict[str, Any],
    execution_plan: dict[str, Any],
    decision: dict[str, Any],
    specialist_route: dict[str, Any] | None,
    memory: dict[str, Any],
    growth_focus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intent = str(classification.get("intent") or "general").strip().lower()
    coverage_ratio = _coverage_ratio(grounded_context, intent)
    freshness = str(grounded_context.get("freshness_status") or "unknown")
    requested_human = bool(classification.get("requested_human"))
    urgency_score = int(classification.get("urgency_score", 0) or 0)
    human_takeover = bool(conversation.get("human_takeover"))
    requires_grounding = bool(((execution_plan.get("response_contract") or {}).get("requires_grounding")))
    requires_verification = bool(((execution_plan.get("response_contract") or {}).get("requires_verification")))
    support_status = grounded_context.get("support_status") or {}
    uncertainty_reasons: list[str] = []

    if requires_grounding and coverage_ratio < 0.6:
        uncertainty_reasons.append("insufficient_operational_grounding")
    if freshness == "stale":
        uncertainty_reasons.append("stale_evidence")
    if requested_human:
        uncertainty_reasons.append("explicit_human_request")
    if human_takeover:
        uncertainty_reasons.append("conversation_under_human_takeover")
    if urgency_score >= 80 and intent in _HIGH_CONSEQUENCE_INTENTS:
        uncertainty_reasons.append("high_consequence_urgent_turn")
    if intent == "schedule" and support_status.get("schedule") in {"missing", "unknown"}:
        uncertainty_reasons.append("missing_schedule_grounding")
    if intent == "pricing" and support_status.get("pricing") in {"missing", "unknown"}:
        uncertainty_reasons.append("missing_pricing_grounding")

    confidence = 0.86
    if classification.get("_classifier_source") == "heuristic":
        confidence -= 0.12
    if classification.get("_classifier_source") == "openai":
        confidence += 0.04
    confidence -= max(0.0, (1.0 - coverage_ratio)) * 0.35
    if freshness == "stale":
        confidence -= 0.15
    if urgency_score >= 80:
        confidence -= 0.08
    if requested_human:
        confidence -= 0.18
    confidence = round(max(0.0, min(1.0, confidence)), 3)

    readiness = 0.78
    if human_takeover:
        readiness = 0.0
    else:
        readiness += 0.1 if grounded_context.get("verifiable") else -0.18
        readiness -= 0.2 if freshness == "stale" else 0.0
        readiness -= 0.12 if requested_human else 0.0
        readiness -= 0.1 if conversation.get("status") in {"paused", "blocked", "closed"} else 0.0
    execution_readiness = round(max(0.0, min(1.0, readiness)), 3)

    risk_score = 0.18
    if intent in _HIGH_CONSEQUENCE_INTENTS:
        risk_score += 0.22
    if coverage_ratio < 0.6:
        risk_score += 0.24
    if freshness == "stale":
        risk_score += 0.16
    if requested_human:
        risk_score += 0.2
    if urgency_score >= 80:
        risk_score += 0.15
    risk_if_send = _risk_band(max(0.0, min(1.0, risk_score)))

    need_verification = bool(
        requires_verification
        and (
            intent in _HIGH_CONSEQUENCE_INTENTS
            or coverage_ratio < 0.9
            or freshness == "stale"
            or urgency_score >= 70
        )
    )
    need_tool = bool(intent in _TOOL_READY_INTENTS and execution_readiness >= 0.72 and not requested_human)
    need_human = bool(requested_human or human_takeover or (intent == "complaint" and urgency_score >= 60))

    if need_human:
        next_best_action = "escalate"
    elif conversation.get("status") in {"paused", "blocked", "closed"}:
        next_best_action = "wait"
    elif risk_if_send in {"critical", "high"} and need_verification:
        next_best_action = "verify"
    elif requires_grounding and coverage_ratio < 0.45:
        next_best_action = "request_missing_data"
    elif need_tool:
        next_best_action = "execute_tool"
    elif intent in _PLAYBOOK_INTENTS and str(memory.get("lead_stage") or "") in {"qualified", "stalled", "proposal", "won"} and not need_human:
        next_best_action = "trigger_playbook"
    else:
        next_best_action = "respond"

    focus_target = (growth_focus or {}).get("focus_target") or {}
    focus_action = str((growth_focus or {}).get("recommended_runtime_action") or "")
    focus_config = (((growth_focus or {}).get("config") or {}).get("runtime_priority") or {})
    if focus_target and not need_human and conversation.get("status") not in {"paused", "blocked", "closed"}:
        if focus_action == "execute_tool" and focus_config.get("prioritize_tools", True) and execution_readiness >= 0.72 and risk_if_send != "critical":
            next_best_action = "execute_tool"
            need_tool = True
        elif focus_action == "trigger_playbook" and focus_config.get("prioritize_playbooks", True) and execution_readiness >= 0.64 and risk_if_send in {"low", "medium"}:
            next_best_action = "trigger_playbook"

    tool_plan = _tool_plan(intent, classification, memory) if need_tool else None
    if need_tool and tool_plan is None:
        tool_plan = _growth_focus_tool_plan(growth_focus, memory)

    learning_opportunities: list[str] = []
    if coverage_ratio < 0.7:
        learning_opportunities.append("expand_grounded_knowledge_for_intent")
    if freshness == "stale":
        learning_opportunities.append("refresh_governed_knowledge")
    if need_tool and not grounded_context.get("coverage", {}).get("governed_knowledge"):
        learning_opportunities.append("improve_tool_trigger_context")
    if next_best_action == "request_missing_data":
        learning_opportunities.append("capture_missing_operational_fields_earlier")
    if focus_target:
        learning_opportunities.append("keep_growth_focus_hot_until_outcome")

    return {
        "state_version": "self_state_v1",
        "scope": "turn",
        "intent": intent,
        "confidence": confidence,
        "uncertainty_reason": uncertainty_reasons,
        "evidence_coverage": coverage_ratio,
        "execution_readiness": execution_readiness,
        "risk_if_send": risk_if_send,
        "need_verification": need_verification,
        "need_tool": need_tool,
        "need_human": need_human,
        "next_best_action": next_best_action,
        "learning_opportunity": learning_opportunities,
        "tool_plan": tool_plan,
        "growth_focus": growth_focus or {},
        "decision_snapshot": {
            "selected_action": decision.get("action"),
            "selected_reason": decision.get("reason"),
            "specialist_agent_key": (specialist_route or {}).get("specialist_agent_key"),
            "risk_flags": execution_plan.get("risk_flags") or [],
        },
        "text_preview": str(text or "")[:160],
    }


def build_conversation_self_state(
    *,
    conversation: dict[str, Any],
    memory: dict[str, Any],
    turn_self_state: dict[str, Any],
) -> dict[str, Any]:
    open_threads = 1 if conversation.get("status") not in {"closed", "blocked"} else 0
    confidence = float(turn_self_state.get("confidence") or 0.0)
    if memory.get("lead_stage") in {"qualified", "proposal", "won"}:
        confidence = min(1.0, confidence + 0.04)
    if conversation.get("human_takeover"):
        confidence = min(confidence, 0.35)
    next_best_action = str(turn_self_state.get("next_best_action") or "respond")
    if conversation.get("human_takeover"):
        next_best_action = "wait"
    elif turn_self_state.get("need_human"):
        next_best_action = "escalate"
    return {
        "state_version": "self_state_v1",
        "scope": "conversation",
        "conversation_status": conversation.get("status"),
        "lead_stage": memory.get("lead_stage"),
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "uncertainty_reason": list(turn_self_state.get("uncertainty_reason") or []),
        "evidence_coverage": float(turn_self_state.get("evidence_coverage") or 0.0),
        "execution_readiness": float(turn_self_state.get("execution_readiness") or 0.0),
        "risk_if_send": turn_self_state.get("risk_if_send"),
        "need_verification": bool(turn_self_state.get("need_verification")),
        "need_tool": bool(turn_self_state.get("need_tool")),
        "need_human": bool(turn_self_state.get("need_human")),
        "next_best_action": next_best_action,
        "learning_opportunity": list(turn_self_state.get("learning_opportunity") or []),
        "open_threads": open_threads,
    }


def apply_self_state_decision(
    *,
    decision: dict[str, Any],
    turn_self_state: dict[str, Any],
    conversation_self_state: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(decision or {})
    next_best_action = str(turn_self_state.get("next_best_action") or conversation_self_state.get("next_best_action") or "respond")
    updated["self_state"] = {
        "turn": turn_self_state,
        "conversation": conversation_self_state,
    }
    updated["self_state_selected_action"] = next_best_action
    updated["self_state_confidence"] = turn_self_state.get("confidence")

    mapping = {
        "respond": ("respond", "self_state_respond_ready"),
        "verify": ("verify", "self_state_verify_before_send"),
        "request_missing_data": ("request_missing_data", "self_state_missing_operational_data"),
        "escalate": ("handoff", "self_state_need_human"),
        "wait": ("wait", "self_state_wait"),
        "trigger_playbook": ("trigger_playbook", "self_state_trigger_playbook"),
        "execute_tool": ("execute_tool", "self_state_execute_tool"),
    }
    if next_best_action in mapping:
        updated_action, reason = mapping[next_best_action]
        updated["action"] = updated_action
        updated["reason"] = reason
    if updated.get("action") == "execute_tool" and not turn_self_state.get("tool_plan"):
        updated["action"] = "verify"
        updated["reason"] = "self_state_tool_missing_payload"
    return updated


def persist_self_state(
    conn,
    *,
    organization_id: str | None,
    bot_id: str | None,
    conversation_id: str | None,
    contact_id: str | None,
    message_id: str | None,
    turn_self_state: dict[str, Any],
    conversation_self_state: dict[str, Any],
) -> None:
    if conn is None or not organization_id or not conversation_id:
        return
    now = utcnow_iso()
    if table_exists(conn, "runtime_self_state_turns"):
        execute(
            conn,
            """
            INSERT INTO runtime_self_state_turns (
                id, organization_id, bot_id, conversation_id, contact_id, message_id,
                confidence, uncertainty_reason, evidence_coverage, execution_readiness,
                risk_if_send, need_verification, need_tool, need_human,
                next_best_action, learning_opportunity, state_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("selfturn"),
                organization_id,
                bot_id,
                conversation_id,
                contact_id,
                message_id,
                float(turn_self_state.get("confidence") or 0.0),
                to_json(turn_self_state.get("uncertainty_reason") or []),
                float(turn_self_state.get("evidence_coverage") or 0.0),
                float(turn_self_state.get("execution_readiness") or 0.0),
                turn_self_state.get("risk_if_send"),
                1 if turn_self_state.get("need_verification") else 0,
                1 if turn_self_state.get("need_tool") else 0,
                1 if turn_self_state.get("need_human") else 0,
                turn_self_state.get("next_best_action"),
                to_json(turn_self_state.get("learning_opportunity") or []),
                to_json(turn_self_state),
                now,
            ),
        )
    if table_exists(conn, "runtime_self_state_conversations"):
        existing = fetch_one(conn, "SELECT id FROM runtime_self_state_conversations WHERE conversation_id = ?", (conversation_id,))
        if existing:
            execute(
                conn,
                """
                UPDATE runtime_self_state_conversations
                SET confidence = ?, uncertainty_reason = ?, evidence_coverage = ?, execution_readiness = ?,
                    risk_if_send = ?, need_verification = ?, need_tool = ?, need_human = ?, next_best_action = ?,
                    learning_opportunity = ?, state_json = ?, updated_at = ?
                WHERE conversation_id = ?
                """,
                (
                    float(conversation_self_state.get("confidence") or 0.0),
                    to_json(conversation_self_state.get("uncertainty_reason") or []),
                    float(conversation_self_state.get("evidence_coverage") or 0.0),
                    float(conversation_self_state.get("execution_readiness") or 0.0),
                    conversation_self_state.get("risk_if_send"),
                    1 if conversation_self_state.get("need_verification") else 0,
                    1 if conversation_self_state.get("need_tool") else 0,
                    1 if conversation_self_state.get("need_human") else 0,
                    conversation_self_state.get("next_best_action"),
                    to_json(conversation_self_state.get("learning_opportunity") or []),
                    to_json(conversation_self_state),
                    now,
                    conversation_id,
                ),
            )
        else:
            execute(
                conn,
                """
                INSERT INTO runtime_self_state_conversations (
                    id, organization_id, bot_id, conversation_id, contact_id,
                    confidence, uncertainty_reason, evidence_coverage, execution_readiness,
                    risk_if_send, need_verification, need_tool, need_human,
                    next_best_action, learning_opportunity, state_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("selfconv"),
                    organization_id,
                    bot_id,
                    conversation_id,
                    contact_id,
                    float(conversation_self_state.get("confidence") or 0.0),
                    to_json(conversation_self_state.get("uncertainty_reason") or []),
                    float(conversation_self_state.get("evidence_coverage") or 0.0),
                    float(conversation_self_state.get("execution_readiness") or 0.0),
                    conversation_self_state.get("risk_if_send"),
                    1 if conversation_self_state.get("need_verification") else 0,
                    1 if conversation_self_state.get("need_tool") else 0,
                    1 if conversation_self_state.get("need_human") else 0,
                    conversation_self_state.get("next_best_action"),
                    to_json(conversation_self_state.get("learning_opportunity") or []),
                    to_json(conversation_self_state),
                    now,
                    now,
                ),
            )


def maybe_trigger_self_state_playbook(
    conn,
    *,
    organization_id: str | None,
    bot_id: str | None,
    contact_id: str | None,
    conversation_id: str | None,
    decision: dict[str, Any],
) -> dict[str, Any] | None:
    if conn is None or not organization_id or not bot_id or not contact_id or decision.get("action") != "trigger_playbook":
        return None
    growth_focus = (decision.get("growth_os_focus") or active_growth_os_focus(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        contact_id=contact_id,
        conversation_id=conversation_id,
    )) or {}
    focus_target = growth_focus.get("focus_target") or {}
    if focus_target.get("candidate_id"):
        return materialize_proactive_candidate(
            conn,
            candidate_id=str(focus_target.get("candidate_id")),
            actor_user_id=None,
            record_exposure=True,
            metadata={"trigger": "self_state_runtime", "decision_reason": decision.get("reason"), "source": "growth_os_contact_focus"},
        )
    evaluated = evaluate_proactive_candidates(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        contact_ids=[contact_id],
        conversation_ids=[conversation_id] if conversation_id else None,
        persist=True,
        limit=5,
        metadata={"trigger": "self_state_runtime"},
    )
    items = list(evaluated.get("items") or [])
    if not items:
        return None
    candidate = items[0]
    return materialize_proactive_candidate(
        conn,
        candidate_id=str(candidate.get("id")),
        actor_user_id=None,
        record_exposure=True,
        metadata={"trigger": "self_state_runtime", "decision_reason": decision.get("reason")},
    )
