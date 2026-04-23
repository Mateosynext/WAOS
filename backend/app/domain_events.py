from __future__ import annotations

from typing import Any

from .db import execute, table_exists
from .platform.observability import log_event
from .utils import new_id, to_json, utcnow_iso


def emit_domain_event(
    conn,
    *,
    event_name: str,
    organization_id: str | None = None,
    bot_id: str | None = None,
    conversation_id: str | None = None,
    message_id: str | None = None,
    correlation_id: str | None = None,
    status: str = "ok",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "id": new_id("evt"),
        "event_name": event_name,
        "organization_id": organization_id,
        "bot_id": bot_id,
        "conversation_id": conversation_id,
        "message_id": message_id,
        "correlation_id": correlation_id,
        "status": status,
        "payload": payload or {},
        "created_at": utcnow_iso(),
    }
    log_event(
        event_name,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=conversation_id,
        message_id=message_id,
        correlation_id=correlation_id,
        status=status,
        payload=record["payload"],
    )
    if table_exists(conn, "domain_events"):
        execute(
            conn,
            "INSERT INTO domain_events (id, event_name, organization_id, bot_id, conversation_id, message_id, correlation_id, status, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record["id"], event_name, organization_id, bot_id, conversation_id, message_id, correlation_id, status, to_json(record["payload"]), record["created_at"]),
        )
    return record
