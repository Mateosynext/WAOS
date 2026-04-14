from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import execute, fetch_all, fetch_one, get_connection, init_db  # noqa: E402
from app.job_idempotency import begin_job_execution, mark_job_completed, mark_job_failed  # noqa: E402
from app.platform import append_technical_log, create_integration_sync_run, create_runtime_callback, finish_execution_run, finish_integration_sync_run, start_execution_run  # noqa: E402
from app.repositories import create_audit_log, create_message, get_bot, get_conversation, publish_version  # noqa: E402
from app.integrations_runtime import sync_google_calendar  # noqa: E402
from app.payments_runtime import reconcile_pending_provider_payments  # noqa: E402
from app.utils import RetryableProviderError, add_minutes, add_seconds, from_json, new_id, parse_iso, to_json, utcnow_iso  # noqa: E402
from app.whatsapp import send_whatsapp_message, send_whatsapp_text  # noqa: E402
from app.v8 import generate_executive_report  # noqa: E402

POLL_SECONDS = int(os.getenv("WORKER_POLL_SECONDS", "5"))
JOB_BATCH_SIZE = int(os.getenv("WORKER_BATCH_SIZE", "50"))




def _claim_due_records(conn, *, table: str, statuses: tuple[str, ...], batch_size: int, extra_where: str = "", lock_minutes: int = 5) -> list[dict]:
    now = utcnow_iso()
    stale_lock = add_minutes(now, -lock_minutes)
    placeholders = ",".join("?" for _ in statuses)
    rows = fetch_all(
        conn,
        f"""
        SELECT id FROM {table}
        WHERE status IN ({placeholders}) AND scheduled_for <= ? AND (locked_at IS NULL OR locked_at <= ?) {extra_where}
        ORDER BY priority DESC, scheduled_for ASC
        LIMIT ?
        """,
        [*statuses, now, stale_lock, batch_size],
    )
    claimed: list[dict] = []
    for row in rows:
        result = conn.execute(
            f"UPDATE {table} SET locked_at = ?, status = CASE WHEN status = 'queued' THEN 'running' ELSE status END WHERE id = ? AND (locked_at IS NULL OR locked_at <= ?)",
            (now, row["id"], stale_lock),
        )
        if getattr(result, "rowcount", 0):
            claimed_row = fetch_one(conn, f"SELECT * FROM {table} WHERE id = ?", (row["id"],))
            if claimed_row:
                claimed.append(claimed_row)
    return claimed

def _claim_due_integrations(conn, *, batch_size: int, lock_minutes: int = 5) -> list[dict]:
    now = utcnow_iso()
    stale_lock = add_minutes(now, -lock_minutes)
    rows = fetch_all(
        conn,
        """
        SELECT id FROM integration_connections
        WHERE auto_sync_enabled = 1
          AND status IN ('active', 'configured')
          AND next_sync_at IS NOT NULL
          AND next_sync_at <= ?
          AND (locked_at IS NULL OR locked_at <= ?)
        ORDER BY next_sync_at ASC
        LIMIT ?
        """,
        (now, stale_lock, batch_size),
    )
    claimed: list[dict] = []
    for row in rows:
        result = conn.execute(
            "UPDATE integration_connections SET locked_at = ? WHERE id = ? AND (locked_at IS NULL OR locked_at <= ?)",
            (now, row['id'], stale_lock),
        )
        if getattr(result, 'rowcount', 0):
            claimed_row = fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (row['id'],))
            if claimed_row:
                claimed.append(claimed_row)
    return claimed


def _integration_retry_schedule(attempts: int, frequency_minutes: int) -> str:
    backoff = min(180, max(frequency_minutes, 5) * max(1, min(attempts, 6)))
    return add_minutes(utcnow_iso(), backoff)


