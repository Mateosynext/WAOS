from __future__ import annotations

from typing import Any

from .db import execute, fetch_all
from .utils import new_id, to_json, utcnow_iso

OPERATIONAL_STATES = {
    "local_created",
    "provider_pending",
    "provider_confirmed",
    "provider_failed",
    "retrying",
    "dead_letter",
}


def ensure_operational_events_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS operational_provider_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            conversation_id TEXT,
            correlation_id TEXT,
            job_id TEXT,
            message_id TEXT,
            outbox_message_id TEXT,
            tool_execution_id TEXT,
            payment_id TEXT,
            integration_id TEXT,
            provider TEXT,
            provider_request_id TEXT,
            provider_message_id TEXT,
            state TEXT NOT NULL,
            event_type TEXT NOT NULL,
            source TEXT NOT NULL,
            request_json TEXT NOT NULL DEFAULT '{}',
            response_json TEXT NOT NULL DEFAULT '{}',
            error_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_operational_provider_events_org_created ON operational_provider_events(organization_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_operational_provider_events_correlation ON operational_provider_events(correlation_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_operational_provider_events_job ON operational_provider_events(job_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_operational_provider_events_message ON operational_provider_events(message_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_operational_provider_events_outbox ON operational_provider_events(outbox_message_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_operational_provider_events_tool ON operational_provider_events(tool_execution_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_operational_provider_events_payment ON operational_provider_events(payment_id, created_at DESC);
        """
    )


def record_operational_event(
    conn,
    *,
    organization_id: str,
    state: str,
    event_type: str,
    source: str,
    bot_id: str | None = None,
    conversation_id: str | None = None,
    correlation_id: str | None = None,
    job_id: str | None = None,
    message_id: str | None = None,
    outbox_message_id: str | None = None,
    tool_execution_id: str | None = None,
    payment_id: str | None = None,
    integration_id: str | None = None,
    provider: str | None = None,
    provider_request_id: str | None = None,
    provider_message_id: str | None = None,
    request: dict[str, Any] | None = None,
    response: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if state not in OPERATIONAL_STATES:
        raise ValueError(f"invalid_operational_state:{state}")
    ensure_operational_events_schema(conn)
    event = {
        "id": new_id("opevt"),
        "organization_id": organization_id,
        "bot_id": bot_id,
        "conversation_id": conversation_id,
        "correlation_id": correlation_id,
        "job_id": job_id,
        "message_id": message_id,
        "outbox_message_id": outbox_message_id,
        "tool_execution_id": tool_execution_id,
        "payment_id": payment_id,
        "integration_id": integration_id,
        "provider": provider,
        "provider_request_id": provider_request_id,
        "provider_message_id": provider_message_id,
        "state": state,
        "event_type": event_type,
        "source": source,
        "request_json": to_json(request or {}),
        "response_json": to_json(response or {}),
        "error_json": to_json(error or {}),
        "created_at": utcnow_iso(),
    }
    execute(
        conn,
        """
        INSERT INTO operational_provider_events (
            id, organization_id, bot_id, conversation_id, correlation_id, job_id, message_id,
            outbox_message_id, tool_execution_id, payment_id, integration_id, provider,
            provider_request_id, provider_message_id, state, event_type, source,
            request_json, response_json, error_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["id"], event["organization_id"], event["bot_id"], event["conversation_id"], event["correlation_id"], event["job_id"], event["message_id"],
            event["outbox_message_id"], event["tool_execution_id"], event["payment_id"], event["integration_id"], event["provider"],
            event["provider_request_id"], event["provider_message_id"], event["state"], event["event_type"], event["source"],
            event["request_json"], event["response_json"], event["error_json"], event["created_at"],
        ),
    )
    return event


def list_operational_events(
    conn,
    *,
    organization_id: str,
    correlation_id: str | None = None,
    job_id: str | None = None,
    message_id: str | None = None,
    outbox_message_id: str | None = None,
    tool_execution_id: str | None = None,
    payment_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    ensure_operational_events_schema(conn)
    where = ["organization_id = ?"]
    params: list[Any] = [organization_id]
    filters = {
        "correlation_id": correlation_id,
        "job_id": job_id,
        "message_id": message_id,
        "outbox_message_id": outbox_message_id,
        "tool_execution_id": tool_execution_id,
        "payment_id": payment_id,
    }
    for column, value in filters.items():
        if value:
            where.append(f"{column} = ?")
            params.append(value)
    params.append(max(1, min(int(limit or 100), 500)))
    return fetch_all(
        conn,
        f"SELECT * FROM operational_provider_events WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT ?",
        tuple(params),
    )
