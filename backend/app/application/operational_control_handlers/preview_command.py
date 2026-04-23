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



def handle(service, uow, *, user: dict, payload) -> dict:
    conn = uow.conn
    require_permission(user, payload.organization_id, "operations.control.execute")
    bot = service._get_bot(conn, user, payload.bot_id)
    parsed = service._parse_command(payload.text, bot)
    if not parsed.get("intent"):
        return {
            "ok": False,
            "status": "ambiguous",
            "reply_text": parsed.get("reply_text") or "No pude interpretar el comando operativo.",
            "intent": None,
            "impact": {"appointments_affected": 0, "clients_notified": 0},
            "requires_confirmation": False,
        }
    impact = service._build_impact(conn, bot, parsed)
    requires_confirmation = service._requires_confirmation(parsed["intent"], impact)
    second_approval = service._needs_second_approval(conn, bot["organization_id"], bot["id"], parsed["intent"], impact)
    return {
        "ok": True,
        "status": "preview",
        "intent": parsed["intent"],
        "entities": parsed.get("entities", {}),
        "impact": impact,
        "requires_confirmation": requires_confirmation,
        "requires_second_approval": second_approval,
        "reply_text": service._preview_reply(parsed["intent"], parsed.get("entities", {}), impact, requires_confirmation),
    }