def process_due_integrations() -> list[dict]:
    processed: list[dict] = []
    with get_connection() as conn:
        rows = _claim_due_integrations(conn, batch_size=JOB_BATCH_SIZE)
        for row in rows:
            config = from_json(row.get('config_json'), {})
            frequency_minutes = max(5, int(row.get('sync_frequency_minutes') or config.get('sync_frequency_minutes') or 30))
            sync_run = create_integration_sync_run(
                conn,
                organization_id=row['organization_id'],
                integration_id=row['id'],
                bot_id=row.get('bot_id'),
                direction='auto',
                summary={'provider': row.get('provider'), 'mode': 'worker_auto_sync'},
            )
            try:
                if row.get('provider') == 'google_calendar':
                    summary = sync_google_calendar(conn, {**row, 'config': config})
                elif row.get('provider') == 'stripe':
                    summary = reconcile_pending_provider_payments(conn, integration={**row, 'config': config}, limit=50)
                else:
                    summary = {'provider': row.get('provider'), 'mode': 'noop', 'reason': 'worker_auto_sync_not_supported'}
                finish_integration_sync_run(conn, sync_id=sync_run['id'], status='completed', summary=summary)
                execute(
                    conn,
                    "UPDATE integration_connections SET health_status = ?, credential_status = CASE WHEN provider = 'google_calendar' THEN 'connected' ELSE credential_status END, last_error = NULL, last_sync_at = ?, last_success_at = ?, retry_count = 0, next_sync_at = ?, locked_at = NULL, updated_at = ? WHERE id = ?",
                    (
                        'healthy' if not (summary.get('errors') or []) else 'degraded',
                        utcnow_iso(),
                        utcnow_iso(),
                        add_minutes(utcnow_iso(), frequency_minutes),
                        utcnow_iso(),
                        row['id'],
                    ),
                )
                create_runtime_callback(
                    conn,
                    organization_id=row['organization_id'],
                    bot_id=row.get('bot_id'),
                    execution_run_id=None,
                    callback_type='integration.synced',
                    target=f"provider://{row.get('provider') or 'integration'}",
                    status='delivered',
                    payload={'integration_id': row['id'], 'provider': row.get('provider')},
                    response=summary,
                )
                processed.append({'id': row['id'], 'status': 'completed', 'provider': row.get('provider')})
            except Exception as exc:
                attempts = int(row.get('retry_count') or 0) + 1
                next_sync_at = _integration_retry_schedule(attempts, frequency_minutes)
                finish_integration_sync_run(conn, sync_id=sync_run['id'], status='failed', summary={}, error={'error': str(exc)})
                execute(
                    conn,
                    "UPDATE integration_connections SET health_status = 'degraded', last_error = ?, retry_count = ?, next_sync_at = ?, locked_at = NULL, updated_at = ? WHERE id = ?",
                    (str(exc), attempts, next_sync_at, utcnow_iso(), row['id']),
                )
                create_runtime_callback(
                    conn,
                    organization_id=row['organization_id'],
                    bot_id=row.get('bot_id'),
                    execution_run_id=None,
                    callback_type='integration.sync_failed',
                    target=f"provider://{row.get('provider') or 'integration'}",
                    status='retry',
                    payload={'integration_id': row['id'], 'provider': row.get('provider')},
                    response={},
                    last_error=str(exc),
                )
                processed.append({'id': row['id'], 'status': 'retry', 'provider': row.get('provider'), 'error': str(exc)})
    return processed


def _job_max_attempts(job: dict) -> int:
    payload = json.loads(job.get("payload_json") or "{}")
    return int(payload.get("max_attempts") or 3)


def process_due_jobs() -> list[dict]:
    processed: list[dict] = []
    with get_connection() as conn:
        jobs = _claim_due_records(conn, table="automation_jobs", statuses=("queued", "retry"), batch_size=JOB_BATCH_SIZE)
        for job in jobs:
            conversation = get_conversation(conn, job["conversation_id"]) if job.get("conversation_id") else None
            bot = get_bot(conn, job["bot_id"])
            run = start_execution_run(
                conn,
                organization_id=job["organization_id"],
                bot_id=job["bot_id"],
                version_id=bot.get("published_version_id") if bot else None,
                conversation_id=job.get("conversation_id"),
                message_id=None,
                job_id=job["id"],
                source_type="automation_job",
                queue_name="runtime.jobs",
                input_payload={"job": job},
                attempt=int(job.get("attempts") or 0) + 1,
            )
            payload = json.loads(job.get("payload_json") or "{}")
            max_attempts = _job_max_attempts(job)
            dedupe_key = job.get("dedupe_key") or f"automation:{job["id"]}"
            execution = begin_job_execution(conn, job_type=job.get("job_type") or "automation", dedupe_key=dedupe_key, payload=payload)
            if execution.get("status") == "completed":
                execute(conn, "UPDATE automation_jobs SET status = 'executed', locked_at = NULL, last_error = NULL WHERE id = ?", (job["id"],))
                processed.append({"id": job["id"], "status": "duplicate_skipped"})
                continue
            try:
                if not conversation or int(conversation.get("human_takeover", 0)) == 1:
                    execute(
                        conn,
                        "UPDATE automation_jobs SET status = 'skipped', attempts = attempts + 1, executed_at = ?, last_error = ? WHERE id = ?",
                        (utcnow_iso(), "human_takeover_or_missing_conversation", job["id"]),
                    )
                    append_technical_log(conn, organization_id=job["organization_id"], bot_id=job["bot_id"], execution_run_id=run["id"], conversation_id=job.get("conversation_id"), level="warning", category="worker", message="Job skipped", trace_id=run["trace_id"], execution_id=run["execution_id"], details={"reason": "human_takeover_or_missing_conversation"})
                    finish_execution_run(conn, run_id=run["id"], status="completed", output_payload={"status": "skipped"})
                    processed.append({"id": job["id"], "status": "skipped"})
                    continue
                if payload.get("simulate_fail"):
                    raise RuntimeError("simulated_job_failure")
                body = payload.get("message_template") or "Solo dando seguimiento a tu consulta."
                message = create_message(
                    conn,
                    organization_id=job["organization_id"],
                    conversation_id=job["conversation_id"],
                    contact_id=job.get("contact_id"),
                    bot_id=job["bot_id"],
                    direction="outbound",
                    kind="text",
                    source="worker",
                    body=body,
                    status="queued",
                    metadata={"automation_job_id": job["id"], "trace_id": run["trace_id"], "execution_id": run["execution_id"]},
                )
                execute(
                    conn,
                    """
                    INSERT INTO outbox_messages
                    (id, organization_id, bot_id, execution_run_id, conversation_id, channel, payload_json, status, attempts, last_error, scheduled_for, sent_at, created_at, provider_response_json, priority)
                    VALUES (?, ?, ?, ?, ?, 'whatsapp', ?, 'queued', 0, NULL, ?, NULL, ?, '{}', ?)
                    """,
                    (new_id("out"), job["organization_id"], job["bot_id"], run["id"], job.get("conversation_id"), to_json({"body": body, "message_id": message["id"], "contact_id": job.get("contact_id"), "simulate_fail": bool(payload.get("simulate_outbox_fail"))}), utcnow_iso(), utcnow_iso(), int(job.get("priority") or 50)),
                )
                execute(conn, "UPDATE automation_jobs SET status = 'executed', attempts = attempts + 1, executed_at = ?, last_error = NULL WHERE id = ?", (utcnow_iso(), job["id"]))
                append_technical_log(conn, organization_id=job["organization_id"], bot_id=job["bot_id"], execution_run_id=run["id"], conversation_id=job.get("conversation_id"), level="info", category="worker", message="Automation job executed", trace_id=run["trace_id"], execution_id=run["execution_id"], details={"job_id": job["id"], "message_id": message["id"]})
                create_runtime_callback(conn, organization_id=job["organization_id"], bot_id=job["bot_id"], execution_run_id=run["id"], callback_type="job.executed", target="api://runtime/jobs", status="delivered", payload={"job_id": job["id"], "message_id": message["id"]}, response={"accepted": True})
                mark_job_completed(conn, dedupe_key=dedupe_key, result={"message_id": message["id"], "job_id": job["id"]})
                finish_execution_run(conn, run_id=run["id"], status="completed", output_payload={"status": "executed", "message_id": message["id"]})
                processed.append({"id": job["id"], "status": "executed"})
            except Exception as exc:
                attempts = int(job.get("attempts") or 0) + 1
                status = "dead_letter" if attempts >= max_attempts else "retry"
                next_schedule = utcnow_iso() if status == "dead_letter" else add_minutes(utcnow_iso(), min(15, attempts * 2))
                execute(conn, "UPDATE automation_jobs SET status = ?, attempts = ?, last_error = ?, scheduled_for = ? WHERE id = ?", (status, attempts, str(exc), next_schedule, job["id"]))
                append_technical_log(conn, organization_id=job["organization_id"], bot_id=job["bot_id"], execution_run_id=run["id"], conversation_id=job.get("conversation_id"), level="error", category="worker", message="Automation job failed", trace_id=run["trace_id"], execution_id=run["execution_id"], details={"job_id": job["id"], "error": str(exc), "status": status})
                create_runtime_callback(conn, organization_id=job["organization_id"], bot_id=job["bot_id"], execution_run_id=run["id"], callback_type="job.failed", target="api://runtime/jobs", status="failed" if status == "dead_letter" else "retry", payload={"job_id": job["id"], "status": status}, response={}, last_error=str(exc))
                mark_job_failed(conn, dedupe_key=dedupe_key, error_text=str(exc))
                finish_execution_run(conn, run_id=run["id"], status="failed", error_payload={"error": str(exc), "retry_status": status})
                processed.append({"id": job["id"], "status": status})
    return processed


