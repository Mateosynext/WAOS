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



def handle(service, uow, *, user: dict, organization_id: str, bot_id: str) -> dict:
    conn = uow.conn
    require_permission(user, organization_id, "operations.control.read")
    bot = service._get_bot(conn, user, bot_id)
    authorized = fetch_all(conn, "SELECT * FROM authorized_operational_numbers WHERE organization_id = ? AND bot_id = ? AND status = 'verified' ORDER BY updated_at DESC", (organization_id, bot_id)) if table_exists(conn, "authorized_operational_numbers") else []
    recent = fetch_all(conn, "SELECT * FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT 12", (organization_id, bot_id)) if table_exists(conn, "operational_command_requests") else []
    scheduled = fetch_all(conn, "SELECT * FROM scheduled_operational_actions WHERE organization_id = ? AND bot_id = ? AND status IN ('scheduled','queued','running') ORDER BY execute_at ASC LIMIT 12", (organization_id, bot_id)) if table_exists(conn, "scheduled_operational_actions") else []
    alerts = fetch_all(conn, "SELECT * FROM operational_command_alerts WHERE organization_id = ? AND bot_id = ? AND status = 'open' ORDER BY created_at DESC LIMIT 8", (organization_id, bot_id)) if table_exists(conn, "operational_command_alerts") else []
    today_start, today_end = service._date_window("today")
    blocked = fetch_all(conn, "SELECT * FROM availability_overrides WHERE organization_id = ? AND bot_id = ? AND status = 'active' AND start_at >= ? AND start_at <= ? ORDER BY start_at ASC", (organization_id, bot_id, today_start, today_end)) if table_exists(conn, "availability_overrides") else []
    upcoming_appointments = fetch_all(conn, "SELECT * FROM appointments WHERE organization_id = ? AND bot_id = ? AND status IN ('scheduled','confirmed') AND scheduled_for >= ? ORDER BY scheduled_for ASC LIMIT 20", (organization_id, bot_id, utcnow_iso()))
    return {
        "organization_id": organization_id,
        "bot_id": bot_id,
        "bot": {
            "id": bot["id"],
            "name": bot.get("name"),
            "status": bot.get("status"),
            "ai_paused": bool(bot.get("ai_paused")),
            "current_state": bot.get("current_state"),
            "operational_state": bot.get("operational_state") or ("paused" if bot.get("ai_paused") else "active"),
            "temp_unavailability_message": bot.get("temp_unavailability_message"),
            "operational_resume_at": bot.get("operational_resume_at"),
        },
        "counts": {
            "authorized_numbers": len(authorized),
            "recent_commands": len(recent),
            "scheduled_actions": len(scheduled),
            "alerts_open": len(alerts),
            "blocked_slots_today": len(blocked),
            "upcoming_appointments": len(upcoming_appointments),
        },
        "authorized_numbers": [service._serialize_authorized_number(item) for item in authorized[:8]],
        "recent_commands": [service._serialize_command(item) for item in recent],
        "scheduled_actions": [service._serialize_scheduled_action(item) for item in scheduled],
        "alerts": [service._serialize_alert(item) for item in alerts],
        "upcoming_appointments": [service._serialize_appointment(item) for item in upcoming_appointments[:8]],
    }
