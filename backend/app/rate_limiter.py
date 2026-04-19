from __future__ import annotations

from typing import Any

from .config import settings
from .world_class_plus import consume_defensive_rate_limit


def defensive_rate_limit(
    conn,
    *,
    organization_id: str | None,
    scope_key: str,
    channel: str,
    direction: str,
    max_events: int,
    window_seconds: int,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return consume_defensive_rate_limit(
        conn,
        organization_id=organization_id,
        scope_key=scope_key,
        channel=channel,
        direction=direction,
        max_events=max_events,
        window_seconds=window_seconds,
        metadata=metadata,
    )


def inbound_client_rate_limit(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    phone: str,
    channel: str = "whatsapp",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scope_key = f"inbound:{organization_id}:{bot_id}:{channel}:{phone}"
    return defensive_rate_limit(
        conn,
        organization_id=organization_id,
        scope_key=scope_key,
        channel=channel,
        direction="inbound",
        max_events=settings.inbound_spam_max_events,
        window_seconds=settings.inbound_spam_window_seconds,
        metadata=metadata,
    )


def public_ingest_rate_limit(
    conn,
    *,
    organization_id: str,
    scope_key: str,
    channel: str,
    direction: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return defensive_rate_limit(
        conn,
        organization_id=organization_id,
        scope_key=scope_key,
        channel=channel,
        direction=direction,
        max_events=settings.public_ingest_max_events,
        window_seconds=settings.public_ingest_window_seconds,
        metadata=metadata,
    )


def defensive_limit_status(row: dict[str, Any] | None, *, reason_code: str = "defensive_rate_limit_exceeded") -> dict[str, Any]:
    row = row or {}
    return {
        "allowed": bool(row.get("allowed", False)),
        "remaining": int(row.get("remaining") or 0),
        "reason_code": reason_code,
        "window_seconds": int(row.get("window_seconds") or 0),
        "events_used": int(row.get("events_used") or 0),
        "max_events": int(row.get("max_events") or 0),
    }
