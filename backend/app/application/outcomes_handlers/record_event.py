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



def handle(service, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
    ensure_org_access(user, payload.organization_id)
    require_permission(user, payload.organization_id, "conversation.manage")
    if payload.bot_id:
        bot = get_bot(uow.conn, payload.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if bot["organization_id"] != payload.organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)

    dedupe_key = payload.dedupe_key or service._build_dedupe_key(payload.model_dump())
    existing = fetch_one(
        uow.conn,
        "SELECT * FROM outcome_events WHERE organization_id = ? AND dedupe_key = ?",
        (payload.organization_id, dedupe_key),
    )
    if existing:
        return ok({
            "event": service._serialize_event(existing),
            "attribution": service._list_attribution_rows(uow.conn, organization_id=payload.organization_id, outcome_event_id=existing["id"], limit=200),
            "deduped": True,
        })

    now = utcnow_iso()
    row_id = new_id("outcome_event")
    execute(
        uow.conn,
        """
        INSERT INTO outcome_events (
            id, organization_id, bot_id, conversation_id, contact_id, lead_id, appointment_id, payment_id,
            review_id, event_name, event_category, event_timestamp, source_system, external_event_id,
            status, value_number, value_text, value_json, operator_user_id, vertical, funnel_stage,
            dedupe_key, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            payload.organization_id,
            payload.bot_id,
            payload.conversation_id,
            payload.contact_id,
            payload.lead_id,
            payload.appointment_id,
            payload.payment_id,
            payload.review_id,
            payload.event_name,
            payload.event_category,
            payload.event_timestamp or now,
            payload.source_system,
            payload.external_event_id,
            payload.status,
            payload.value_number,
            payload.value_text,
            to_json(payload.value),
            payload.operator_user_id,
            payload.vertical,
            payload.funnel_stage,
            dedupe_key,
            now,
        ),
    )
    event_row = fetch_one(uow.conn, "SELECT * FROM outcome_events WHERE id = ?", (row_id,))
    attribution_summary = service._materialize_attribution_for_event(
        uow.conn,
        event_row=event_row,
        attribution_window_hours=168,
    )
    service._recompute_scorecards(
        uow.conn,
        organization_id=payload.organization_id,
        bot_id=payload.bot_id,
        windows=["7d", "28d"],
        attribution_window_hours=168,
    )
    create_audit_log(
        uow.conn,
        organization_id=payload.organization_id,
        actor_user_id=user["id"],
        actor_type="user",
        entity_type="outcome_event",
        entity_id=row_id,
        action="outcomes.event.recorded",
        metadata={
            "event_name": payload.event_name,
            "event_category": payload.event_category,
            "source_system": payload.source_system,
            "dedupe_key": dedupe_key,
        },
    )
    uow.commit()
    return ok({
        "event": service._serialize_event(event_row),
        "attribution": attribution_summary,
        "deduped": False,
    })
