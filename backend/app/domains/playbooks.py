from __future__ import annotations

from collections import Counter
from typing import Any

from ..config import settings
from ..db import execute, fetch_all, fetch_one
from ..repositories import create_audit_log, create_message, get_bot, get_contact, get_contact_memory, get_conversation, upsert_memory
from ..utils import add_minutes, new_id, parse_iso, to_json, from_json, utcnow_iso

def create_playbook(conn, *, organization_id: str, industry: str, name: str, config: dict[str, Any]) -> dict:
    playbook_id = new_id("pb")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO industry_playbooks (id, organization_id, industry, name, status, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, 'active', ?, ?, ?)",
        (playbook_id, organization_id, industry, name, to_json(config), now, now),
    )
    return fetch_one(conn, "SELECT * FROM industry_playbooks WHERE id = ?", (playbook_id,))
