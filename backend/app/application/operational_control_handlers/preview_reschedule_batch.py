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
    require_permission(user, payload.organization_id, "appointment.manage")
    bot = service._get_bot(conn, user, payload.bot_id)
    entities = service._structured_reschedule_entities(payload)
    parsed = {"intent": "appointment.reschedule_mass", "entities": entities}
    impact = service._build_impact(conn, bot, parsed)
    plan = service._plan_reschedule(conn, payload.organization_id, payload.bot_id, entities)
    impact["planned"] = len([item for item in plan if item["status"] == "planned"])
    impact["unresolved"] = len([item for item in plan if item["status"] != "planned"])
    return {
        "ok": True,
        "status": "preview",
        "intent": "appointment.reschedule_mass",
        "entities": entities,
        "impact": impact,
        "plan": plan,
        "requires_confirmation": True,
        "reply_text": f"Preview listo. Se afectarían {impact['appointments_affected']} cita(s) y {impact['planned']} quedarían reprogramadas con slot válido.",
    }
