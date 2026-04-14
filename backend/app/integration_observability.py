from __future__ import annotations

from typing import Any

from .db import execute, fetch_all
from .utils import from_json, new_id, to_json, utcnow_iso


def record_integration_event(
    conn,
    *,
    organization_id: str,
    integration_id: str | None,
    bot_id: str | None,
    provider: str,
    event_type: str,
    status: str,
    summary: str = "",
    severity: str = "info",
    external_reference: str | None = None,
    request_payload: dict[str, Any] | None = None,
    response_payload: dict[str, Any] | None = None,
    error_payload: dict[str, Any] | None = None,
    provider_status_code: int | None = None,
) -> dict[str, Any]:
    event_id = new_id("ievt")
    now = utcnow_iso()
    execute(
        conn,
        """
        INSERT INTO integration_events (
            id, organization_id, integration_id, bot_id, provider, event_type, status, severity,
            summary, external_reference, request_json, response_json, error_json,
            provider_status_code, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            organization_id,
            integration_id,
            bot_id,
            provider,
            event_type,
            status,
            severity,
            summary,
            external_reference,
            to_json(request_payload or {}),
            to_json(response_payload or {}),
            to_json(error_payload or {}),
            provider_status_code,
            now,
        ),
    )
    return {
        "id": event_id,
        "organization_id": organization_id,
        "integration_id": integration_id,
        "bot_id": bot_id,
        "provider": provider,
        "event_type": event_type,
        "status": status,
        "severity": severity,
        "summary": summary,
        "external_reference": external_reference,
        "request": request_payload or {},
        "response": response_payload or {},
        "error": error_payload or {},
        "provider_status_code": provider_status_code,
        "created_at": now,
    }


def integration_event_row(row: dict[str, Any]) -> dict[str, Any]:
    request = from_json(row.get("request_json"), {})
    response = from_json(row.get("response_json"), {})
    error = from_json(row.get("error_json"), {})
    summary = row.get("summary") or error.get("message") or row.get("event_type") or row.get("status")
    return {
        **row,
        "kind": row.get("event_type") or row.get("kind") or "provider",
        "summary": summary,
        "detail": row.get("detail") or error.get("message") or response.get("message") or summary,
        "request": request,
        "response": response,
        "error": error,
        "timestamp": row.get("created_at"),
    }


def list_integration_events(conn, *, organization_id: str, integration_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    if integration_id:
        rows = fetch_all(
            conn,
            "SELECT * FROM integration_events WHERE organization_id = ? AND integration_id = ? ORDER BY created_at DESC LIMIT ?",
            (organization_id, integration_id, limit),
        )
    else:
        rows = fetch_all(
            conn,
            "SELECT * FROM integration_events WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?",
            (organization_id, limit),
        )
    return [integration_event_row(row) for row in rows]


def integration_observability_summary(conn, *, organization_id: str, integration_id: str | None = None) -> dict[str, Any]:
    rows = list_integration_events(conn, organization_id=organization_id, integration_id=integration_id, limit=200)
    totals = {"ok": 0, "retry": 0, "failed": 0, "warning": 0}
    latest_error = None
    by_provider: dict[str, dict[str, Any]] = {}
    for row in rows:
        status = str(row.get("status") or "unknown").lower()
        provider = str(row.get("provider") or "unknown")
        if status in {"ok", "healthy", "connected", "completed", "paid", "verified"}:
            totals["ok"] += 1
        elif status in {"retry", "requeued", "running"}:
            totals["retry"] += 1
        elif status in {"warning", "degraded", "expired"}:
            totals["warning"] += 1
        else:
            totals["failed"] += 1
            if latest_error is None:
                latest_error = row
        bucket = by_provider.setdefault(provider, {"provider": provider, "events": 0, "failed": 0, "last_event_at": None})
        bucket["events"] += 1
        if status not in {"ok", "healthy", "connected", "completed", "paid", "verified", "running"}:
            bucket["failed"] += 1
        if not bucket["last_event_at"]:
            bucket["last_event_at"] = row.get("created_at")
    return {
        "totals": totals,
        "latest_error": latest_error,
        "providers": list(by_provider.values()),
        "recent": rows[:20],
    }
