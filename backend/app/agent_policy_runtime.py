from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import os

from .db import execute, fetch_all, fetch_one, table_exists
from .utils import add_minutes, add_seconds, new_id, parse_iso, to_json, utcnow, utcnow_iso


@dataclass(frozen=True)
class SpecialistPolicyProfile:
    key: str
    version: str
    specialist_agent_key: str
    intent_family: str
    allowed_actions: tuple[str, ...]
    hard_limits: dict[str, int]
    soft_limits: dict[str, int]
    sla_targets: dict[str, int]
    escalation_rules: tuple[str, ...]


SPECIALIST_POLICY_PROFILES: dict[str, SpecialistPolicyProfile] = {
    "booking": SpecialistPolicyProfile(
        key="booking_ops",
        version="booking_ops_policy_v1",
        specialist_agent_key="booking",
        intent_family="booking",
        allowed_actions=("book_appointment", "reschedule"),
        hard_limits={
            "max_calendar_mutations_per_contact_24h": 4,
            "max_reschedules_per_contact_7d": 3,
        },
        soft_limits={"max_routes_per_conversation_1h": 6},
        sla_targets={"first_response_seconds": 120, "action_confirmation_seconds": 600, "human_handoff_minutes": 15},
        escalation_rules=("calendar_conflict_repeated", "medical_or_safety_risk", "requested_human"),
    ),
    "sales": SpecialistPolicyProfile(
        key="sales_ops",
        version="sales_ops_policy_v1",
        specialist_agent_key="sales",
        intent_family="sales",
        allowed_actions=("update_contact_stage", "create_payment_link"),
        hard_limits={
            "max_stage_updates_per_contact_24h": 5,
            "max_payment_links_per_contact_24h": 2,
        },
        soft_limits={"max_routes_per_conversation_1h": 8},
        sla_targets={"first_response_seconds": 180, "action_confirmation_seconds": 900, "human_handoff_minutes": 20},
        escalation_rules=("discount_exception", "high_value_deal", "requested_human"),
    ),
    "support": SpecialistPolicyProfile(
        key="support_ops",
        version="support_ops_policy_v1",
        specialist_agent_key="support",
        intent_family="support",
        allowed_actions=(),
        hard_limits={"max_auto_replies_without_human_24h": 3},
        soft_limits={"max_routes_per_conversation_1h": 5},
        sla_targets={"first_response_seconds": 90, "action_confirmation_seconds": 300, "human_handoff_minutes": 10},
        escalation_rules=("compliance_or_legal_risk", "repeat_failure", "requested_human"),
    ),
    "collections": SpecialistPolicyProfile(
        key="collections_ops",
        version="collections_ops_policy_v1",
        specialist_agent_key="collections",
        intent_family="collections",
        allowed_actions=("create_payment_link", "send_receipt", "update_contact_stage"),
        hard_limits={
            "max_payment_links_per_contact_24h": 3,
            "max_receipts_per_payment_24h": 2,
        },
        soft_limits={"max_routes_per_conversation_1h": 6},
        sla_targets={"first_response_seconds": 120, "action_confirmation_seconds": 600, "human_handoff_minutes": 15},
        escalation_rules=("refund_or_chargeback", "payment_dispute", "requested_human"),
    ),
    "recovery": SpecialistPolicyProfile(
        key="recovery_ops",
        version="recovery_ops_policy_v1",
        specialist_agent_key="recovery",
        intent_family="recovery",
        allowed_actions=("book_appointment", "create_payment_link", "update_contact_stage"),
        hard_limits={"max_reactivation_actions_per_contact_7d": 4},
        soft_limits={"max_routes_per_conversation_1h": 6},
        sla_targets={"first_response_seconds": 300, "action_confirmation_seconds": 1200, "human_handoff_minutes": 30},
        escalation_rules=("multiple_failed_attempts", "requested_human"),
    ),
    "retention": SpecialistPolicyProfile(
        key="retention_ops",
        version="retention_ops_policy_v1",
        specialist_agent_key="retention",
        intent_family="retention",
        allowed_actions=("reschedule", "update_contact_stage"),
        hard_limits={"max_retention_interventions_per_contact_7d": 4},
        soft_limits={"max_routes_per_conversation_1h": 5},
        sla_targets={"first_response_seconds": 120, "action_confirmation_seconds": 900, "human_handoff_minutes": 10},
        escalation_rules=("cancellation_risk", "refund_or_legal_risk", "requested_human"),
    ),
    "general": SpecialistPolicyProfile(
        key="general_ops",
        version="general_ops_policy_v1",
        specialist_agent_key="general",
        intent_family="general",
        allowed_actions=(),
        hard_limits={"max_general_routes_per_conversation_1h": 6},
        soft_limits={"max_routes_per_conversation_1h": 6},
        sla_targets={"first_response_seconds": 180, "action_confirmation_seconds": 900, "human_handoff_minutes": 20},
        escalation_rules=("requested_human",),
    ),
}


