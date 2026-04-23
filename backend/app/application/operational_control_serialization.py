from __future__ import annotations

import datetime as dt
import json
import os
import re
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from ..db import execute, fetch_all, fetch_one, table_exists
from ..repositories.audit import create_audit_log
from ..repositories.bots import get_bot
from ..repositories.conversations import create_message
from ..security import ensure_bot_access
from ..utils import add_minutes, new_id, parse_iso, to_json, utcnow, utcnow_iso
from .operational_control_policy import needs_second_approval, requires_confirmation, risk_level
from .operational_control_presenters import (
    serialize_alert,
    serialize_appointment,
    serialize_authorized_number,
    serialize_command,
    serialize_override,
    serialize_scheduled_action,
)

class OperationalControlSerializationMixin:
    def _json(self, value: str | None, default: Any) -> Any:
        try:
            return json.loads(value) if value else default
        except Exception:
            return default

    def _serialize_command(self, row: dict) -> dict:
        return serialize_command(row)

    def _serialize_authorized_number(self, row: dict) -> dict:
        return serialize_authorized_number(row, scope_summary=self._scope_summary(self._json(row.get('scope_json'), {})))

    def _serialize_scheduled_action(self, row: dict) -> dict:
        return serialize_scheduled_action(row)

    def _serialize_appointment(self, row: dict) -> dict:
        return serialize_appointment(row)

    def _serialize_override(self, row: dict) -> dict:
        return serialize_override(row)

    def _serialize_alert(self, row: dict) -> dict:
        return serialize_alert(row)
