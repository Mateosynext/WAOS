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
    require_permission(user, payload.organization_id, "operations.chat.authorize_number")
    service._get_bot(conn, user, payload.bot_id)
    existing = fetch_one(conn, "SELECT * FROM authorized_operational_numbers WHERE organization_id = ? AND bot_id = ? AND phone_e164 = ?", (payload.organization_id, payload.bot_id, payload.phone_e164))
    now = utcnow_iso()
    if existing:
        execute(conn, "UPDATE authorized_operational_numbers SET role = ?, allowed_intents_json = ?, scope_json = ?, status = ?, verified_at = ?, updated_at = ?, created_by = ? WHERE id = ?", (payload.role, to_json(payload.allowed_intents), to_json(payload.scope), payload.status, now if payload.status == 'verified' else None, now, user['id'], existing['id']))
        row = fetch_one(conn, "SELECT * FROM authorized_operational_numbers WHERE id = ?", (existing["id"],))
    else:
        number_id = new_id("opnum")
        execute(conn, "INSERT INTO authorized_operational_numbers (id, organization_id, bot_id, phone_e164, role, allowed_intents_json, scope_json, status, verified_at, last_used_at, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)", (number_id, payload.organization_id, payload.bot_id, payload.phone_e164, payload.role, to_json(payload.allowed_intents), to_json(payload.scope), payload.status, now if payload.status == 'verified' else None, user['id'], now, now))
        row = fetch_one(conn, "SELECT * FROM authorized_operational_numbers WHERE id = ?", (number_id,))
    create_audit_log(conn, organization_id=payload.organization_id, actor_user_id=user["id"], actor_type="user", entity_type="authorized_operational_number", entity_id=row["id"], action="operations.authorized_number.upserted", metadata={"phone": payload.phone_e164, "status": payload.status, "allowed_intents": payload.allowed_intents})
    return service._serialize_authorized_number(row)
