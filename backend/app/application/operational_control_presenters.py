from __future__ import annotations

from typing import Any

from ..utils import from_json


def serialize_command(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "organization_id": row.get("organization_id"),
        "bot_id": row.get("bot_id"),
        "source_channel": row.get("source_channel"),
        "actor_user_id": row.get("actor_user_id"),
        "actor_phone_e164": row.get("actor_phone_e164"),
        "detected_intent": row.get("detected_intent"),
        "status": row.get("status"),
        "risk_level": row.get("risk_level"),
        "requires_confirmation": bool(row.get("requires_confirmation")),
        "confirmation_code": row.get("confirmation_code"),
        "approved_by_user_id": row.get("approved_by_user_id"),
        "approval_note": row.get("approval_note"),
        "parsed_entities": from_json(row.get("parsed_entities_json"), {}),
        "resolved_scope": from_json(row.get("resolved_scope_json"), {}),
        "result": from_json(row.get("result_json"), {}),
        "error": from_json(row.get("error_json"), {}),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "scheduled_for": row.get("scheduled_for"),
        "executed_at": row.get("executed_at"),
        "undoable_until": row.get("undoable_until"),
    }


def serialize_authorized_number(row: dict[str, Any], *, scope_summary: str) -> dict[str, Any]:
    return {
        "id": row["id"],
        "organization_id": row.get("organization_id"),
        "bot_id": row.get("bot_id"),
        "phone_e164": row.get("phone_e164"),
        "role": row.get("role"),
        "allowed_intents": from_json(row.get("allowed_intents_json"), []),
        "scope": from_json(row.get("scope_json"), {}),
        "status": row.get("status"),
        "verified_at": row.get("verified_at"),
        "last_used_at": row.get("last_used_at"),
        "updated_at": row.get("updated_at"),
        "scope_summary": scope_summary,
    }


def serialize_scheduled_action(row: dict[str, Any]) -> dict[str, Any]:
    return {"id": row["id"], "action_type": row.get("action_type"), "execute_at": row.get("execute_at"), "status": row.get("status"), "payload": from_json(row.get("payload_json"), {})}


def serialize_appointment(row: dict[str, Any]) -> dict[str, Any]:
    return {"id": row["id"], "scheduled_for": row.get("scheduled_for"), "status": row.get("status"), "conversation_id": row.get("conversation_id"), "contact_id": row.get("contact_id")}


def serialize_override(row: dict[str, Any]) -> dict[str, Any]:
    return {"id": row["id"], "override_type": row.get("override_type"), "start_at": row.get("start_at"), "end_at": row.get("end_at"), "reason": row.get("reason"), "scope": from_json(row.get("scope_json"), {}), "status": row.get("status")}


def serialize_alert(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "severity": row.get("severity"),
        "alert_type": row.get("alert_type"),
        "title": row.get("title"),
        "body": row.get("body"),
        "status": row.get("status"),
        "details": from_json(row.get("details_json"), {}),
        "created_at": row.get("created_at"),
        "command_id": row.get("command_id"),
    }
