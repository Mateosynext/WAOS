from __future__ import annotations

import json

from ..db import execute, fetch_all
from ..utils import new_id, to_json, utcnow_iso


def _report_job_dedupe_key(*, organization_id: str, bot_id: str | None, period_start: str, period_end: str) -> str:
    return f"report:{organization_id}:{bot_id or 'all'}:{period_start}:{period_end}"


def serialize_report_generation_job(row: dict) -> dict:
    return {**row, "request": json.loads(row.get("request_json") or "{}")}


def queue_executive_report_generation(conn, *, organization_id: str, period_start: str, period_end: str, bot_id: str | None = None, delivery_channels: list[str] | None = None, requested_by_user_id: str | None = None) -> dict:
    dedupe_key = _report_job_dedupe_key(organization_id=organization_id, bot_id=bot_id, period_start=period_start, period_end=period_end)
    existing = fetch_all(conn, "SELECT * FROM report_generation_jobs WHERE dedupe_key = ? ORDER BY created_at DESC LIMIT 1", (dedupe_key,))
    if existing:
        return serialize_report_generation_job(existing[0])
    now = utcnow_iso()
    payload = {"organization_id": organization_id, "bot_id": bot_id, "period_start": period_start, "period_end": period_end, "delivery_channels": delivery_channels or []}
    job = {
        "id": new_id("rjob"),
        "organization_id": organization_id,
        "bot_id": bot_id,
        "requested_by_user_id": requested_by_user_id,
        "dedupe_key": dedupe_key,
        "request_json": to_json(payload),
        "status": "queued",
        "attempts": 0,
        "last_error": None,
        "report_id": None,
        "scheduled_for": now,
        "started_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    execute(conn, "INSERT INTO report_generation_jobs (id, organization_id, bot_id, requested_by_user_id, dedupe_key, request_json, status, attempts, last_error, report_id, scheduled_for, started_at, completed_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (job['id'], job['organization_id'], job['bot_id'], job['requested_by_user_id'], job['dedupe_key'], job['request_json'], job['status'], job['attempts'], job['last_error'], job['report_id'], job['scheduled_for'], job['started_at'], job['completed_at'], job['created_at'], job['updated_at']))
    return serialize_report_generation_job(job)


def list_report_generation_jobs(conn, *, organization_id: str | None = None) -> list[dict]:
    if organization_id:
        rows = fetch_all(conn, "SELECT * FROM report_generation_jobs WHERE organization_id = ? ORDER BY created_at DESC LIMIT 100", (organization_id,))
    else:
        rows = fetch_all(conn, "SELECT * FROM report_generation_jobs ORDER BY created_at DESC LIMIT 100")
    return [serialize_report_generation_job(row) for row in rows]
