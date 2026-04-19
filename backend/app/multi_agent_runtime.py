from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .agent_policy_runtime import build_policy_route_summary
from .db import execute, fetch_all, fetch_one, table_exists
from .utils import from_json, new_id, to_json, utcnow_iso


@dataclass(frozen=True)
class SpecialistAgentProfile:
    key: str
    version: str
    prompt_base_id: str
    objective: str
    tone: str
    allowed_tools: tuple[str, ...]
    risk_level: str
    success_metrics: tuple[str, ...]
    escalation_criteria: tuple[str, ...]
    funnel_stage: str


SPECIALIST_AGENTS: dict[str, SpecialistAgentProfile] = {
    "booking": SpecialistAgentProfile(
        key="booking",
        version="booking_specialist_v1",
        prompt_base_id="prompt_specialist_booking_v1",
        objective="maximize_scheduled_appointments",
        tone="clear_fast_confirmatory",
        allowed_tools=("book_appointment", "reschedule", "grounded_context"),
        risk_level="medium",
        success_metrics=("appointments_booked", "show_rate", "time_to_booking"),
        escalation_criteria=("calendar_conflict_unresolved", "medical_or_safety_risk", "requested_human"),
        funnel_stage="booking",
    ),
    "sales": SpecialistAgentProfile(
        key="sales",
        version="sales_specialist_v1",
        prompt_base_id="prompt_specialist_sales_v1",
        objective="maximize_revenue_and_stage_progression",
        tone="consultative_confident",
        allowed_tools=("update_contact_stage", "create_payment_link", "grounded_context"),
        risk_level="medium",
        success_metrics=("revenue", "close_rate", "proposal_to_payment_rate"),
        escalation_criteria=("discount_exception", "high_value_deal", "requested_human"),
        funnel_stage="sales",
    ),
    "support": SpecialistAgentProfile(
        key="support",
        version="support_specialist_v1",
        prompt_base_id="prompt_specialist_support_v1",
        objective="resolve_issue_without_regression",
        tone="empathetic_precise",
        allowed_tools=("grounded_context",),
        risk_level="high",
        success_metrics=("resolution_rate", "csat_proxy", "reopen_rate"),
        escalation_criteria=("compliance_or_legal_risk", "repeat_failure", "requested_human"),
        funnel_stage="support",
    ),
    "collections": SpecialistAgentProfile(
        key="collections",
        version="collections_specialist_v1",
        prompt_base_id="prompt_specialist_collections_v1",
        objective="recover_payment_with_low_friction",
        tone="firm_respectful",
        allowed_tools=("create_payment_link", "send_receipt", "update_contact_stage"),
        risk_level="high",
        success_metrics=("payment_started", "payment_completed", "days_sales_outstanding_reduction"),
        escalation_criteria=("refund_or_chargeback", "payment_dispute", "requested_human"),
        funnel_stage="payment",
    ),
    "recovery": SpecialistAgentProfile(
        key="recovery",
        version="recovery_specialist_v1",
        prompt_base_id="prompt_specialist_recovery_v1",
        objective="reactivate_stalled_conversations",
        tone="persistent_helpful",
        allowed_tools=("book_appointment", "create_payment_link", "update_contact_stage", "grounded_context"),
        risk_level="medium",
        success_metrics=("reactivation_rate", "reply_rate", "recovered_pipeline_value"),
        escalation_criteria=("multiple_failed_attempts", "requested_human"),
        funnel_stage="reactivation",
    ),
    "retention": SpecialistAgentProfile(
        key="retention",
        version="retention_specialist_v1",
        prompt_base_id="prompt_specialist_retention_v1",
        objective="avoid_churn_and_preserve_ltv",
        tone="empathetic_retention_oriented",
        allowed_tools=("reschedule", "update_contact_stage", "grounded_context"),
        risk_level="high",
        success_metrics=("saved_customers", "reschedule_rate", "ltv_retained"),
        escalation_criteria=("cancellation_risk", "refund_or_legal_risk", "requested_human"),
        funnel_stage="retention",
    ),
    "general": SpecialistAgentProfile(
        key="general",
        version="general_specialist_v1",
        prompt_base_id="prompt_specialist_general_v1",
        objective="triage_and_clarify",
        tone="helpful_brief",
        allowed_tools=("grounded_context",),
        risk_level="low",
        success_metrics=("routing_accuracy", "time_to_clarity"),
        escalation_criteria=("requested_human",),
        funnel_stage="triage",
    ),
}


