from __future__ import annotations

from typing import Any

from .base import ConnectionLike
from ..db import execute, fetch_one, table_exists
from ..utils import hash_value, new_id, to_json, utcnow_iso


def register_event_receipt(conn: ConnectionLike, *, organization_id: str, event_key: str, status: str, stored_event: dict[str, Any]) -> bool:
    if not table_exists(conn, "webhook_event_receipts"):
        return True
    existing = fetch_one(conn, "SELECT * FROM webhook_event_receipts WHERE channel = 'whatsapp' AND external_event_id = ?", (event_key,))
    if existing:
        return False
    execute(
        conn,
        """
        INSERT INTO webhook_event_receipts
        (id, channel, organization_id, external_event_id, status, payload_hash, created_at)
        VALUES (?, 'whatsapp', ?, ?, ?, ?, ?)
        """,
        (new_id("wreceipt"), organization_id, event_key, status, hash_value(to_json(stored_event)), utcnow_iso()),
    )
    return True


def find_outbox_by_provider_message_id(conn: ConnectionLike, provider_message_id: str | None) -> dict | None:
    if not provider_message_id:
        return None
    return fetch_one(conn, "SELECT * FROM outbox_messages WHERE provider_message_id = ? ORDER BY created_at DESC LIMIT 1", (provider_message_id,))


def find_message_by_external_id(conn: ConnectionLike, provider_message_id: str | None) -> dict | None:
    if not provider_message_id:
        return None
    return fetch_one(conn, "SELECT * FROM messages WHERE external_id = ? ORDER BY created_at DESC LIMIT 1", (provider_message_id,))


def update_outbox_status_event(conn: ConnectionLike, *, outbox_id: str, status: str, provider_response: dict[str, Any], provider_status_code: int) -> dict | None:
    execute(
        conn,
        "UPDATE outbox_messages SET status = ?, provider_response_json = ?, provider_status_code = COALESCE(provider_status_code, ?) WHERE id = ?",
        (status, to_json(provider_response), provider_status_code, outbox_id),
    )
    return fetch_one(conn, "SELECT * FROM outbox_messages WHERE id = ?", (outbox_id,))


def update_message_status_event(conn: ConnectionLike, *, message_id: str, status: str, metadata: dict[str, Any]) -> dict | None:
    execute(conn, "UPDATE messages SET status = ?, metadata_json = ? WHERE id = ?", (status, to_json(metadata), message_id))
    return fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (message_id,))
