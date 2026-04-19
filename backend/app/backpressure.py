from __future__ import annotations

import math
from typing import Any

from .config import settings
from .utils import add_minutes, parse_iso, utcnow_iso
from .world_class import consume_retry_budget, fetch_one, record_dead_letter_event, table_exists


def queue_depth_snapshot(conn, *, organization_id: str | None = None) -> dict[str, Any]:
    params: list[Any] = []
    jobs_clause = "WHERE status IN ('queued','retry','scheduled')"
    outbox_clause = "WHERE status IN ('queued','retry')"
    if organization_id:
        jobs_clause += " AND organization_id = ?"
        outbox_clause += " AND organization_id = ?"
        params.append(organization_id)
    jobs_row = fetch_one(conn, f"SELECT COUNT(*) AS total, MIN(scheduled_for) AS oldest FROM automation_jobs {jobs_clause}", tuple(params)) if table_exists(conn, "automation_jobs") else {"total": 0, "oldest": None}
    outbox_row = fetch_one(conn, f"SELECT COUNT(*) AS total, MIN(COALESCE(next_attempt_at, scheduled_for, created_at)) AS oldest FROM outbox_messages {outbox_clause}", tuple(params)) if table_exists(conn, "outbox_messages") else {"total": 0, "oldest": None}
    jobs_total = int((jobs_row or {}).get("total") or 0)
    outbox_total = int((outbox_row or {}).get("total") or 0)
    oldest_age_seconds = 0
    oldest_candidates = [value for value in [(jobs_row or {}).get("oldest"), (outbox_row or {}).get("oldest")] if value]
    if oldest_candidates:
        oldest_dt = min(dt for dt in (parse_iso(value) for value in oldest_candidates) if dt is not None)
        now_dt = parse_iso(utcnow_iso())
        if oldest_dt and now_dt:
            oldest_age_seconds = max(0, int((now_dt - oldest_dt).total_seconds()))
    queue_pressure = jobs_total + math.ceil(outbox_total * 0.7)
    return {
        "organization_id": organization_id,
        "jobs_queued": jobs_total,
        "outbox_queued": outbox_total,
        "queue_pressure": queue_pressure,
        "oldest_age_seconds": oldest_age_seconds,
    }


def recommended_worker_batch_size(conn, *, organization_id: str | None = None, base_batch_size: int | None = None) -> int:
    base = int(base_batch_size or settings.worker_batch_size)
    ceiling = max(base, settings.worker_backpressure_batch_ceiling)
    snapshot = queue_depth_snapshot(conn, organization_id=organization_id)
    pressure = int(snapshot.get("queue_pressure") or 0)
    oldest = int(snapshot.get("oldest_age_seconds") or 0)
    multiplier = 1
    if pressure >= 400 or oldest >= 1800:
        multiplier = 4
    elif pressure >= 150 or oldest >= 900:
        multiplier = 3
    elif pressure >= 60 or oldest >= 300:
        multiplier = 2
    return max(base, min(ceiling, base * multiplier))


def adaptive_poll_seconds(*, processed_total: int, queue_pressure: int, oldest_age_seconds: int, base_seconds: int | None = None) -> int:
    base = int(base_seconds or settings.worker_max_poll_seconds or settings.worker_min_poll_seconds)
    if queue_pressure >= 250 or oldest_age_seconds >= 900:
        return settings.worker_min_poll_seconds
    if processed_total > 0 or queue_pressure >= 50:
        return max(settings.worker_min_poll_seconds, min(base, 2))
    if queue_pressure >= 10:
        return max(settings.worker_min_poll_seconds, min(base, 4))
    return max(settings.worker_min_poll_seconds, min(base, settings.worker_max_poll_seconds))


def graceful_degradation_flags(conn, *, organization_id: str | None = None) -> dict[str, Any]:
    snapshot = queue_depth_snapshot(conn, organization_id=organization_id)
    queue_pressure = int(snapshot.get("queue_pressure") or 0)
    oldest = int(snapshot.get("oldest_age_seconds") or 0)
    high_pressure = queue_pressure >= 120 or oldest >= 600
    extreme_pressure = queue_pressure >= 300 or oldest >= 1800
    return {
        "queue": snapshot,
        "degrade_ai_generation": high_pressure,
        "prefer_heuristics": high_pressure,
        "pause_non_critical_jobs": extreme_pressure,
        "send_minimal_callbacks": extreme_pressure,
    }


def resolve_failure_outcome(
    conn,
    *,
    provider: str,
    scope_key: str,
    attempts: int,
    max_attempts: int,
    organization_id: str | None,
    channel: str,
    source_table: str,
    source_id: str,
    reason_code: str,
    payload_snapshot: dict[str, Any] | None,
    error_payload: dict[str, Any] | None,
    non_retryable: bool = False,
    window_seconds: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    retry_state = consume_retry_budget(
        conn,
        provider=provider,
        scope_key=scope_key,
        max_retries=max_attempts,
        window_seconds=int(window_seconds or settings.worker_retry_budget_window_seconds),
        metadata=metadata or {},
    )
    dead_letter = non_retryable or attempts >= max_attempts or not retry_state.get("allowed", True)
    status = "dead_letter" if dead_letter else "retry"
    if dead_letter:
        record_dead_letter_event(
            conn,
            organization_id=organization_id,
            channel=channel,
            source_table=source_table,
            source_id=source_id,
            reason_code=reason_code,
            payload_snapshot=payload_snapshot,
            error_payload=error_payload,
        )
    return {"status": status, "retry_budget": retry_state, "dead_letter": dead_letter}


def next_retry_schedule(*, attempts: int, base_delay_minutes: int = 2, max_delay_minutes: int = 15) -> str:
    delay = min(max_delay_minutes, max(1, attempts) * base_delay_minutes)
    return add_minutes(utcnow_iso(), delay)