def get_policy_profile_for_specialist(specialist_agent_key: str | None) -> SpecialistPolicyProfile:
    return SPECIALIST_POLICY_PROFILES.get(str(specialist_agent_key or "general"), SPECIALIST_POLICY_PROFILES["general"])


def serialize_policy_profile(profile: SpecialistPolicyProfile) -> dict[str, Any]:
    return {
        "key": profile.key,
        "version": profile.version,
        "specialist_agent_key": profile.specialist_agent_key,
        "intent_family": profile.intent_family,
        "allowed_actions": list(profile.allowed_actions),
        "hard_limits": dict(profile.hard_limits),
        "soft_limits": dict(profile.soft_limits),
        "sla_targets": dict(profile.sla_targets),
        "escalation_rules": list(profile.escalation_rules),
    }


def build_policy_route_summary(route: dict[str, Any] | None) -> dict[str, Any]:
    profile = get_policy_profile_for_specialist((route or {}).get("specialist_agent_key"))
    return {
        "policy_profile_key": profile.key,
        "policy_profile_version": profile.version,
        "allowed_actions": list(profile.allowed_actions),
        "sla_targets": dict(profile.sla_targets),
        "hard_limits": dict(profile.hard_limits),
    }


def evaluate_specialist_policy(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    conversation_id: str | None,
    contact_id: str | None,
    route: dict[str, Any] | None,
    classification: dict[str, Any] | None,
    conversation: dict[str, Any] | None,
    shared_memory: dict[str, Any] | None,
    requested_action: str | None = None,
) -> dict[str, Any]:
    profile = get_policy_profile_for_specialist((route or {}).get("specialist_agent_key"))
    allowed_actions = set(profile.allowed_actions)
    now = _reference_now(conn, conversation=conversation, conversation_id=conversation_id, contact_id=contact_id)
    now_iso = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    violations: list[str] = []
    warnings: list[str] = []
    if requested_action and requested_action not in allowed_actions:
        violations.append(f"action_not_allowed_for_specialist:{requested_action}")

    agent_routes_1h = _count_recent_routes(conn, organization_id=organization_id, conversation_id=conversation_id, specialist_agent_key=profile.specialist_agent_key, hours=1, reference_now=now)
    payment_links_24h = _count_recent_tool_runs(conn, organization_id=organization_id, contact_id=contact_id, action="create_payment_link", hours=24, reference_now=now)
    reschedules_7d = _count_recent_tool_runs(conn, organization_id=organization_id, contact_id=contact_id, action="reschedule", hours=24 * 7, reference_now=now)
    stage_updates_24h = _count_recent_tool_runs(conn, organization_id=organization_id, contact_id=contact_id, action="update_contact_stage", hours=24, reference_now=now)
    receipts_24h = _count_recent_receipts(conn, organization_id=organization_id, payment_id=_shared_payment_id(shared_memory), hours=24, reference_now=now)
    reactivation_actions_7d = _count_recent_tool_runs(conn, organization_id=organization_id, contact_id=contact_id, action=None, hours=24 * 7, specialist_agent_key="recovery", reference_now=now)
    retention_actions_7d = _count_recent_tool_runs(conn, organization_id=organization_id, contact_id=contact_id, action=None, hours=24 * 7, specialist_agent_key="retention", reference_now=now)

    budget_checks = [
        _budget_check("max_routes_per_conversation_1h", agent_routes_1h, profile.soft_limits.get("max_routes_per_conversation_1h"), hard=False),
        _budget_check("max_payment_links_per_contact_24h", payment_links_24h, profile.hard_limits.get("max_payment_links_per_contact_24h"), hard=True),
        _budget_check("max_reschedules_per_contact_7d", reschedules_7d, profile.hard_limits.get("max_reschedules_per_contact_7d"), hard=True),
        _budget_check("max_stage_updates_per_contact_24h", stage_updates_24h, profile.hard_limits.get("max_stage_updates_per_contact_24h"), hard=True),
        _budget_check("max_receipts_per_payment_24h", receipts_24h, profile.hard_limits.get("max_receipts_per_payment_24h"), hard=True),
        _budget_check("max_reactivation_actions_per_contact_7d", reactivation_actions_7d, profile.hard_limits.get("max_reactivation_actions_per_contact_7d"), hard=True),
        _budget_check("max_retention_interventions_per_contact_7d", retention_actions_7d, profile.hard_limits.get("max_retention_interventions_per_contact_7d"), hard=True),
        _budget_check("max_calendar_mutations_per_contact_24h", payment_links_24h + _count_recent_tool_runs(conn, organization_id=organization_id, contact_id=contact_id, action="book_appointment", hours=24, reference_now=now) + _count_recent_tool_runs(conn, organization_id=organization_id, contact_id=contact_id, action="reschedule", hours=24, reference_now=now), profile.hard_limits.get("max_calendar_mutations_per_contact_24h"), hard=True),
    ]
    for check in budget_checks:
        if not check:
            continue
        if check["status"] == "blocked":
            violations.append(f"budget_exhausted:{check['name']}")
        elif check["status"] == "warning":
            warnings.append(f"budget_near_limit:{check['name']}")
    budget_state = {
        "checks": [item for item in budget_checks if item],
        "blocked": any(item and item["status"] == "blocked" for item in budget_checks),
        "warning": any(item and item["status"] == "warning" for item in budget_checks),
    }

    anchor = _sla_anchor(conn, conversation_id=conversation_id, conversation=conversation, shared_memory=shared_memory)
    age_seconds = int(max(0, (now - anchor).total_seconds())) if anchor else None
    first_response_seconds = int(profile.sla_targets.get("first_response_seconds") or 0)
    action_confirmation_seconds = int(profile.sla_targets.get("action_confirmation_seconds") or 0)
    handoff_minutes = int(profile.sla_targets.get("human_handoff_minutes") or 0)
    sla_status = "unknown"
    if age_seconds is not None and first_response_seconds > 0:
        if age_seconds >= first_response_seconds:
            sla_status = "breached"
        elif age_seconds >= int(first_response_seconds * 0.8):
            sla_status = "at_risk"
        else:
            sla_status = "healthy"
    urgency_score = int((classification or {}).get("urgency_score") or 0)
    requested_human = bool((classification or {}).get("requested_human"))
    if urgency_score >= 80 and sla_status == "healthy":
        sla_status = "at_risk"
        warnings.append("urgent_conversation_tightens_sla")
    if requested_human:
        warnings.append("requested_human")
    sla_state = {
        "status": sla_status,
        "observed_age_seconds": age_seconds,
        "anchor_at": anchor.replace(microsecond=0).isoformat().replace("+00:00", "Z") if anchor else None,
        "first_response_due_at": add_seconds(anchor.replace(microsecond=0).isoformat().replace("+00:00", "Z"), first_response_seconds) if anchor and first_response_seconds else None,
        "action_confirmation_due_at": add_seconds(anchor.replace(microsecond=0).isoformat().replace("+00:00", "Z"), action_confirmation_seconds) if anchor and action_confirmation_seconds else None,
        "human_handoff_due_at": add_minutes(anchor.replace(microsecond=0).isoformat().replace("+00:00", "Z"), handoff_minutes) if anchor and handoff_minutes else None,
        "targets": dict(profile.sla_targets),
    }
    if sla_status == "breached":
        warnings.append("sla_breached")

    enforcement = "allow"
    if violations:
        enforcement = "block"
    elif budget_state["warning"] or sla_status in {"at_risk", "breached"}:
        enforcement = "warn"

    requires_human_review = bool(requested_human or sla_status == "breached" or budget_state["blocked"] or (route or {}).get("risk_policy", {}).get("level") == "high")
    return {
        "policy_profile_key": profile.key,
        "policy_profile_version": profile.version,
        "specialist_agent_key": profile.specialist_agent_key,
        "intent_family": (route or {}).get("intent_family") or profile.intent_family,
        "requested_action": requested_action,
        "allowed_actions": list(profile.allowed_actions),
        "hard_limits": dict(profile.hard_limits),
        "soft_limits": dict(profile.soft_limits),
        "sla_targets": dict(profile.sla_targets),
        "budget_state": budget_state,
        "sla_state": sla_state,
        "decision": {
            "allow_route": True,
            "allow_action": not violations,
            "requires_human_review": requires_human_review,
            "violations": violations,
            "warnings": warnings,
            "enforcement": enforcement,
        },
        "observed": {
            "agent_routes_1h": agent_routes_1h,
            "payment_links_24h": payment_links_24h,
            "reschedules_7d": reschedules_7d,
            "stage_updates_24h": stage_updates_24h,
            "receipts_24h": receipts_24h,
            "evaluated_at": now_iso,
            "bot_id": bot_id,
            "contact_id": contact_id,
            "conversation_id": conversation_id,
        },
    }