def _get_actor_user(conn, user_id: str | None = None) -> dict:
    if user_id:
        user = fetch_one(conn, "SELECT * FROM users WHERE id = ?", (user_id,))
        if user:
            return user
    user = fetch_one(conn, "SELECT * FROM users ORDER BY created_at ASC LIMIT 1")
    if user:
        return user
    return {"id": "system"}


def _create_notification(conn, *, organization_id: str, bot_id: str | None = None, user_id: str | None = None, conversation_id: str | None = None, category: str, title: str, body: str, severity: str = "info", channel: str = "in_app", metadata: dict | None = None) -> None:
    execute(
        conn,
        """
        INSERT INTO operator_notifications
        (id, organization_id, bot_id, user_id, conversation_id, category, channel, title, body, severity, status, metadata_json, created_at, read_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unread', ?, ?, NULL)
        """,
        (new_id("ntf"), organization_id, bot_id, user_id, conversation_id, category, channel, title, body, severity, to_json(metadata or {}), utcnow_iso()),
    )


def _next_schedule_at(current_value: str | None, frequency: str) -> str:
    base = parse_iso(current_value) or parse_iso(utcnow_iso())
    if frequency == "daily":
        delta = dt.timedelta(days=1)
    elif frequency == "monthly":
        delta = dt.timedelta(days=30)
    else:
        delta = dt.timedelta(days=7)
    return (base + delta).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _window_bounds(end_value: str | None, frequency: str) -> tuple[str, str]:
    end_dt = parse_iso(end_value) or parse_iso(utcnow_iso())
    if frequency == "daily":
        delta = dt.timedelta(days=1)
    elif frequency == "monthly":
        delta = dt.timedelta(days=30)
    else:
        delta = dt.timedelta(days=7)
    start_dt = end_dt - delta
    return (
        start_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        end_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )


def _compare_value(observed: float, comparator: str, threshold: float) -> bool:
    if comparator == ">":
        return observed > threshold
    if comparator == ">=":
        return observed >= threshold
    if comparator == "<":
        return observed < threshold
    if comparator == "<=":
        return observed <= threshold
    return False


