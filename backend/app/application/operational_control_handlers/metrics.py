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



def handle(service, uow, *, user: dict, organization_id: str, bot_id: str, window_days: int = 7) -> dict:
    conn = uow.conn
    require_permission(user, organization_id, "operations.control.read")
    service._get_bot(conn, user, bot_id)
    since = (utcnow() - dt.timedelta(days=max(1, int(window_days)))).isoformat().replace("+00:00", "Z")
    totals = fetch_one(conn, "SELECT COUNT(*) AS total, SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed, SUM(CASE WHEN status = 'awaiting_confirmation' THEN 1 ELSE 0 END) AS awaiting_confirmation, SUM(CASE WHEN status = 'executed' THEN 1 ELSE 0 END) AS executed, SUM(CASE WHEN status IN ('reverted','partially_reverted') THEN 1 ELSE 0 END) AS reverted, SUM(CASE WHEN status = 'rate_limited' THEN 1 ELSE 0 END) AS rate_limited, SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) AS high_risk FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? AND created_at >= ?", (organization_id, bot_id, since)) or {}
    intents = fetch_all(conn, "SELECT detected_intent, COUNT(*) AS count FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? AND created_at >= ? GROUP BY detected_intent ORDER BY count DESC LIMIT 8", (organization_id, bot_id, since))
    statuses = fetch_all(conn, "SELECT status, COUNT(*) AS count FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? AND created_at >= ? GROUP BY status ORDER BY count DESC", (organization_id, bot_id, since))
    ambiguous = fetch_one(conn, "SELECT COUNT(*) AS total FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? AND created_at >= ? AND detected_intent IS NULL", (organization_id, bot_id, since)) or {"total": 0}
    alerts_open = fetch_one(conn, "SELECT COUNT(*) AS total FROM operational_command_alerts WHERE organization_id = ? AND bot_id = ? AND status = 'open' AND created_at >= ?", (organization_id, bot_id, since)) if table_exists(conn, 'operational_command_alerts') else {"total": 0}
    return {
        "window_days": window_days,
        "summary": {
            "total": int(totals.get("total") or 0),
            "executed": int(totals.get("executed") or 0),
            "failed": int(totals.get("failed") or 0),
            "awaiting_confirmation": int(totals.get("awaiting_confirmation") or 0),
            "high_risk": int(totals.get("high_risk") or 0),
            "ambiguous": int(ambiguous.get("total") or 0),
            "rate_limited": int(totals.get("rate_limited") or 0),
            "reverted": int(totals.get("reverted") or 0),
            "alerts_open": int((alerts_open or {}).get("total") or 0),
        },
        "intents": [{"intent": row.get("detected_intent") or "unknown", "count": int(row.get("count") or 0)} for row in intents],
        "statuses": [{"status": row.get("status") or "unknown", "count": int(row.get("count") or 0)} for row in statuses],
    }