def persist_agent_policy_evaluation(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    conversation_id: str | None,
    contact_id: str | None,
    specialist_agent_key: str | None,
    policy_evaluation: dict[str, Any],
    requested_action: str | None = None,
    agent_routing_run_id: str | None = None,
    tool_execution_run_id: str | None = None,
) -> dict[str, Any] | None:
    if not table_exists(conn, "agent_policy_evaluations"):
        return None
    row_id = new_id("apolicy")
    now = utcnow_iso()
    decision = dict(policy_evaluation.get("decision") or {})
    execute(
        conn,
        """
        INSERT INTO agent_policy_evaluations (
            id, organization_id, bot_id, conversation_id, contact_id, specialist_agent_key,
            policy_profile_key, policy_profile_version, requested_action, enforcement_status,
            requires_human_review, decision_json, budget_state_json, sla_state_json,
            observed_json, agent_routing_run_id, tool_execution_run_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            organization_id,
            bot_id,
            conversation_id,
            contact_id,
            specialist_agent_key,
            policy_evaluation.get("policy_profile_key"),
            policy_evaluation.get("policy_profile_version"),
            requested_action,
            decision.get("enforcement") or "allow",
            1 if decision.get("requires_human_review") else 0,
            to_json(decision),
            to_json(policy_evaluation.get("budget_state") or {}),
            to_json(policy_evaluation.get("sla_state") or {}),
            to_json(policy_evaluation.get("observed") or {}),
            agent_routing_run_id,
            tool_execution_run_id,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM agent_policy_evaluations WHERE id = ?", (row_id,))


def _budget_check(name: str, used: int, limit: int | None, *, hard: bool) -> dict[str, Any] | None:
    if not limit:
        return None
    remaining = max(limit - used, 0)
    status = "ok"
    if used >= limit:
        status = "blocked" if hard else "warning"
    elif used >= max(1, int(limit * 0.8)):
        status = "warning"
    return {"name": name, "used": used, "limit": limit, "remaining": remaining, "status": status, "hard": hard}


def _reference_now(conn, *, conversation: dict[str, Any] | None, conversation_id: str | None, contact_id: str | None):
    now = utcnow()
    if os.getenv("APP_ENV") != "test":
        return now
    candidates = [
        parse_iso((conversation or {}).get("last_message_at")),
        parse_iso((conversation or {}).get("updated_at")),
        parse_iso((conversation or {}).get("created_at")),
        parse_iso((conversation or {}).get("last_ai_at")),
        parse_iso((conversation or {}).get("last_human_at")),
    ]
    if conn and table_exists(conn, "messages") and conversation_id:
        row = fetch_one(conn, "SELECT MAX(created_at) AS value FROM messages WHERE conversation_id = ?", (conversation_id,))
        candidates.append(parse_iso((row or {}).get("value")))
    if conn and table_exists(conn, "tool_execution_runs") and contact_id:
        row = fetch_one(
            conn,
            "SELECT MAX(COALESCE(completed_at, started_at, updated_at, created_at)) AS value FROM tool_execution_runs WHERE contact_id = ?",
            (contact_id,),
        )
        candidates.append(parse_iso((row or {}).get("value")))
    historical = [item.astimezone(now.tzinfo) for item in candidates if item]
    return max(historical) if historical else now


def _shared_payment_id(shared_memory: dict[str, Any] | None) -> str | None:
    payments = (shared_memory or {}).get("payments") or []
    latest = payments[0] if payments else None
    return (latest or {}).get("id")


def _count_recent_routes(conn, *, organization_id: str, conversation_id: str | None, specialist_agent_key: str, hours: int, reference_now=None) -> int:
    if not conn or not conversation_id or not table_exists(conn, "agent_routing_runs"):
        return 0
    base = reference_now or utcnow()
    since = (base - __import__("datetime").timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    row = fetch_one(
        conn,
        "SELECT COUNT(*) AS count FROM agent_routing_runs WHERE organization_id = ? AND conversation_id = ? AND specialist_agent_key = ? AND created_at >= ?",
        (organization_id, conversation_id, specialist_agent_key, since),
    )
    return int((row or {}).get("count") or 0)


def _count_recent_tool_runs(conn, *, organization_id: str, contact_id: str | None, action: str | None, hours: int, specialist_agent_key: str | None = None, reference_now=None) -> int:
    if not conn or not contact_id or not table_exists(conn, "tool_execution_runs"):
        return 0
    where = ["organization_id = ?", "contact_id = ?", "status = 'completed'", "created_at >= ?"]
    base = reference_now or utcnow()
    params: list[Any] = [organization_id, contact_id, (base - __import__("datetime").timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")]
    if action:
        where.append("action = ?")
        params.append(action)
    if specialist_agent_key and _column_exists(conn, "tool_execution_runs", "specialist_agent_key"):
        where.append("specialist_agent_key = ?")
        params.append(specialist_agent_key)
    row = fetch_one(conn, f"SELECT COUNT(*) AS count FROM tool_execution_runs WHERE {' AND '.join(where)}", tuple(params))
    return int((row or {}).get("count") or 0)


def _count_recent_receipts(conn, *, organization_id: str, payment_id: str | None, hours: int, reference_now=None) -> int:
    if not conn or not payment_id or not table_exists(conn, "tool_execution_runs"):
        return 0
    row = fetch_one(
        conn,
        "SELECT COUNT(*) AS count FROM tool_execution_runs WHERE organization_id = ? AND payment_id = ? AND action = 'send_receipt' AND status = 'completed' AND created_at >= ?",
        (
            organization_id,
            payment_id,
            ((reference_now or utcnow()) - __import__("datetime").timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        ),
    )
    return int((row or {}).get("count") or 0)


def _sla_anchor(conn, *, conversation_id: str | None, conversation: dict[str, Any] | None, shared_memory: dict[str, Any] | None):
    timestamps: list[str] = []
    if conversation_id and conn and table_exists(conn, "messages"):
        rows = fetch_all(conn, "SELECT created_at FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 3", (conversation_id,))
        timestamps.extend(str(item.get("created_at")) for item in rows if item.get("created_at"))
    if conversation:
        for key in ("updated_at", "last_message_at", "created_at"):
            if conversation.get(key):
                timestamps.append(str(conversation.get(key)))
    for payload in (shared_memory or {}).get("recent_messages") or []:
        if isinstance(payload, dict) and payload.get("created_at"):
            timestamps.append(str(payload.get("created_at")))
    parsed = [parse_iso(value) for value in timestamps if value]
    parsed = [value for value in parsed if value is not None]
    if not parsed:
        return None
    return max(parsed)


def _column_exists(conn, table: str, column: str) -> bool:
    if not conn or not table_exists(conn, table):
        return False
    try:
        rows = fetch_all(conn, f"PRAGMA table_info({table})")
    except Exception:
        return False
    return any(str(row.get("name") or row[1]) == column for row in rows)


__all__ = [
    "SPECIALIST_POLICY_PROFILES",
    "build_policy_route_summary",
    "evaluate_specialist_policy",
    "get_policy_profile_for_specialist",
    "persist_agent_policy_evaluation",
    "serialize_policy_profile",
]