def _metric_handoff_rate(conn, organization_id: str, bot_id: str | None, window_minutes: int) -> tuple[float, dict]:
    cutoff = add_minutes(utcnow_iso(), -window_minutes)
    params = [organization_id, cutoff]
    bot_sql = ""
    if bot_id:
        bot_sql = " AND bot_id = ?"
        params.append(bot_id)
    rows = fetch_all(conn, f"SELECT human_takeover FROM conversations WHERE organization_id = ? AND updated_at >= ?{bot_sql}", params)
    total = len(rows)
    handoffs = sum(1 for row in rows if int(row.get("human_takeover") or 0) == 1)
    value = round((handoffs / total) * 100, 2) if total else 0.0
    return value, {"total_conversations": total, "handoffs": handoffs}


def _metric_unanswered_risk(conn, organization_id: str, bot_id: str | None, window_minutes: int, config: dict) -> tuple[float, dict]:
    stale_hours = int(config.get("stale_hours") or 4)
    stale_cutoff = add_minutes(utcnow_iso(), -(stale_hours * 60))
    params = [organization_id, stale_cutoff]
    bot_sql = ""
    if bot_id:
        bot_sql = " AND bot_id = ?"
        params.append(bot_id)
    rows = fetch_all(conn, f"SELECT id FROM conversations WHERE organization_id = ? AND ai_active = 1 AND COALESCE(last_message_at, updated_at) <= ?{bot_sql}", params)
    return float(len(rows)), {"stale_cutoff": stale_cutoff, "conversations": len(rows), "window_minutes": window_minutes}


def _metric_bookings_drop(conn, organization_id: str, bot_id: str | None, window_minutes: int) -> tuple[float, dict]:
    current_start = add_minutes(utcnow_iso(), -window_minutes)
    previous_start = add_minutes(current_start, -window_minutes)
    params_current = [organization_id, current_start, utcnow_iso()]
    params_previous = [organization_id, previous_start, current_start]
    bot_sql = ""
    if bot_id:
        bot_sql = " AND bot_id = ?"
        params_current.append(bot_id)
        params_previous.append(bot_id)
    current = fetch_one(conn, f"SELECT COUNT(*) AS total FROM appointments WHERE organization_id = ? AND created_at >= ? AND created_at < ?{bot_sql}", params_current)
    previous = fetch_one(conn, f"SELECT COUNT(*) AS total FROM appointments WHERE organization_id = ? AND created_at >= ? AND created_at < ?{bot_sql}", params_previous)
    current_total = int((current or {}).get("total") or 0)
    previous_total = int((previous or {}).get("total") or 0)
    value = round(((previous_total - current_total) / previous_total) * 100, 2) if previous_total else 0.0
    return value, {"current": current_total, "previous": previous_total}


def _metric_close_probability_drop(conn, organization_id: str, bot_id: str | None, window_minutes: int) -> tuple[float, dict]:
    current_start = add_minutes(utcnow_iso(), -window_minutes)
    previous_start = add_minutes(current_start, -window_minutes)
    params_current = [organization_id, current_start]
    params_previous = [organization_id, previous_start, current_start]
    bot_sql = ""
    if bot_id:
        bot_sql = " AND bot_id = ?"
        params_current.append(bot_id)
        params_previous.append(bot_id)
    current = fetch_one(conn, f"SELECT AVG(lead_score) AS avg_score, COUNT(*) AS total FROM contact_memory WHERE organization_id = ? AND last_updated_at >= ?{bot_sql}", params_current)
    previous = fetch_one(conn, f"SELECT AVG(lead_score) AS avg_score, COUNT(*) AS total FROM contact_memory WHERE organization_id = ? AND last_updated_at >= ? AND last_updated_at < ?{bot_sql}", params_previous)
    current_avg = float((current or {}).get("avg_score") or 0.0)
    previous_avg = float((previous or {}).get("avg_score") or 0.0)
    value = round(((previous_avg - current_avg) / previous_avg) * 100, 2) if previous_avg else 0.0
    return value, {"current_avg": current_avg, "previous_avg": previous_avg, "current_total": int((current or {}).get("total") or 0), "previous_total": int((previous or {}).get("total") or 0)}


def _compute_alert_metric(conn, rule: dict) -> tuple[float, dict]:
    config = from_json(rule.get("config_json"), {})
    metric_key = rule.get("metric_key")
    window_minutes = int(rule.get("window_minutes") or 60)
    if metric_key == "handoff_rate":
        return _metric_handoff_rate(conn, rule["organization_id"], rule.get("bot_id"), window_minutes)
    if metric_key == "unanswered_risk":
        return _metric_unanswered_risk(conn, rule["organization_id"], rule.get("bot_id"), window_minutes, config)
    if metric_key == "bookings_drop":
        return _metric_bookings_drop(conn, rule["organization_id"], rule.get("bot_id"), window_minutes)
    return _metric_close_probability_drop(conn, rule["organization_id"], rule.get("bot_id"), window_minutes)


