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



def handle(service, uow, *, user: dict, command_id: str, confirmation_code: str | None = None) -> dict:
    conn = uow.conn
    command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,))
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    require_permission(user, command["organization_id"], "operations.control.high_impact")
    service._get_bot(conn, user, command["bot_id"])
    if command.get("status") != "awaiting_confirmation":
        raise HTTPException(status_code=409, detail="Command is not awaiting confirmation")
    if confirmation_code and command.get("confirmation_code") and confirmation_code.upper() != str(command.get("confirmation_code")).upper():
        raise HTTPException(status_code=400, detail="Invalid confirmation code")
    parsed = {"intent": command.get("detected_intent"), "entities": service._json(command.get("parsed_entities_json"), {})}
    impact = service._json(command.get("result_json"), {}).get("impact") or service._build_impact(conn, get_bot(conn, command["bot_id"]), parsed)
    if service._needs_second_approval(conn, command["organization_id"], command["bot_id"], parsed.get("intent"), impact):
        execute(conn, "UPDATE operational_command_requests SET status = 'awaiting_second_approval', approved_by_user_id = ?, approved_at = ?, updated_at = ? WHERE id = ?", (user["id"], utcnow_iso(), utcnow_iso(), command_id))
        create_audit_log(conn, organization_id=command["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="operational_command", entity_id=command_id, action="operations.command.first_approved", metadata={"intent": parsed.get("intent")})
        return service._serialize_command(fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,)))
    result = service._execute_command(conn, command_id=command_id)
    return result
