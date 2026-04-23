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
    bot = get_bot(uow.conn, payload.bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if bot["organization_id"] != payload.organization_id:
        raise HTTPException(status_code=403, detail="Bot does not belong to organization")
    ensure_bot_access(user, bot)

    now = utcnow_iso()
    row_id = new_id("outcome_exposure")
    execute(
        uow.conn,
        """
        INSERT INTO outcome_exposures (
            id, organization_id, bot_id, conversation_id, contact_id, lead_id, appointment_id, payment_id,
            message_id, source_type, channel, prompt_run_id, prompt_version_id, flow_id, flow_version_id,
            template_id, template_version_id, routing_rule_id, decision_path_id, timing_policy_id,
            tone_policy_id, nba_policy_id, escalation_policy_id, playbook_id, playbook_version_id,
            handoff_id, handoff_kind, specialist_agent_key, specialist_agent_version, specialist_prompt_id,
            intent_family, agent_routing_run_id, policy_profile_key, policy_profile_version, policy_evaluation_id, operator_user_id, assigned_variant, vertical, funnel_stage,
            metadata_json, sent_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            payload.message_id,
            payload.source_type,
            payload.channel,
            payload.prompt_run_id,
            payload.prompt_version_id,
            payload.flow_id,
            payload.flow_version_id,
            payload.template_id,
            payload.template_version_id,
            payload.routing_rule_id,
            payload.decision_path_id,
            payload.timing_policy_id,
            payload.tone_policy_id,
            payload.nba_policy_id,
            payload.escalation_policy_id,
            payload.playbook_id,
            payload.playbook_version_id,
            payload.handoff_id,
            payload.handoff_kind,
            payload.specialist_agent_key,
            payload.specialist_agent_version,
            payload.specialist_prompt_id,
            payload.intent_family,
            payload.agent_routing_run_id,
            payload.policy_profile_key,
            payload.policy_profile_version,
            payload.policy_evaluation_id,
            payload.operator_user_id,
            payload.assigned_variant,
            payload.vertical or bot.get("vertical"),
            payload.funnel_stage,
            to_json(payload.metadata),
            payload.sent_at or now,
            now,
        ),
    )
    create_audit_log(
        uow.conn,
        organization_id=payload.organization_id,
        actor_user_id=user["id"],
        actor_type="user",
        entity_type="outcome_exposure",
        entity_id=row_id,
        action="outcomes.exposure.recorded",
        metadata={
            "bot_id": payload.bot_id,
            "prompt_run_id": payload.prompt_run_id,
            "prompt_version_id": payload.prompt_version_id,
            "flow_id": payload.flow_id,
            "template_id": payload.template_id,
            "specialist_agent_key": payload.specialist_agent_key,
            "agent_routing_run_id": payload.agent_routing_run_id,
            "policy_profile_key": payload.policy_profile_key,
            "funnel_stage": payload.funnel_stage,
        },
    )
    uow.commit()
    return ok(service._serialize_exposure(fetch_one(uow.conn, "SELECT * FROM outcome_exposures WHERE id = ?", (row_id,))))
