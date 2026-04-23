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



def handle(service, uow, *, user: dict, organization_id: str, bot_id: str) -> list[dict]:
    conn = uow.conn
    require_permission(user, organization_id, "operations.control.read")
    service._get_bot(conn, user, bot_id)
    rows = fetch_all(conn, "SELECT * FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT 30", (organization_id, bot_id))
    return [service._serialize_command(item) for item in rows]
