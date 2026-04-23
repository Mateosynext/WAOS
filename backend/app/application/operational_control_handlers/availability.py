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



def handle(service, uow, *, user: dict, organization_id: str, bot_id: str, day: str | None = None) -> dict:
    conn = uow.conn
    require_permission(user, organization_id, "operations.control.read")
    service._get_bot(conn, user, bot_id)
    start_at, end_at = service._date_window(day or "today")
    appointments = fetch_all(conn, "SELECT * FROM appointments WHERE organization_id = ? AND bot_id = ? AND scheduled_for >= ? AND scheduled_for <= ? ORDER BY scheduled_for ASC", (organization_id, bot_id, start_at, end_at))
    overrides = fetch_all(conn, "SELECT * FROM availability_overrides WHERE organization_id = ? AND bot_id = ? AND status = 'active' AND end_at >= ? AND start_at <= ? ORDER BY start_at ASC", (organization_id, bot_id, start_at, end_at)) if table_exists(conn, "availability_overrides") else []
    return {
        "day": day or "today",
        "start_at": start_at,
        "end_at": end_at,
        "appointments": [service._serialize_appointment(item) for item in appointments],
        "overrides": [service._serialize_override(item) for item in overrides],
        "summary": {
            "appointments": len(appointments),
            "blocked_ranges": len([item for item in overrides if item.get("override_type") in {"block_slot", "block_day", "vacation"}]),
            "open_exceptions": len([item for item in overrides if item.get("override_type") == "open_exception"]),
        },
    }
