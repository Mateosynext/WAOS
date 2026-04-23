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
    return service._submit_preparsed_command(conn, user=user, bot=bot, raw_text=f"structured_reschedule:{payload.scope_day}", parsed=parsed, source_channel="portal", dry_run=False)
