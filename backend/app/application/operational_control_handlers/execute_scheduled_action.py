from __future__ import annotations

import datetime as dt
import json
import os
import re
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from ...db import execute, fetch_all, fetch_one, table_exists
from ...repositories.audit import create_audit_log
from ...repositories.bots import get_bot
from ...repositories.conversations import create_message
from ...security import ensure_bot_access
from ...utils import add_minutes, new_id, parse_iso, to_json, utcnow, utcnow_iso
from ..operational_control_policy import needs_second_approval, requires_confirmation, risk_level
from ..operational_control_presenters import (
    serialize_alert,
    serialize_appointment,
    serialize_authorized_number,
    serialize_command,
    serialize_override,
    serialize_scheduled_action,
)
from ..support import require_permission



def handle(service, conn, *, action_id: str | None = None, command_id: str | None = None) -> dict:
    action = None
    if action_id:
        action = fetch_one(conn, "SELECT * FROM scheduled_operational_actions WHERE id = ?", (action_id,))
    elif command_id:
        action = fetch_one(conn, "SELECT * FROM scheduled_operational_actions WHERE command_id = ? AND status IN ('scheduled','queued','running') ORDER BY execute_at ASC LIMIT 1", (command_id,))
    if not action:
        raise HTTPException(status_code=404, detail="scheduled_action_not_found")
    if action.get("status") == "executed":
        return service._serialize_scheduled_action(action)
    execute(conn, "UPDATE scheduled_operational_actions SET status = 'running', updated_at = ? WHERE id = ?", (utcnow_iso(), action["id"]))
    payload = service._json(action.get("payload_json"), {})
    command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (action.get("command_id"),)) if action.get("command_id") else None
    if not command:
        execute(conn, "UPDATE scheduled_operational_actions SET status = 'failed', updated_at = ? WHERE id = ?", (utcnow_iso(), action["id"]))
        return {"id": action["id"], "status": "failed", "error": "missing_command"}
    bot = get_bot(conn, action["bot_id"])
    result = service._apply_bot_state_change(conn, bot, command, "bot.resume" if action.get("action_type") == "active" else f"bot.{action.get('action_type')}", {"message": payload.get("message"), "bot_target_state": action.get("action_type")}, utcnow_iso())
    execute(conn, "UPDATE scheduled_operational_actions SET status = 'executed', updated_at = ? WHERE id = ?", (utcnow_iso(), action["id"]))
    execute(conn, "UPDATE operational_command_requests SET status = CASE WHEN status IN ('scheduled','queued','running') THEN 'executed' ELSE status END, executed_at = COALESCE(executed_at, ?), updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), command["id"]))
    create_audit_log(conn, organization_id=command["organization_id"], actor_user_id=command.get("actor_user_id"), actor_type="system", entity_type="operational_command", entity_id=command["id"], action="operations.command.executed_from_scheduler", metadata={"action_id": action["id"], "result": result})
    return {"id": action["id"], "status": "executed", "result": result}
