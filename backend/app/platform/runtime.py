from __future__ import annotations

import hashlib
import hmac
from typing import Any

from ..config import settings
from ..db import execute, fetch_all, fetch_one
from ..contracts import count_row, runtime_callback_row, integration_sync_run_row
from ..verticals import get_vertical_profile
from ..world_class import circuit_breaker_summary, summarize_ai_usage
from ..telemetry_runtime import observability_dashboard_summary
from ..utils import (
    add_minutes,
    current_mfa_code,
    decrypt_secret,
    encrypt_secret,
    from_json,
    generate_recovery_codes,
    generate_totp_secret,
    hash_value,
    new_id,
    next_day_iso,
    parse_iso,
    provisioning_uri,
    qr_svg_data_url,
    random_token,
    to_json,
    utcnow_iso,
    verify_totp,
)

def start_execution_run(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    version_id: str | None,
    conversation_id: str | None,
    message_id: str | None,
    job_id: str | None,
    source_type: str,
    queue_name: str | None,
    input_payload: dict[str, Any],
    attempt: int = 1,
    trace_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    run_id = new_id("run")
    trace_id = trace_id or correlation_id or new_id("trace")
    execution_id = new_id("exec")
    now = utcnow_iso()
    execute(
        conn,
        """
        INSERT INTO execution_runs
        (id, organization_id, bot_id, version_id, conversation_id, message_id, job_id, source_type, status, trace_id, execution_id, queue_name, attempt, input_json, output_json, error_json, started_at, finished_at, duration_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, ?, ?, ?, '{}', '{}', ?, NULL, NULL, ?)
        """,
        (
            run_id,
            organization_id,
            bot_id,
            version_id,
            conversation_id,
            message_id,
            job_id,
            source_type,
            trace_id,
            execution_id,
            queue_name,
            attempt,
            to_json(input_payload),
            now,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM execution_runs WHERE id = ?", (run_id,))


def append_technical_log(
    conn,
    *,
    organization_id: str | None,
    bot_id: str | None,
    execution_run_id: str | None,
    conversation_id: str | None,
    level: str,
    category: str,
    message: str,
    trace_id: str | None,
    execution_id: str | None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    log_id = new_id("tlog")
    execute(
        conn,
        """
        INSERT INTO technical_logs
        (id, organization_id, bot_id, execution_run_id, conversation_id, level, category, message, trace_id, execution_id, details_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            log_id,
            organization_id,
            bot_id,
            execution_run_id,
            conversation_id,
            level,
            category,
            message,
            trace_id,
            execution_id,
            to_json(details or {}),
            utcnow_iso(),
        ),
    )
    return fetch_one(conn, "SELECT * FROM technical_logs WHERE id = ?", (log_id,))


def finish_execution_run(
    conn,
    *,
    run_id: str,
    status: str,
    output_payload: dict[str, Any] | None = None,
    error_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = fetch_one(conn, "SELECT * FROM execution_runs WHERE id = ?", (run_id,))
    finished_at = utcnow_iso()
    duration_ms = None
    started = parse_iso(current.get("started_at")) if current else None
    finished = parse_iso(finished_at)
    if started and finished:
        duration_ms = int((finished - started).total_seconds() * 1000)
    execute(
        conn,
        """
        UPDATE execution_runs
        SET status = ?, output_json = ?, error_json = ?, finished_at = ?, duration_ms = ?
        WHERE id = ?
        """,
        (status, to_json(output_payload or {}), to_json(error_payload or {}), finished_at, duration_ms, run_id),
    )
    return fetch_one(conn, "SELECT * FROM execution_runs WHERE id = ?", (run_id,))


def upsert_integration(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    integration_type: str,
    provider: str,
    name: str,
    status: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    existing = fetch_one(
        conn,
        "SELECT * FROM integration_connections WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND integration_type = ? AND provider = ? AND name = ?",
        (organization_id, bot_id, integration_type, provider, name),
    )
    now = utcnow_iso()
    if existing:
        execute(
            conn,
            """
            UPDATE integration_connections
            SET status = ?, config_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, to_json(config), now, existing["id"]),
        )
        return fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (existing["id"],))
    conn_id = new_id("int")
    execute(
        conn,
        """
        INSERT INTO integration_connections
        (id, organization_id, bot_id, integration_type, provider, name, status, health_status, config_json, last_test_at, last_sync_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'unknown', ?, NULL, NULL, ?, ?)
        """,
        (conn_id, organization_id, bot_id, integration_type, provider, name, status, to_json(config), now, now),
    )
    return fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (conn_id,))


def compute_observability_overview(conn, organization_id: str | None = None, bot_id: str | None = None) -> dict[str, Any]:
    where = []
    params: list[Any] = []
    if organization_id:
        where.append("organization_id = ?")
        params.append(organization_id)
    if bot_id:
        where.append("bot_id = ?")
        params.append(bot_id)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    runs = fetch_all(conn, f"SELECT status, duration_ms FROM execution_runs {where_sql} ORDER BY created_at DESC LIMIT 1000", params)
    total = len(runs)
    failed = len([r for r in runs if r.get("status") == "failed"])
    completed = [int(r["duration_ms"]) for r in runs if r.get("duration_ms") is not None]
    completed.sort()

    def percentile(values: list[int], p: float) -> int | None:
        if not values:
            return None
        idx = max(0, min(len(values) - 1, int(round((len(values) - 1) * p))))
        return values[idx]

    recent_failures = fetch_all(
        conn,
        f"SELECT id, status, trace_id, execution_id, created_at, error_json FROM execution_runs {where_sql} {'AND' if where_sql else 'WHERE'} status = 'failed' ORDER BY created_at DESC LIMIT 10",
        params,
    )
    logs = fetch_all(
        conn,
        f"SELECT level, category, message, trace_id, execution_id, created_at FROM technical_logs {where_sql} ORDER BY created_at DESC LIMIT 20",
        params,
    )
    dead_jobs = fetch_one(conn, f"SELECT COUNT(*) AS value FROM automation_jobs {where_sql} {'AND' if where_sql else 'WHERE'} status = 'dead_letter'", params)
    dead_outbox = fetch_one(conn, f"SELECT COUNT(*) AS value FROM outbox_messages {where_sql} {'AND' if where_sql else 'WHERE'} status = 'dead_letter'", params)
    callbacks = fetch_one(conn, f"SELECT COUNT(*) AS value FROM runtime_callbacks {where_sql}", params)
    ai_usage = summarize_ai_usage(conn, organization_id=organization_id, bot_id=bot_id, limit=500)
    circuits = circuit_breaker_summary(conn)
    return {
        "totals": {
            "runs": total,
            "failed_runs": failed,
            "success_rate": round(((total - failed) / total) * 100, 2) if total else None,
            "p95_duration_ms": percentile(completed, 0.95),
            "p99_duration_ms": percentile(completed, 0.99),
            "dead_letter_jobs": int((dead_jobs or {}).get("value") or 0),
            "dead_letter_outbox": int((dead_outbox or {}).get("value") or 0),
            "callbacks": int((callbacks or {}).get("value") or 0),
        },
        "ai": ai_usage,
        "circuits": circuits,
        "recent_failures": recent_failures,
        "recent_logs": logs,
        "dashboards": observability_dashboard_summary(conn, organization_id=organization_id, bot_id=bot_id),
    }


def queue_overview(conn, organization_id: str | None = None) -> dict[str, Any]:
    params: list[Any] = []
    job_where = ""
    outbox_where = ""
    callback_where = ""
    integration_where = ""
    if organization_id:
        job_where = "WHERE organization_id = ?"
        outbox_where = "WHERE organization_id = ?"
        callback_where = "WHERE organization_id = ?"
        integration_where = "WHERE organization_id = ?"
        params = [organization_id]
    jobs = [count_row(row, fallback_kind="automation_jobs") for row in fetch_all(conn, f"SELECT status, COUNT(*) as count FROM automation_jobs {job_where} GROUP BY status", params)]
    outbox = [count_row(row, fallback_kind="outbox") for row in fetch_all(conn, f"SELECT status, COUNT(*) as count FROM outbox_messages {outbox_where} GROUP BY status", params)]
    callbacks = [count_row(row, fallback_kind="callbacks") for row in fetch_all(conn, f"SELECT status, COUNT(*) as count FROM runtime_callbacks {callback_where} GROUP BY status", params)]
    integration_sync = [count_row(row, fallback_kind="integration_sync") for row in fetch_all(conn, f"SELECT COALESCE(status, 'unknown') as status, COUNT(*) as count FROM integration_connections {integration_where} GROUP BY COALESCE(status, 'unknown')", params)]
    return {"automation_jobs": jobs, "outbox": outbox, "callbacks": callbacks, "integration_sync": integration_sync}


def scheduler_overview(conn, organization_id: str | None = None) -> dict[str, Any]:
    params: list[Any] = []
    where = ""
    integration_where = ""
    if organization_id:
        where = "WHERE organization_id = ?"
        integration_where = "WHERE organization_id = ?"
        params = [organization_id]
    counts = [count_row(row, fallback_kind="scheduler") for row in fetch_all(conn, f"SELECT status, COUNT(*) AS count FROM automation_jobs {where} GROUP BY status", params)]
    due_where = (where + (" AND " if where else "WHERE ") + "scheduled_for <= ?")
    due = fetch_one(conn, f"SELECT COUNT(*) AS value FROM automation_jobs {due_where}", params + [utcnow_iso()])
    next_job = fetch_one(conn, f"SELECT id, scheduled_for, status FROM automation_jobs {where} ORDER BY scheduled_for ASC LIMIT 1", params)
    stale_where = where + (" AND " if where else "WHERE ") + "status = 'running' AND locked_at IS NOT NULL"
    stale_locks = fetch_one(conn, f"SELECT COUNT(*) AS value FROM automation_jobs {stale_where}", params)
    integration_due_where = integration_where + ((" AND " if integration_where else "WHERE ") + "auto_sync_enabled = 1 AND COALESCE(status,'configured') IN ('active','configured') AND COALESCE(next_sync_at,'') != '' AND next_sync_at <= ?")
    integration_due = fetch_one(conn, f"SELECT COUNT(*) AS value FROM integration_connections {integration_due_where}", params + [utcnow_iso()])
    next_integration = fetch_one(conn, f"SELECT id, provider, next_sync_at, status FROM integration_connections {integration_where} ORDER BY CASE WHEN next_sync_at IS NULL OR next_sync_at = '' THEN 1 ELSE 0 END, next_sync_at ASC LIMIT 1", params)
    retrying_where = integration_where + ((" AND " if integration_where else "WHERE ") + "retry_count > 0")
    integration_retries = fetch_one(conn, f"SELECT COUNT(*) AS value FROM integration_connections {retrying_where}", params)
    return {
        "counts": counts,
        "due_now": int((due or {}).get("value") or 0),
        "next_job": next_job,
        "stale_locks": int((stale_locks or {}).get("value") or 0),
        "integration_due_now": int((integration_due or {}).get("value") or 0),
        "next_integration": next_integration,
        "integration_retries": int((integration_retries or {}).get("value") or 0),
    }


def materialize_daily_metrics(conn, *, organization_id: str, bot_id: str | None = None, day: str | None = None) -> dict[str, Any]:
    day = day or utcnow_iso()[:10]
    start = f"{day}T00:00:00Z"
    end = next_day_iso(day)
    params: list[Any] = [organization_id]
    bot_clause = ""
    if bot_id:
        bot_clause = " AND bot_id = ?"
        params.append(bot_id)
    msg_in = fetch_one(conn, f"SELECT COUNT(*) AS value FROM messages WHERE organization_id = ?{bot_clause} AND direction = 'inbound' AND created_at >= ? AND created_at < ?", params + [start, end])
    msg_out = fetch_one(conn, f"SELECT COUNT(*) AS value FROM messages WHERE organization_id = ?{bot_clause} AND direction = 'outbound' AND created_at >= ? AND created_at < ?", params + [start, end])
    runs = fetch_one(conn, f"SELECT COUNT(*) AS value FROM execution_runs WHERE organization_id = ?{bot_clause} AND created_at >= ? AND created_at < ?", params + [start, end])
    failures = fetch_one(conn, f"SELECT COUNT(*) AS value FROM execution_runs WHERE organization_id = ?{bot_clause} AND status = 'failed' AND created_at >= ? AND created_at < ?", params + [start, end])
    metrics = {
        "day": day,
        "window": {"start": start, "end": end},
        "inbound_messages": int((msg_in or {}).get("value") or 0),
        "outbound_messages": int((msg_out or {}).get("value") or 0),
        "runs": int((runs or {}).get("value") or 0),
        "failed_runs": int((failures or {}).get("value") or 0),
    }
    existing = fetch_one(conn, "SELECT * FROM metrics_daily WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND day = ?", (organization_id, bot_id, day))
    if existing:
        execute(conn, "UPDATE metrics_daily SET metrics_json = ?, created_at = ? WHERE id = ?", (to_json(metrics), utcnow_iso(), existing["id"]))
        return {**fetch_one(conn, "SELECT * FROM metrics_daily WHERE id = ?", (existing["id"],)), "metrics": metrics}
    row_id = new_id("md")
    execute(conn, "INSERT INTO metrics_daily (id, organization_id, bot_id, day, metrics_json, created_at) VALUES (?, ?, ?, ?, ?, ?)", (row_id, organization_id, bot_id, day, to_json(metrics), utcnow_iso()))
    return {**fetch_one(conn, "SELECT * FROM metrics_daily WHERE id = ?", (row_id,)), "metrics": metrics}


def create_runtime_callback(conn, *, organization_id: str | None, bot_id: str | None, execution_run_id: str | None, callback_type: str, target: str, status: str, payload: dict[str, Any], response: dict[str, Any] | None = None, last_error: str | None = None) -> dict[str, Any]:
    callback_id = new_id("cb")
    delivered_at = utcnow_iso() if status == 'delivered' else None
    execute(conn, "INSERT INTO runtime_callbacks (id, organization_id, bot_id, execution_run_id, callback_type, target, status, payload_json, response_json, last_error, created_at, delivered_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (callback_id, organization_id, bot_id, execution_run_id, callback_type, target, status, to_json(payload), to_json(response or {}), last_error, utcnow_iso(), delivered_at))
    row = fetch_one(conn, "SELECT * FROM runtime_callbacks WHERE id = ?", (callback_id,))
    return {**row, "payload": from_json(row.get("payload_json"), {}), "response": from_json(row.get("response_json"), {})}


def list_runtime_callbacks(conn, *, organization_id: str, bot_id: str | None = None) -> list[dict[str, Any]]:
    if bot_id:
        rows = fetch_all(conn, "SELECT * FROM runtime_callbacks WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT 100", (organization_id, bot_id))
    else:
        rows = fetch_all(conn, "SELECT * FROM runtime_callbacks WHERE organization_id = ? ORDER BY created_at DESC LIMIT 100", (organization_id,))
    return [runtime_callback_row(row) for row in rows]


def create_integration_sync_run(conn, *, organization_id: str, integration_id: str, bot_id: str | None, direction: str, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    sync_id = new_id("sync")
    now = utcnow_iso()
    execute(conn, "INSERT INTO integration_sync_runs (id, organization_id, integration_id, bot_id, status, direction, summary_json, error_json, started_at, finished_at, created_at) VALUES (?, ?, ?, ?, 'running', ?, ?, '{}', ?, NULL, ?)", (sync_id, organization_id, integration_id, bot_id, direction, to_json(summary or {}), now, now))
    return fetch_one(conn, "SELECT * FROM integration_sync_runs WHERE id = ?", (sync_id,))


def finish_integration_sync_run(conn, *, sync_id: str, status: str, summary: dict[str, Any] | None = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    execute(conn, "UPDATE integration_sync_runs SET status = ?, summary_json = ?, error_json = ?, finished_at = ? WHERE id = ?", (status, to_json(summary or {}), to_json(error or {}), utcnow_iso(), sync_id))
    return fetch_one(conn, "SELECT * FROM integration_sync_runs WHERE id = ?", (sync_id,))


def list_integration_sync_runs(conn, *, organization_id: str, integration_id: str | None = None) -> list[dict[str, Any]]:
    if integration_id:
        rows = fetch_all(conn, "SELECT * FROM integration_sync_runs WHERE organization_id = ? AND integration_id = ? ORDER BY created_at DESC LIMIT 50", (organization_id, integration_id))
    else:
        rows = fetch_all(conn, "SELECT * FROM integration_sync_runs WHERE organization_id = ? ORDER BY created_at DESC LIMIT 50", (organization_id,))
    return [integration_sync_run_row(row) for row in rows]