def process_report_schedules() -> list[dict]:
    processed: list[dict] = []
    with get_connection() as conn:
        rows = fetch_all(conn, "SELECT * FROM report_schedules WHERE status = 'active' AND next_run_at <= ? ORDER BY next_run_at ASC LIMIT ?", (utcnow_iso(), JOB_BATCH_SIZE))
        for schedule in rows:
            try:
                period_start, period_end = _window_bounds(schedule.get("next_run_at"), schedule.get("frequency") or "weekly")
                report = generate_executive_report(conn, organization_id=schedule["organization_id"], period_start=period_start, period_end=period_end, bot_id=schedule.get("bot_id"), delivery_channels=from_json(schedule.get("delivery_channels_json"), []))
                run_id = new_id("rsrun")
                execute(conn, "INSERT INTO report_schedule_runs (id, schedule_id, organization_id, bot_id, report_id, status, run_at, artifact_path, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?)", (run_id, schedule["id"], schedule["organization_id"], schedule.get("bot_id"), report.get("id"), utcnow_iso(), report.get("pdf_path"), to_json({"period_start": period_start, "period_end": period_end, "pdf_filename": report.get("pdf_filename")}), utcnow_iso()))
                execute(conn, "UPDATE report_schedules SET next_run_at = ?, updated_at = ? WHERE id = ?", (_next_schedule_at(schedule.get("next_run_at"), schedule.get("frequency") or "weekly"), utcnow_iso(), schedule["id"]))
                for channel in from_json(schedule.get("delivery_channels_json"), []):
                    _record_delivery_attempt(conn, organization_id=schedule["organization_id"], bot_id=schedule.get("bot_id"), conversation_id=None, entity_type="report_schedule_run", entity_id=run_id, channel=str(channel), target=str(channel), subject=schedule.get("name") or "Reporte programado", body=report.get("pdf_filename") or report.get("id") or "executive_report", status="delivered", provider="waos", metadata={"schedule_id": schedule["id"], "report_id": report.get("id")}, scheduled_at=schedule.get("next_run_at"), delivered_at=utcnow_iso())
                _create_notification(conn, organization_id=schedule["organization_id"], bot_id=schedule.get("bot_id"), category="report", title="Reporte programado generado", body=f"{schedule.get('name')} genero {report.get('pdf_filename') or report.get('id')}.", severity="info", metadata={"schedule_id": schedule["id"], "report_id": report.get("id")})
                processed.append({"id": schedule["id"], "status": "completed", "report_id": report.get("id")})
            except Exception as exc:
                run_id = new_id("rsrun")
                execute(conn, "INSERT INTO report_schedule_runs (id, schedule_id, organization_id, bot_id, report_id, status, run_at, artifact_path, metadata_json, created_at) VALUES (?, ?, ?, ?, NULL, 'failed', ?, NULL, ?, ?)", (run_id, schedule["id"], schedule["organization_id"], schedule.get("bot_id"), utcnow_iso(), to_json({"error": str(exc)}), utcnow_iso()))
                for channel in from_json(schedule.get("delivery_channels_json"), []):
                    _record_delivery_attempt(conn, organization_id=schedule["organization_id"], bot_id=schedule.get("bot_id"), conversation_id=None, entity_type="report_schedule_run", entity_id=run_id, channel=str(channel), target=str(channel), subject=schedule.get("name") or "Reporte programado", body=str(exc), status="failed", provider="waos", metadata={"schedule_id": schedule["id"], "error": str(exc)}, scheduled_at=schedule.get("next_run_at"), delivered_at=None)
                _create_notification(conn, organization_id=schedule["organization_id"], bot_id=schedule.get("bot_id"), category="report", title="Fallo un reporte programado", body=f"{schedule.get('name')} fallo: {exc}", severity="warning", metadata={"schedule_id": schedule["id"]})
                processed.append({"id": schedule["id"], "status": "failed", "error": str(exc)})
    return processed


def process_publish_schedules() -> list[dict]:
    processed: list[dict] = []
    with get_connection() as conn:
        rows = fetch_all(conn, "SELECT * FROM publish_schedules WHERE status = 'scheduled' AND scheduled_for <= ? ORDER BY scheduled_for ASC LIMIT ?", (utcnow_iso(), JOB_BATCH_SIZE))
        for schedule in rows:
            try:
                actor = _get_actor_user(conn, schedule.get("created_by"))
                version_id = schedule.get("version_id")
                if version_id:
                    version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ? AND bot_id = ?", (version_id, schedule["bot_id"]))
                else:
                    version = None
                if version:
                    execute(conn, "UPDATE bots SET published_version_id = ?, current_state = 'published', updated_at = ? WHERE id = ?", (version_id, utcnow_iso(), schedule["bot_id"]))
                    execute(conn, "UPDATE bot_versions SET status = 'published' WHERE id = ?", (version_id,))
                    create_audit_log(conn, organization_id=schedule["organization_id"], actor_user_id=actor.get("id"), actor_type="system", entity_type="bot", entity_id=schedule["bot_id"], action="bot.version_published_scheduled", metadata={"version_id": version_id, "schedule_id": schedule["id"]})
                else:
                    published = publish_version(conn, bot_id=schedule["bot_id"], actor_user=actor, notes=schedule.get("notes") or "Scheduled publish")
                    version_id = published.get("id")
                execute(conn, "UPDATE publish_schedules SET status = 'executed', published_at = ? WHERE id = ?", (utcnow_iso(), schedule["id"]))
                execute(conn, "INSERT INTO publish_schedule_runs (id, schedule_id, organization_id, bot_id, version_id, status, run_at, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, 'completed', ?, ?, ?)", (new_id("psrun"), schedule["id"], schedule["organization_id"], schedule["bot_id"], version_id, utcnow_iso(), to_json({"notes": schedule.get("notes")}), utcnow_iso()))
                _create_notification(conn, organization_id=schedule["organization_id"], bot_id=schedule["bot_id"], category="publish", title="Version publicada automaticamente", body=f"Se publico la version {version_id} para el bot {schedule['bot_id']}.", severity="info", metadata={"schedule_id": schedule["id"], "version_id": version_id})
                processed.append({"id": schedule["id"], "status": "completed", "version_id": version_id})
            except Exception as exc:
                execute(conn, "UPDATE publish_schedules SET status = 'failed', published_at = NULL WHERE id = ?", (schedule["id"],))
                execute(conn, "INSERT INTO publish_schedule_runs (id, schedule_id, organization_id, bot_id, version_id, status, run_at, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, 'failed', ?, ?, ?)", (new_id("psrun"), schedule["id"], schedule["organization_id"], schedule["bot_id"], schedule.get("version_id"), utcnow_iso(), to_json({"error": str(exc)}), utcnow_iso()))
                _create_notification(conn, organization_id=schedule["organization_id"], bot_id=schedule["bot_id"], category="publish", title="Fallo una publicacion programada", body=f"No se pudo publicar {schedule['bot_id']}: {exc}", severity="warning", metadata={"schedule_id": schedule["id"]})
                processed.append({"id": schedule["id"], "status": "failed", "error": str(exc)})
    return processed


