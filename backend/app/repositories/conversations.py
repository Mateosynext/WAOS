from __future__ import annotations

import os
from typing import Any

from .base import ConnectionLike

from ..db import execute, fetch_all, fetch_one, has_column
from ..defaults import default_bot_config
from ..utils import from_json, hash_password, new_id, slugify, to_json, utcnow_iso
from ..verticals import build_organization_settings

def get_conversation(conn: ConnectionLike, conversation_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (conversation_id,))


def upsert_conversation(conn: ConnectionLike, *, organization_id: str, bot_id: str, contact_id: str) -> dict:
    existing = fetch_one(
        conn,
        "SELECT * FROM conversations WHERE organization_id = ? AND bot_id = ? AND contact_id = ?",
        (organization_id, bot_id, contact_id),
    )
    now = utcnow_iso()
    if existing:
        execute(conn, "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, existing["id"]))
        return get_conversation(conn, existing["id"])
    conversation_id = new_id("conv")
    execute(
        conn,
        """
        INSERT INTO conversations
        (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'ai_active', 0, 1, NULL, NULL, NULL, NULL, NULL, NULL, ?, ?)
        """,
        (conversation_id, organization_id, bot_id, contact_id, now, now),
    )
    return get_conversation(conn, conversation_id)


def create_message(
    conn: ConnectionLike,
    *,
    organization_id: str,
    conversation_id: str,
    contact_id: str | None,
    bot_id: str,
    direction: str,
    kind: str,
    source: str,
    body: str,
    external_id: str | None = None,
    status: str = "sent",
    metadata: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict:
    message_id = new_id("msg")
    now = utcnow_iso()
    payload = {**(metadata or {})}
    if correlation_id:
        payload.setdefault("correlation_id", correlation_id)
    if has_column(conn, "messages", "correlation_id"):
        execute(
            conn,
            """
            INSERT INTO messages
            (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, correlation_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                organization_id,
                conversation_id,
                contact_id,
                bot_id,
                direction,
                kind,
                source,
                body,
                external_id,
                status,
                to_json(payload),
                correlation_id,
                now,
            ),
        )
    else:
        execute(
            conn,
            """
            INSERT INTO messages
            (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                organization_id,
                conversation_id,
                contact_id,
                bot_id,
                direction,
                kind,
                source,
                body,
                external_id,
                status,
                to_json(payload),
                now,
            ),
        )
    execute(
        conn,
        """
        UPDATE conversations
        SET last_message_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (now, now, conversation_id),
    )
    return fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (message_id,))
