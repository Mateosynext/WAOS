from __future__ import annotations

from typing import Any

from .base import ConnectionLike
from ..db import execute, fetch_all, fetch_one, table_exists
from ..utils import new_id, to_json, utcnow_iso


def load_shared_memory_rows(
    conn: ConnectionLike,
    *,
    conversation_id: str | None,
    contact_id: str | None,
) -> dict[str, list[dict[str, Any]]]:
    if not (conversation_id or contact_id):
        return {"appointments": [], "payments": [], "leads": [], "outcomes": [], "tool_executions": []}
    return {
        "appointments": fetch_all(conn, "SELECT id, scheduled_for, status, provider, updated_at FROM appointments WHERE conversation_id = ? OR contact_id = ? ORDER BY updated_at DESC LIMIT 5", (conversation_id, contact_id)),
        "payments": fetch_all(conn, "SELECT id, amount, currency, status, payment_link_url, updated_at FROM commerce_payments WHERE conversation_id = ? OR contact_id = ? ORDER BY updated_at DESC LIMIT 5", (conversation_id, contact_id)),
        "leads": fetch_all(conn, "SELECT id, stage, estimated_amount, next_action, close_probability, updated_at FROM crm_leads WHERE conversation_id = ? OR contact_id = ? ORDER BY updated_at DESC LIMIT 3", (conversation_id, contact_id)),
        "outcomes": fetch_all(conn, "SELECT id, event_name, event_category, event_timestamp, value_number FROM outcome_events WHERE conversation_id = ? OR contact_id = ? ORDER BY event_timestamp DESC LIMIT 5", (conversation_id, contact_id)) if table_exists(conn, "outcome_events") else [],
        "tool_executions": fetch_all(conn, "SELECT id, action, status, adapter_key, provider, completed_at, created_at FROM tool_execution_runs WHERE conversation_id = ? OR contact_id = ? ORDER BY COALESCE(completed_at, created_at) DESC LIMIT 5", (conversation_id, contact_id)) if table_exists(conn, "tool_execution_runs") else [],
    }


def insert_agent_routing_run(conn: ConnectionLike, payload: dict[str, Any]) -> dict[str, Any] | None:
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
            payload["organization_id"], payload["bot_id"], payload.get("conversation_id"), payload.get("contact_id"), payload.get("message_id"), payload.get("status") or "routed",
            str(payload.get("text") or "")[:280], payload.get("intent_detected"), payload.get("intent_family"), payload.get("router_version"), float(payload.get("router_confidence") or 0),
            payload.get("specialist_agent_key"), payload.get("specialist_agent_version"), payload.get("prompt_base_id"), to_json(payload.get("allowed_tools") or []),
            to_json(payload.get("risk_policy") or {}), to_json(payload.get("success_metrics") or []), to_json(payload.get("route_reason") or []), to_json(payload.get("shared_memory") or {}),
            to_json(payload.get("execution_plan") or {}), to_json(payload.get("supervisor") or {}), payload.get("policy_profile_key"), payload.get("policy_profile_version"), payload.get("policy_evaluation_id"), to_json(payload.get("policy") or {}), now, now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM agent_routing_runs WHERE id = ?", (row_id,))


def _resolve_exposure_context(conn: ConnectionLike, payload: dict[str, Any]) -> dict[str, Any]:
    message_row = None
    if payload.get("message_id"):
        message_row = fetch_one(conn, "SELECT id, created_at, conversation_id, contact_id FROM messages WHERE id = ?", (payload.get("message_id"),))
    if not message_row and payload.get("conversation_id"):
        message_row = fetch_one(
            conn,
            "SELECT id, created_at, conversation_id, contact_id FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1",
            (payload.get("conversation_id"),),
        )
    if not message_row and payload.get("contact_id"):
        message_row = fetch_one(
            conn,
            "SELECT id, created_at, conversation_id, contact_id FROM messages WHERE contact_id = ? ORDER BY created_at DESC LIMIT 1",
            (payload.get("contact_id"),),
        )

    conversation_row = None
    if payload.get("conversation_id"):
        conversation_row = fetch_one(conn, "SELECT id, last_message_at, contact_id FROM conversations WHERE id = ?", (payload.get("conversation_id"),))

    payment_row = None
    if payload.get("conversation_id"):
        payment_row = fetch_one(
            conn,
            "SELECT id FROM commerce_payments WHERE conversation_id = ? ORDER BY updated_at DESC, created_at DESC LIMIT 1",
            (payload.get("conversation_id"),),
        )
    if not payment_row and payload.get("contact_id"):
        payment_row = fetch_one(
            conn,
            "SELECT id FROM commerce_payments WHERE contact_id = ? ORDER BY updated_at DESC, created_at DESC LIMIT 1",
            (payload.get("contact_id"),),
        )

    sent_at = (
        (message_row or {}).get("created_at")
        or (conversation_row or {}).get("last_message_at")
        or payload.get("sent_at")
        or utcnow_iso()
    )
    return {
        "message_id": (message_row or {}).get("id") or payload.get("message_id"),
        "conversation_id": payload.get("conversation_id") or (message_row or {}).get("conversation_id"),
        "contact_id": payload.get("contact_id") or (message_row or {}).get("contact_id") or (conversation_row or {}).get("contact_id"),
        "payment_id": payload.get("payment_id") or (payment_row or {}).get("id"),
        "sent_at": sent_at,
    }


def insert_specialist_exposure(conn: ConnectionLike, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not table_exists(conn, "outcome_exposures"):
        return None
    now = utcnow_iso()
    context = _resolve_exposure_context(conn, payload)
    row_id = new_id("outcome_exposure")
    execute(
        conn,
        """
        INSERT INTO outcome_exposures (
            id, organization_id, bot_id, conversation_id, contact_id, lead_id, appointment_id, payment_id,
            message_id, source_type, channel, prompt_run_id, prompt_version_id, flow_id, flow_version_id,
            template_id, template_version_id, routing_rule_id, decision_path_id, timing_policy_id,
            tone_policy_id, nba_policy_id, escalation_policy_id, playbook_id, playbook_version_id,
            handoff_id, handoff_kind, specialist_agent_key, specialist_agent_version, specialist_prompt_id,
            intent_family, agent_routing_run_id, policy_profile_key, policy_profile_version, policy_evaluation_id,
            operator_user_id, assigned_variant, vertical, funnel_stage, metadata_json, sent_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            payload["organization_id"],
            payload["bot_id"],
            context.get("conversation_id"),
            context.get("contact_id"),
            None,
            None,
            context.get("payment_id"),
            context.get("message_id"),
            "specialist_route",
            payload.get("channel") or "whatsapp",
            payload.get("prompt_run_id"),
            payload.get("prompt_base_id"),
            payload.get("flow_id"),
            payload.get("flow_version_id"),
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            payload.get("specialist_agent_key"),
            payload.get("specialist_agent_version"),
            payload.get("prompt_base_id"),
            payload.get("intent_family"),
            payload.get("agent_routing_run_id"),
            payload.get("policy_profile_key"),
            payload.get("policy_profile_version"),
            payload.get("policy_evaluation_id"),
            None,
            payload.get("assigned_variant"),
            None,
            payload.get("funnel_stage"),
            to_json(payload.get("metadata") or {}),
            context.get("sent_at"),
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM outcome_exposures WHERE id = ?", (row_id,))