_INTENT_TO_AGENT = {
    "schedule": "booking",
    "booking": "booking",
    "appointment": "booking",
    "reschedule": "booking",
    "pricing": "sales",
    "quote": "sales",
    "sales": "sales",
    "payment": "collections",
    "billing": "collections",
    "collections": "collections",
    "support": "support",
    "faq": "support",
    "complaint": "support",
    "reactivation": "recovery",
    "followup": "recovery",
    "retention": "retention",
    "cancel": "retention",
    "churn": "retention",
}


def _normalized(text: str) -> str:
    return str(text or "").strip().lower()


def _heuristic_intent_family(text: str, intent: str) -> str:
    lower = _normalized(text)
    if any(token in lower for token in ("agenda", "agendar", "cita", "horario", "reagendar", "disponibilidad")):
        return "booking"
    if any(token in lower for token in ("precio", "cotizacion", "promo", "comprar", "vender", "plan")):
        return "sales"
    if any(token in lower for token in ("pago", "cobro", "factura", "link de pago", "recibo", "adeudo")):
        return "collections"
    if any(token in lower for token in ("ayuda", "soporte", "problema", "error", "no funciona", "queja")):
        return "support"
    if any(token in lower for token in ("sigues ahi", "retomar", "reactivar", "volvi", "aun me interesa")):
        return "recovery"
    if any(token in lower for token in ("cancelar", "baja", "ya no", "molesto", "dejar", "permanecer")):
        return "retention"
    return _INTENT_TO_AGENT.get(_normalized(intent), "general")


def route_intent_to_specialist(
    *,
    text: str,
    classification: dict[str, Any],
    memory: dict[str, Any],
    conversation: dict[str, Any],
    bot_config: dict[str, Any],
) -> dict[str, Any]:
    intent = _normalized(classification.get("intent") or "general")
    requested_human = bool(classification.get("requested_human"))
    urgency_score = int(classification.get("urgency_score", 0) or 0)
    lead_stage = _normalized(memory.get("lead_stage") or "")
    family = _heuristic_intent_family(text, intent)
    profile = SPECIALIST_AGENTS.get(family, SPECIALIST_AGENTS["general"])

    confidence = 0.55
    reasons: list[str] = []
    if intent and _INTENT_TO_AGENT.get(intent) == profile.key:
        confidence += 0.2
        reasons.append(f"intent:{intent}")
    if family != "general":
        confidence += 0.1
        reasons.append(f"heuristic_family:{family}")
    if requested_human:
        reasons.append("requested_human")
    if urgency_score >= 70:
        reasons.append("high_urgency")
        if profile.key in {"support", "collections", "retention"}:
            confidence += 0.05
    if lead_stage in {"nuevo", "hot", "propuesta", "negociacion"} and profile.key == "sales":
        confidence += 0.05
        reasons.append(f"lead_stage:{lead_stage}")
    if conversation.get("human_takeover"):
        reasons.append("existing_human_takeover")

    confidence = round(max(0.05, min(0.99, confidence)), 2)
    return {
        "router_version": "intent_router_v1",
        "intent_detected": intent or "general",
        "intent_family": family,
        "confidence": confidence,
        "route_reason": reasons or ["default_generalist_fallback"],
        "specialist_agent_key": profile.key,
        "specialist_agent_version": profile.version,
        "prompt_base_id": profile.prompt_base_id,
        "objective": profile.objective,
        "tone": profile.tone,
        "allowed_tools": list(profile.allowed_tools),
        "risk_policy": {
            "level": profile.risk_level,
            "money_actions_require_confirmation": profile.key in {"sales", "collections"},
            "support_escalates_on_unknowns": profile.key == "support",
            "retention_never_promises_refund": profile.key == "retention",
        },
        "success_metrics": list(profile.success_metrics),
        "escalation_criteria": list(profile.escalation_criteria),
        "funnel_stage": profile.funnel_stage,
        "shared_memory_scope": ["contact_memory", "appointments", "payments", "lead_state", "recent_outcomes"],
    }


