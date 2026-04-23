from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from fastapi import HTTPException

from ...contracts import ok
from ...db import execute, fetch_all, fetch_one
from ...repositories import create_audit_log, get_bot
from ...security import ensure_bot_access, ensure_org_access
from ...utils import from_json, new_id, parse_iso, to_json, utcnow, utcnow_iso
from ..outcomes_policy import guardrail_state, recommendation
from ..outcomes_presenters import serialize_attribution_row, serialize_decision, serialize_event, serialize_exposure, serialize_scorecard
from ..support import require_permission
from ..uow import UnitOfWork


OUTCOME_BASE_SCORES: dict[str, float] = {
    "appointment_scheduled": 8.0,
    "appointment_confirmed": 10.0,
    "payment_started": 9.0,
    "payment_completed": 18.0,
    "appointment_attended": 14.0,
    "attended": 14.0,
    "no_show": -12.0,
    "appointment_no_show": -12.0,
    "reactivated": 11.0,
    "sale_closed": 25.0,
    "human_handoff_resolved": 6.0,
    "appointment_rescheduled": 5.0,
    "lead_stage_progressed": 7.0,
    "receipt_sent": 2.0,
}

POSITIVE_OUTCOMES = {
    "appointment_scheduled",
    "appointment_confirmed",
    "payment_started",
    "payment_completed",
    "appointment_attended",
    "attended",
    "reactivated",
    "sale_closed",
    "human_handoff_resolved",
    "appointment_rescheduled",
    "lead_stage_progressed",
    "receipt_sent",
}

NEGATIVE_OUTCOMES = {"no_show", "appointment_no_show", "lost", "refund", "handoff_failed"}

ENTITY_FIELDS: list[tuple[str, str]] = [
    ("prompt_run", "prompt_run_id"),
    ("prompt_version", "prompt_version_id"),
    ("flow", "flow_id"),
    ("flow_version", "flow_version_id"),
    ("template", "template_id"),
    ("template_version", "template_version_id"),
    ("routing_rule", "routing_rule_id"),
    ("decision_path", "decision_path_id"),
    ("timing_policy", "timing_policy_id"),
    ("tone_policy", "tone_policy_id"),
    ("nba_policy", "nba_policy_id"),
    ("escalation_policy", "escalation_policy_id"),
    ("playbook", "playbook_id"),
    ("playbook_version", "playbook_version_id"),
    ("handoff", "handoff_id"),
    ("specialist_agent", "specialist_agent_key"),
    ("specialist_prompt", "specialist_prompt_id"),
    ("agent_routing_run", "agent_routing_run_id"),
    ("policy_profile", "policy_profile_key"),
    ("operator_user", "operator_user_id"),
    ("response_variant", "assigned_variant"),
    ("channel", "channel"),
    ("source_type", "source_type"),
]

WINDOWS_TO_DAYS = {"7d": 7, "28d": 28, "90d": 90}



def handle(service, uow: UnitOfWork, *, decision_id: str, payload, user: dict) -> dict[str, Any]:
    row = fetch_one(uow.conn, "SELECT * FROM outcome_optimization_decisions WHERE id = ?", (decision_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Decision not found")
    ensure_org_access(user, row["organization_id"])
    require_permission(user, row["organization_id"], "operations.read")
    now = utcnow_iso()
    rollback_id = new_id("outcome_decision")
    execute(
        uow.conn,
        "UPDATE outcome_optimization_decisions SET status = 'rolled_back' WHERE id = ?",
        (decision_id,),
    )
    execute(
        uow.conn,
        """
        INSERT INTO outcome_optimization_decisions (
            id, organization_id, bot_id, entity_type, entity_id, action, decision_source, reason_code,
            status, previous_state_json, new_state_json, evidence_snapshot_json, rollback_of_decision_id,
            created_by, created_at, applied_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'rollback', 'rollback_requested', 'applied', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rollback_id,
            row["organization_id"],
            row.get("bot_id"),
            row["entity_type"],
            row["entity_id"],
            f"rollback:{row['action']}",
            row.get("new_state_json") or "{}",
            row.get("previous_state_json") or "{}",
            to_json({"rollback_note": payload.note or ""}),
            decision_id,
            user["id"],
            now,
            now,
        ),
    )
    create_audit_log(
        uow.conn,
        organization_id=row["organization_id"],
        actor_user_id=user["id"],
        actor_type="user",
        entity_type="outcome_decision",
        entity_id=rollback_id,
        action="outcomes.decision.rolled_back",
        metadata={"rollback_of": decision_id},
    )
    uow.commit()
    data = fetch_one(uow.conn, "SELECT * FROM outcome_optimization_decisions WHERE id = ?", (rollback_id,))
    return ok(service._serialize_decision(data))
