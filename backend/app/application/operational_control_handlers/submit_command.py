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
        raise HTTPException(status_code=400, detail={"message": parsed.get("reply_text") or "Comando ambiguo", "code": "operational_command_ambiguous"})
    return service._submit_preparsed_command(conn, user=user, bot=bot, raw_text=payload.text, parsed=parsed, source_channel=payload.source_channel, dry_run=payload.dry_run, actor_phone_e164=payload.actor_phone_e164)
