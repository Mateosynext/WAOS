from __future__ import annotations

import os
import sqlite3
from typing import Any

from ..db import execute, fetch_all, fetch_one
from ..defaults import default_bot_config
from ..utils import from_json, hash_password, new_id, slugify, to_json, utcnow_iso
from ..verticals import build_organization_settings

def get_contact_memory(conn: sqlite3.Connection, contact_id: str, bot_id: str) -> dict | None:
    return fetch_one(
        conn,
        "SELECT * FROM contact_memory WHERE contact_id = ? AND bot_id = ?",
        (contact_id, bot_id),
    )


def get_contact(conn: sqlite3.Connection, contact_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", (contact_id,))


def upsert_contact(conn: sqlite3.Connection, *, organization_id: str, phone: str, name: str | None = None) -> dict:
    existing = fetch_one(conn, "SELECT * FROM contacts WHERE organization_id = ? AND phone = ?", (organization_id, phone))
    now = utcnow_iso()
    if existing:
        if name and name != existing.get("name"):
            execute(conn, "UPDATE contacts SET name = ?, updated_at = ? WHERE id = ?", (name, now, existing["id"]))
        return get_contact(conn, existing["id"])
    contact_id = new_id("contact")
    execute(
        conn,
        """
        INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, NULL, '[]', ?, ?)
        """,
        (contact_id, organization_id, phone, name, now, now),
    )
    return get_contact(conn, contact_id)


def upsert_memory(conn: sqlite3.Connection, *, organization_id: str, contact_id: str, bot_id: str) -> dict:
    existing = get_contact_memory(conn, contact_id, bot_id)
    now = utcnow_iso()
    if existing:
        return existing
    memory_id = new_id("mem")
    execute(
        conn,
        """
        INSERT INTO contact_memory
        (id, organization_id, contact_id, bot_id, lead_stage, lead_score, interest, objections, summary, next_action, followup_at, memory_json, last_updated_at)
        VALUES (?, ?, ?, ?, 'new', 0, NULL, '', '', '', NULL, '{}', ?)
        """,
        (memory_id, organization_id, contact_id, bot_id, now),
    )
    return get_contact_memory(conn, contact_id, bot_id)