def process_alert_rules() -> list[dict]:
    processed: list[dict] = []
    with get_connection() as conn:
        rows = fetch_all(conn, "SELECT * FROM alert_rules_v14 WHERE status = 'active' ORDER BY updated_at DESC LIMIT ?", (JOB_BATCH_SIZE,))
        for rule in rows:
            try:
                observed_value, details = _compute_alert_metric(conn, rule)
                window_end = utcnow_iso()
                window_start = add_minutes(window_end, -int(rule.get("window_minutes") or 60))
                if not _compare_value(observed_value, rule.get("comparator") or ">=", float(rule.get("threshold_value") or 0)):
                    processed.append({"id": rule["id"], "status": "ok", "observed_value": observed_value})
                    continue
                exists = fetch_one(conn, "SELECT id FROM alert_events WHERE rule_id = ? AND created_at >= ? ORDER BY created_at DESC LIMIT 1", (rule["id"], window_start))
                if exists:
                    processed.append({"id": rule["id"], "status": "deduped", "observed_value": observed_value})
                    continue
                event_id = new_id("aevt")
                execute(conn, "INSERT INTO alert_events (id, rule_id, organization_id, bot_id, metric_key, comparator, threshold_value, observed_value, window_started_at, window_ended_at, status, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'triggered', ?, ?)", (event_id, rule["id"], rule["organization_id"], rule.get("bot_id"), rule.get("metric_key"), rule.get("comparator"), rule.get("threshold_value"), observed_value, window_start, window_end, to_json(details), utcnow_iso()))
                for channel in from_json(rule.get("notify_channels_json"), []):
                    _record_delivery_attempt(conn, organization_id=rule["organization_id"], bot_id=rule.get("bot_id"), conversation_id=None, entity_type="alert_event", entity_id=event_id, channel=str(channel), target=str(channel), subject=f"Alerta KPI: {rule.get('name')}", body=f"{rule.get('metric_key')} dio {observed_value} y cruzo {rule.get('comparator')} {rule.get('threshold_value')}.", status="delivered", provider="waos", metadata={"rule_id": rule["id"], "observed_value": observed_value, "details": details}, scheduled_at=window_end, delivered_at=utcnow_iso())
                    _create_notification(conn, organization_id=rule["organization_id"], bot_id=rule.get("bot_id"), category="alert", channel=str(channel), title=f"Alerta KPI: {rule.get('name')}", body=f"{rule.get('metric_key')} dio {observed_value} y cruzo {rule.get('comparator')} {rule.get('threshold_value')}.", severity="warning", metadata={"rule_id": rule["id"], "observed_value": observed_value, "details": details})
                processed.append({"id": rule["id"], "status": "triggered", "observed_value": observed_value})
            except Exception as exc:
                processed.append({"id": rule["id"], "status": "failed", "error": str(exc)})
    return processed