def build_shared_memory_context(
    *,
    conn,
    organization_id: str | None,
    bot_id: str | None,
    conversation_id: str | None,
    contact_id: str | None,
    memory: dict[str, Any],
    recent_messages: list[dict[str, Any]],
) -> dict[str, Any]:
    if conn is None:
        return {
            "memory_version": "shared_memory_v1",
            "contact_memory": memory,
            "recent_messages": recent_messages[-6:],
            "appointments": [],
            "payments": [],
            "leads": [],
            "outcomes": [],
            "tool_executions": [],
        }

    appointments = fetch_all(
        conn,
        "SELECT id, scheduled_for, status, provider, updated_at FROM appointments WHERE conversation_id = ? OR contact_id = ? ORDER BY updated_at DESC LIMIT 5",
        (conversation_id, contact_id),
    ) if conversation_id or contact_id else []
    payments = fetch_all(
        conn,
        "SELECT id, amount, currency, status, payment_link_url, updated_at FROM commerce_payments WHERE conversation_id = ? OR contact_id = ? ORDER BY updated_at DESC LIMIT 5",
        (conversation_id, contact_id),
    ) if conversation_id or contact_id else []
    leads = fetch_all(
        conn,
        "SELECT id, stage, estimated_amount, next_action, close_probability, updated_at FROM crm_leads WHERE conversation_id = ? OR contact_id = ? ORDER BY updated_at DESC LIMIT 3",
        (conversation_id, contact_id),
    ) if conversation_id or contact_id else []
    outcomes = fetch_all(
        conn,
        "SELECT id, event_name, event_category, event_timestamp, value_number FROM outcome_events WHERE conversation_id = ? OR contact_id = ? ORDER BY event_timestamp DESC LIMIT 5",
        (conversation_id, contact_id),
    ) if (conversation_id or contact_id) and table_exists(conn, "outcome_events") else []
    tool_executions = fetch_all(
        conn,
        "SELECT id, action, status, adapter_key, provider, completed_at, created_at FROM tool_execution_runs WHERE conversation_id = ? OR contact_id = ? ORDER BY COALESCE(completed_at, created_at) DESC LIMIT 5",
        (conversation_id, contact_id),
    ) if (conversation_id or contact_id) and table_exists(conn, "tool_execution_runs") else []

    highlights: list[str] = []
    latest_payment = payments[0] if payments else None
    latest_appointment = appointments[0] if appointments else None
    latest_lead = leads[0] if leads else None
    if latest_payment:
        highlights.append(f"payment_status:{latest_payment.get('status')}")
    if latest_appointment:
        highlights.append(f"appointment_status:{latest_appointment.get('status')}")
    if latest_lead:
        highlights.append(f"lead_stage:{latest_lead.get('stage')}")
    if memory.get("summary"):
        highlights.append("memory_summary_available")
    return {
        "memory_version": "shared_memory_v1",
        "contact_memory": memory,
        "recent_messages": recent_messages[-6:],
        "appointments": [dict(item) if not isinstance(item, dict) else item for item in appointments],
        "payments": [dict(item) if not isinstance(item, dict) else item for item in payments],
        "leads": [dict(item) if not isinstance(item, dict) else item for item in leads],
        "outcomes": [dict(item) if not isinstance(item, dict) else item for item in outcomes],
        "tool_executions": [dict(item) if not isinstance(item, dict) else item for item in tool_executions],
        "highlights": highlights,
    }


def apply_specialist_plan(base_plan: dict[str, Any], route: dict[str, Any], shared_memory: dict[str, Any], policy_evaluation: dict[str, Any] | None = None) -> dict[str, Any]:
    plan = dict(base_plan)
    objectives = list(plan.get("objectives") or [])
    objectives.insert(0, route.get("objective"))
    seen: set[str] = set()
    plan["objectives"] = [item for item in objectives if not (item in seen or seen.add(item))]

    tool_orchestration = list(plan.get("tool_orchestration") or [])
    for tool in route.get("allowed_tools") or []:
        if tool == "grounded_context":
            continue
        if not any(item.get("tool") == tool for item in tool_orchestration):
            tool_orchestration.append({"tool": tool, "mode": "specialist_allowed", "required": False})
    plan["tool_orchestration"] = tool_orchestration

    risk_flags = list(plan.get("risk_flags") or [])
    if route.get("risk_policy", {}).get("level") in {"medium", "high"}:
        risk_flags.append(f"specialist_risk:{route['risk_policy']['level']}")
    if shared_memory.get("payments") and route.get("specialist_agent_key") in {"sales", "collections"}:
        risk_flags.append("payment_context_present")
    if shared_memory.get("appointments") and route.get("specialist_agent_key") in {"booking", "retention"}:
        risk_flags.append("appointment_context_present")
    plan["risk_flags"] = risk_flags

    response_contract = dict(plan.get("response_contract") or {})
    response_contract["specialist_agent_required"] = True
    response_contract["specialist_agent_key"] = route.get("specialist_agent_key")
    response_contract["prompt_base_id"] = route.get("prompt_base_id")
    response_contract["requires_supervisor_review"] = route.get("risk_policy", {}).get("level") == "high"
    plan["response_contract"] = response_contract

    plan["specialist"] = {
        "agent_key": route.get("specialist_agent_key"),
        "agent_version": route.get("specialist_agent_version"),
        "prompt_base_id": route.get("prompt_base_id"),
        "allowed_tools": route.get("allowed_tools"),
        "tone": route.get("tone"),
        "success_metrics": route.get("success_metrics"),
        "shared_memory_highlights": shared_memory.get("highlights") or [],
        "funnel_stage": route.get("funnel_stage"),
        "policy": policy_evaluation or build_policy_route_summary(route),
    }
    return plan


