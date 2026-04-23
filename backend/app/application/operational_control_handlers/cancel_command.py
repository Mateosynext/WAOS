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



def handle(service, uow, *, user: dict, command_id: str, reason: str = '') -> dict:
    conn = uow.conn
    command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,))
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    require_permission(user, command["organization_id"], "operations.control.undo")
    service._cancel_command_internal(conn, command, reason=reason or "cancelled_by_user")
    create_audit_log(conn, organization_id=command["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="operational_command", entity_id=command_id, action="operations.command.cancelled", metadata={"reason": reason})
    return service._serialize_command(fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,)))