def _record_delivery_attempt(conn, *, organization_id: str, bot_id: str | None, conversation_id: str | None, entity_type: str, entity_id: str, channel: str, target: str | None = None, subject: str = "", body: str = "", status: str = "queued", provider: str | None = None, attempt_number: int = 1, metadata: dict | None = None, scheduled_at: str | None = None, delivered_at: str | None = None) -> str:
    delivery_id = new_id("dlv")
    execute(
        conn,
        """
        INSERT INTO delivery_attempts
        (id, organization_id, bot_id, conversation_id, entity_type, entity_id, channel, target, subject, body, status, provider, attempt_number, metadata_json, scheduled_at, delivered_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (delivery_id, organization_id, bot_id, conversation_id, entity_type, entity_id, channel, target, subject, body, status, provider, attempt_number, to_json(metadata or {}), scheduled_at, delivered_at, utcnow_iso()),
    )
    return delivery_id


def _update_delivery_attempt(conn, delivery_attempt_id: str | None, *, status: str, provider: str | None = None, attempt_number: int | None = None, metadata_patch: dict | None = None, delivered: bool = False) -> None:
    if not delivery_attempt_id:
        return
    row = fetch_one(conn, "SELECT * FROM delivery_attempts WHERE id = ?", (delivery_attempt_id,))
    if not row:
        return
    metadata = from_json(row.get("metadata_json"), {})
    metadata.update(metadata_patch or {})
    execute(
        conn,
        "UPDATE delivery_attempts SET status = ?, provider = ?, attempt_number = ?, metadata_json = ?, delivered_at = ? WHERE id = ?",
        (status, provider or row.get("provider"), attempt_number or row.get("attempt_number") or 1, to_json(metadata), utcnow_iso() if delivered else row.get("delivered_at"), delivery_attempt_id),
    )


def _resolve_delivery_target(conn, row: dict, payload: dict) -> tuple[str | None, str | None, dict | None]:
    message = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (payload.get("message_id"),)) if payload.get("message_id") else None
    conversation = fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (row.get("conversation_id"),)) if row.get("conversation_id") else None
    contact_id = payload.get("contact_id") or (message or {}).get("contact_id") or (conversation or {}).get("contact_id")
    contact = fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", (contact_id,)) if contact_id else None
    return (contact.get("phone") if contact else None, payload.get("message_id"), message)


def _retry_schedule(attempts: int, status_code: int | None = None) -> str:
    jitter_seconds = min(45, attempts * 7)
    if status_code == 429:
        return add_seconds(add_minutes(utcnow_iso(), min(60, attempts * 5)), jitter_seconds)
    if status_code and status_code >= 500:
        return add_seconds(add_minutes(utcnow_iso(), min(30, 2**attempts)), jitter_seconds)
    return add_seconds(utcnow_iso(), min(300, attempts * 30) + jitter_seconds)


def process_outbox() -> list[dict]:
    processed: list[dict] = []
    with get_connection() as conn:
        outbox_rows = _claim_due_records(conn, table="outbox_messages", statuses=("queued", "retry"), batch_size=JOB_BATCH_SIZE)
        for row in outbox_rows:
            payload = json.loads(row.get("payload_json") or "{}")
            attempts = int(row.get("attempts") or 0) + 1
            phone, message_id, message = _resolve_delivery_target(conn, row, payload)
            try:
                if payload.get("simulate_fail"):
                    raise RuntimeError("simulated_outbox_failure")
                if row.get("channel") != "whatsapp":
                    raise RetryableProviderError("unsupported_outbox_channel", retryable=False)
                if not phone:
                    raise RetryableProviderError("missing_contact_phone", retryable=False)
                provider_payload = payload.get("provider_payload")
                delivery_attempt_id = payload.get("delivery_attempt_id")
                if provider_payload:
                    result = send_whatsapp_message(conn, organization_id=row["organization_id"], bot_id=row["bot_id"], phone=phone, payload=provider_payload)
                else:
                    result = send_whatsapp_text(conn, organization_id=row["organization_id"], bot_id=row["bot_id"], phone=phone, body=payload.get("body") or (message or {}).get("body") or "")
                execute(
                    conn,
                    "UPDATE outbox_messages SET status = 'sent', attempts = ?, sent_at = ?, last_error = NULL, provider_message_id = ?, provider_status_code = ?, provider_response_json = ?, next_attempt_at = NULL, locked_at = NULL WHERE id = ?",
                    (attempts, utcnow_iso(), result.get("external_id"), result.get("status_code"), to_json(result.get("response") or {}), row["id"]),
                )
                if message_id:
                    metadata = from_json((message or {}).get("metadata_json"), {})
                    metadata.update({"provider": result.get("provider"), "provider_response": result.get("response")})
                    execute(conn, "UPDATE messages SET status = 'sent', external_id = ?, metadata_json = ? WHERE id = ?", (result.get("external_id"), to_json(metadata), message_id))
                _update_delivery_attempt(conn, delivery_attempt_id, status="delivered", provider=result.get("provider"), attempt_number=attempts, metadata_patch={"external_id": result.get("external_id"), "response": result.get("response")}, delivered=True)
                create_runtime_callback(conn, organization_id=row["organization_id"], bot_id=row["bot_id"], execution_run_id=row.get("execution_run_id"), callback_type="outbox.sent", target="provider://whatsapp", status="delivered", payload={"outbox_id": row["id"], "message_id": message_id}, response=result)
                processed.append({"id": row["id"], "status": "sent", "provider_message_id": result.get("external_id")})
            except RetryableProviderError as exc:
                status = "dead_letter" if (not exc.retryable or attempts >= 5) else "retry"
                next_schedule = utcnow_iso() if status == "dead_letter" else _retry_schedule(attempts, exc.status_code)
                execute(conn, "UPDATE outbox_messages SET status = ?, attempts = ?, last_error = ?, scheduled_for = ?, next_attempt_at = ?, provider_status_code = ?, provider_response_json = ?, locked_at = NULL WHERE id = ?", (status, attempts, str(exc), next_schedule, next_schedule if status == 'retry' else None, exc.status_code, to_json(exc.details), row["id"]))
                if message_id:
                    execute(conn, "UPDATE messages SET status = ? WHERE id = ?", (status, message_id))
                _update_delivery_attempt(conn, delivery_attempt_id, status=status, provider="whatsapp", attempt_number=attempts, metadata_patch={"error": str(exc), "details": exc.details})
                create_runtime_callback(conn, organization_id=row["organization_id"], bot_id=row["bot_id"], execution_run_id=row.get("execution_run_id"), callback_type="outbox.failed", target="provider://whatsapp", status="failed" if status == "dead_letter" else "retry", payload={"outbox_id": row["id"], "status": status}, response=exc.details, last_error=str(exc))
                processed.append({"id": row["id"], "status": status, "error": str(exc)})
            except Exception as exc:
                status = "dead_letter" if attempts >= 5 else "retry"
                next_schedule = utcnow_iso() if status == "dead_letter" else _retry_schedule(attempts)
                execute(conn, "UPDATE outbox_messages SET status = ?, attempts = ?, last_error = ?, scheduled_for = ?, next_attempt_at = ?, provider_response_json = ?, locked_at = NULL WHERE id = ?", (status, attempts, str(exc), next_schedule, next_schedule if status == 'retry' else None, to_json({"error": str(exc)}), row["id"]))
                if message_id:
                    execute(conn, "UPDATE messages SET status = ? WHERE id = ?", (status, message_id))
                _update_delivery_attempt(conn, delivery_attempt_id, status=status, provider="whatsapp", attempt_number=attempts, metadata_patch={"error": str(exc)})
                create_runtime_callback(conn, organization_id=row["organization_id"], bot_id=row["bot_id"], execution_run_id=row.get("execution_run_id"), callback_type="outbox.failed", target="provider://whatsapp", status="failed" if status == "dead_letter" else "retry", payload={"outbox_id": row["id"], "status": status}, response={}, last_error=str(exc))
                processed.append({"id": row["id"], "status": status, "error": str(exc)})
    return processed


def process_report_generation_jobs() -> list[dict]:
    processed: list[dict] = []
    with get_connection() as conn:
        rows = _claim_due_records(conn, table="report_generation_jobs", statuses=("queued", "retry", "running"), batch_size=JOB_BATCH_SIZE)
        for row in rows:
            request_payload = json.loads(row.get("request_json") or "{}")
            dedupe_key = row.get("dedupe_key") or f"report:{row['id']}"
            execution = begin_job_execution(conn, job_type="executive_report", dedupe_key=dedupe_key, payload=request_payload)
            if execution.get("status") == "completed" and row.get("report_id"):
                execute(conn, "UPDATE report_generation_jobs SET status = 'completed', updated_at = ? WHERE id = ?", (utcnow_iso(), row["id"]))
                processed.append({"id": row["id"], "status": "duplicate_skipped", "report_id": row.get("report_id")})
                continue
            try:
                execute(conn, "UPDATE report_generation_jobs SET status = 'running', attempts = attempts + 1, started_at = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), row["id"]))
                report = generate_executive_report(conn, organization_id=request_payload["organization_id"], period_start=request_payload["period_start"], period_end=request_payload["period_end"], bot_id=request_payload.get("bot_id"), delivery_channels=request_payload.get("delivery_channels") or [])
                execute(conn, "UPDATE report_generation_jobs SET status = 'completed', report_id = ?, completed_at = ?, updated_at = ?, last_error = NULL WHERE id = ?", (report.get("id"), utcnow_iso(), utcnow_iso(), row["id"]))
                mark_job_completed(conn, dedupe_key=dedupe_key, result={"report_id": report.get("id")})
                processed.append({"id": row["id"], "status": "completed", "report_id": report.get("id")})
            except Exception as exc:
                attempts = int(row.get("attempts") or 0) + 1
                status = "dead_letter" if attempts >= 3 else "retry"
                scheduled_for = utcnow_iso() if status == "dead_letter" else add_minutes(utcnow_iso(), min(20, attempts * 5))
                execute(conn, "UPDATE report_generation_jobs SET status = ?, last_error = ?, scheduled_for = ?, updated_at = ? WHERE id = ?", (status, str(exc), scheduled_for, utcnow_iso(), row["id"]))
                mark_job_failed(conn, dedupe_key=dedupe_key, error_text=str(exc))
                processed.append({"id": row["id"], "status": status, "error": str(exc)})
    return processed


def run_once() -> dict:
    jobs = process_due_jobs()
    integrations = process_due_integrations()
    reports = process_report_schedules()
    report_jobs = process_report_generation_jobs()
    publishes = process_publish_schedules()
    alerts = process_alert_rules()
    outbox = process_outbox()
    return {"jobs": jobs, "integrations": integrations, "reports": reports, "report_jobs": report_jobs, "publishes": publishes, "alerts": alerts, "outbox": outbox}


def main() -> None:
    init_db()
    mode = os.getenv("WORKER_MODE", "loop")
    if mode == "once":
        print(run_once())
        return
    while True:
        result = run_once()
        if result["jobs"] or result["integrations"] or result["reports"] or result["report_jobs"] or result["publishes"] or result["alerts"] or result["outbox"]:
            print(result)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