def supervise_specialist_route(
    *,
    route: dict[str, Any],
    classification: dict[str, Any],
    conversation: dict[str, Any],
    shared_memory: dict[str, Any],
    execution_plan: dict[str, Any],
    policy_evaluation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    requested_human = bool(classification.get("requested_human"))
    intent = _normalized(classification.get("intent") or "general")
    urgency_score = int(classification.get("urgency_score", 0) or 0)
    if requested_human:
        reasons.append("requested_human")
    if conversation.get("human_takeover"):
        reasons.append("conversation_already_in_takeover")
    if route.get("risk_policy", {}).get("level") == "high":
        reasons.append("high_risk_specialist")
    if intent in {"payment", "complaint", "support"} and urgency_score >= 70:
        reasons.append("high_consequence_intent")
    if route.get("specialist_agent_key") == "collections" and shared_memory.get("payments"):
        latest = (shared_memory.get("payments") or [{}])[0]
        if _normalized(latest.get("status")) in {"failed", "refunded", "disputed"}:
            reasons.append("payment_dispute_or_failed_state")
    if route.get("specialist_agent_key") == "support" and not execution_plan.get("response_contract", {}).get("requires_grounding"):
        reasons.append("support_without_grounding_contract")
    if policy_evaluation:
        enforcement = (policy_evaluation.get("decision") or {}).get("enforcement")
        if enforcement == "block":
            reasons.append("policy_engine_block")
        if (policy_evaluation.get("decision") or {}).get("requires_human_review"):
            reasons.append("policy_engine_requires_human_review")
        if (policy_evaluation.get("sla_state") or {}).get("status") == "breached":
            reasons.append("policy_sla_breached")

    force_handoff = requested_human or conversation.get("human_takeover") or (policy_evaluation or {}).get("decision", {}).get("enforcement") == "block"
    escalation_target = "human" if force_handoff else ("supervisor" if reasons else None)
    return {
        "supervisor_version": "specialist_supervisor_v1",
        "needs_review": bool(reasons),
        "force_handoff": bool(force_handoff),
        "escalation_target": escalation_target,
        "risk_reasons": reasons,
        "approved_specialist_agent": route.get("specialist_agent_key"),
        "allowed_tools": route.get("allowed_tools") or [],
        "success_metrics": route.get("success_metrics") or [],
        "policy": policy_evaluation or build_policy_route_summary(route),
    }


def apply_supervisor_decision(
    decision: dict[str, Any],
    *,
    route: dict[str, Any],
    supervisor: dict[str, Any],
) -> dict[str, Any]:
    merged = {
        **decision,
        "specialist_agent": route.get("specialist_agent_key"),
        "specialist_agent_version": route.get("specialist_agent_version"),
        "prompt_base_id": route.get("prompt_base_id"),
        "supervisor": supervisor,
    }
    if supervisor.get("force_handoff"):
        merged["action"] = "handoff"
        merged["reason"] = "specialist_supervisor_escalation"
        merged["policy"] = "specialist_supervisor"
    return merged


def persist_agent_route_run(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    conversation_id: str | None,
    contact_id: str | None,
    message_id: str | None,
    text: str,
    classification: dict[str, Any],
    route: dict[str, Any],
    shared_memory: dict[str, Any],
    execution_plan: dict[str, Any],
    supervisor: dict[str, Any],
    policy_evaluation: dict[str, Any] | None = None,
    policy_evaluation_id: str | None = None,
    status: str = "routed",
) -> dict[str, Any] | None:
    if not table_exists(conn, "agent_routing_runs"):
        return None
    now = utcnow_iso()
    row_id = new_id("aroute")
    execute(
        conn,
        """
        INSERT INTO agent_routing_runs (
            id, organization_id, bot_id, conversation_id, contact_id, message_id, routing_status,
            text_preview, intent_detected, intent_family, router_version, router_confidence,
            specialist_agent_key, specialist_agent_version, prompt_base_id, allowed_tools_json,
            risk_policy_json, success_metrics_json, route_reason_json, shared_memory_json,
            plan_json, supervisor_json, policy_profile_key, policy_profile_version, policy_evaluation_id, policy_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            organization_id,
            bot_id,
            conversation_id,
            contact_id,
            message_id,
            status,
            str(text or "")[:280],
            classification.get("intent"),
            route.get("intent_family"),
            route.get("router_version"),
            float(route.get("confidence") or 0),
            route.get("specialist_agent_key"),
            route.get("specialist_agent_version"),
            route.get("prompt_base_id"),
            to_json(route.get("allowed_tools") or []),
            to_json(route.get("risk_policy") or {}),
            to_json(route.get("success_metrics") or []),
            to_json(route.get("route_reason") or []),
            to_json(shared_memory),
            to_json(execution_plan),
            to_json(supervisor),
            (policy_evaluation or {}).get("policy_profile_key"),
            (policy_evaluation or {}).get("policy_profile_version"),
            policy_evaluation_id,
            to_json(policy_evaluation or build_policy_route_summary(route)),
            now,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM agent_routing_runs WHERE id = ?", (row_id,))


def record_specialist_exposure(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    conversation_id: str | None,
    contact_id: str | None,
    message_id: str | None,
    route: dict[str, Any],
    flow_id: str | None = None,
    prompt_run_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    policy_evaluation: dict[str, Any] | None = None,
    policy_evaluation_id: str | None = None,
) -> dict[str, Any] | None:
    if not table_exists(conn, "outcome_exposures"):
        return None
    now = utcnow_iso()
    row_id = new_id("outcome_exposure")
    execute(
        conn,
        """
        INSERT INTO outcome_exposures (
            id, organization_id, bot_id, conversation_id, contact_id, lead_id, appointment_id, payment_id,
            message_id, source_type, channel, prompt_run_id, prompt_version_id, flow_id, flow_version_id,
            template_id, template_version_id, routing_rule_id, decision_path_id, timing_policy_id,
            tone_policy_id, nba_policy_id, escalation_policy_id, playbook_id, playbook_version_id,
            handoff_id, handoff_kind, operator_user_id, assigned_variant, vertical, funnel_stage,
            metadata_json, sent_at, created_at, specialist_agent_key, specialist_agent_version,
            specialist_prompt_id, intent_family, agent_routing_run_id, policy_profile_key, policy_profile_version, policy_evaluation_id
        ) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            organization_id,
            bot_id,
            conversation_id,
            contact_id,
            message_id,
            "specialist_route",
            "whatsapp",
            prompt_run_id,
            route.get("prompt_base_id"),
            flow_id or route.get("specialist_agent_key"),
            route.get("specialist_agent_version"),
            (metadata or {}).get("assigned_variant"),
            None,
            route.get("funnel_stage"),
            to_json({
                **(metadata or {}),
                "router_version": route.get("router_version"),
                "route_reason": route.get("route_reason") or [],
                "specialist": route.get("specialist_agent_key"),
                "policy_profile_key": (policy_evaluation or {}).get("policy_profile_key"),
                "policy_profile_version": (policy_evaluation or {}).get("policy_profile_version"),
            }),
            now,
            now,
            route.get("specialist_agent_key"),
            route.get("specialist_agent_version"),
            route.get("prompt_base_id"),
            route.get("intent_family"),
            (metadata or {}).get("agent_routing_run_id"),
            (policy_evaluation or {}).get("policy_profile_key"),
            (policy_evaluation or {}).get("policy_profile_version"),
            policy_evaluation_id,
        ),
    )
    return fetch_one(conn, "SELECT * FROM outcome_exposures WHERE id = ?", (row_id,))


__all__ = [
    "SPECIALIST_AGENTS",
    "route_intent_to_specialist",
    "build_shared_memory_context",
    "apply_specialist_plan",
    "supervise_specialist_route",
    "apply_supervisor_decision",
    "persist_agent_route_run",
    "record_specialist_exposure",
]
