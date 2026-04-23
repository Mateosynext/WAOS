from __future__ import annotations

from collections import defaultdict
from typing import Any

from .apm import apm_overview
from .utils import add_minutes, new_id, parse_iso, to_json, utcnow_iso
from .world_class import execute, fetch_all, fetch_one, from_json, table_exists
from .runtime_schema_guards import assert_schema_ready


DEFAULT_ALERT_RULES = [
    {
        "name": "Queue backlog > 100 for 5m",
        "metric_key": "queue_backlog_messages",
        "comparator": ">",
        "threshold_value": 100,
        "window_minutes": 5,
        "notify_channels": ["pagerduty", "opsgenie"],
        "config": {"min_oldest_age_seconds": 300},
    },
    {
        "name": "Execution error rate > 5% in 10m",
        "metric_key": "execution_error_rate",
        "comparator": ">",
        "threshold_value": 5,
        "window_minutes": 10,
        "notify_channels": ["pagerduty", "opsgenie"],
        "config": {},
    },
    {
        "name": "Pipeline latency P95 > 10s in 10m",
        "metric_key": "pipeline_p95_latency_ms",
        "comparator": ">",
        "threshold_value": 10000,
        "window_minutes": 10,
        "notify_channels": ["pagerduty", "opsgenie"],
        "config": {"stage_name": "pipeline.total"},
    },
]


def ensure_telemetry_schema(conn) -> None:
    assert_schema_ready(
        conn,
        owner="migrations.py / platform_schema_migration.py",
        tables=(
            "pipeline_stage_metrics",
            "queue_depth_samples",
            "alert_rules_v14",
            "alert_events",
        ),
    )


def seed_default_alert_rules(conn) -> int:
    if not table_exists(conn, "organizations") or not table_exists(conn, "alert_rules_v14"):
        return 0
    organizations = fetch_all(conn, "SELECT id FROM organizations")
    created = 0
    now = utcnow_iso()
    for org in organizations:
        for rule in DEFAULT_ALERT_RULES:
            existing = fetch_one(
                conn,
                "SELECT id FROM alert_rules_v14 WHERE organization_id = ? AND name = ? LIMIT 1",
                (org["id"], rule["name"]),
            )
            if existing:
                continue
            execute(
                conn,
                "INSERT INTO alert_rules_v14 (id, organization_id, bot_id, name, metric_key, comparator, threshold_value, window_minutes, notify_channels_json, status, config_json, created_by, created_at, updated_at) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, 'active', ?, NULL, ?, ?)",
                (
                    new_id("arule"),
                    org["id"],
                    rule["name"],
                    rule["metric_key"],
                    rule["comparator"],
                    float(rule["threshold_value"]),
                    int(rule["window_minutes"]),
                    to_json(rule["notify_channels"]),
                    to_json(rule.get("config") or {}),
                    now,
                    now,
                ),
            )
            created += 1
    return created



def record_stage_metric(
    conn,
    *,
    organization_id: str | None,
    bot_id: str | None,
    conversation_id: str | None,
    trace_id: str | None,
    correlation_id: str | None,
    vertical: str | None,
    source_type: str | None,
    stage_name: str,
    duration_ms: int | None,
    status: str = "ok",
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not table_exists(conn, "pipeline_stage_metrics"):
        return {}
    row_id = new_id("stg")
    execute(
        conn,
        "INSERT INTO pipeline_stage_metrics (id, organization_id, bot_id, conversation_id, trace_id, correlation_id, vertical, source_type, stage_name, status, duration_ms, metrics_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row_id,
            organization_id,
            bot_id,
            conversation_id,
            trace_id,
            correlation_id,
            vertical,
            source_type,
            stage_name,
            status,
            duration_ms,
            to_json(metrics or {}),
            utcnow_iso(),
        ),
    )
    return fetch_one(conn, "SELECT * FROM pipeline_stage_metrics WHERE id = ?", (row_id,)) or {}



def record_queue_depth_sample(conn, *, organization_id: str | None, snapshot: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if not table_exists(conn, "queue_depth_samples"):
        return {}
    row_id = new_id("qsample")
    execute(
        conn,
        "INSERT INTO queue_depth_samples (id, organization_id, jobs_depth, outbox_depth, integration_depth, callbacks_depth, total_depth, oldest_age_seconds, sampled_at, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row_id,
            organization_id,
            int(snapshot.get("jobs_queued") or 0),
            int(snapshot.get("outbox_queued") or 0),
            int(snapshot.get("integrations_due") or 0),
            int(snapshot.get("callbacks_pending") or 0),
            int(snapshot.get("queue_pressure") or 0),
            int(snapshot.get("oldest_age_seconds") or 0),
            utcnow_iso(),
            to_json(metadata or {}),
            utcnow_iso(),
        ),
    )
    return fetch_one(conn, "SELECT * FROM queue_depth_samples WHERE id = ?", (row_id,)) or {}



def _percentile(values: list[int | float], ratio: float) -> int | None:
    clean = sorted(int(value) for value in values if value is not None)
    if not clean:
        return None
    position = max(0, min(len(clean) - 1, int(round((len(clean) - 1) * ratio))))
    return clean[position]



def _window_cutoff(minutes: int) -> str:
    return add_minutes(utcnow_iso(), -minutes)



def pipeline_latency_dashboard(conn, *, organization_id: str | None = None, bot_id: str | None = None, minutes: int = 60) -> dict[str, Any]:
    if not table_exists(conn, "pipeline_stage_metrics"):
        return {"window_minutes": minutes, "stages": []}
    where: list[str] = ["created_at >= ?"]
    params: list[Any] = [_window_cutoff(minutes)]
    if organization_id:
        where.append("organization_id = ?")
        params.append(organization_id)
    if bot_id:
        where.append("bot_id = ?")
        params.append(bot_id)
    rows = fetch_all(
        conn,
        f"SELECT stage_name, duration_ms, status FROM pipeline_stage_metrics WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT 5000",
        tuple(params),
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("stage_name") or "unknown")].append(row)
    stages = []
    for stage_name, stage_rows in sorted(grouped.items()):
        durations = [int(row.get("duration_ms") or 0) for row in stage_rows if row.get("duration_ms") is not None]
        errors = sum(1 for row in stage_rows if str(row.get("status") or "ok") != "ok")
        stages.append(
            {
                "stage_name": stage_name,
                "count": len(stage_rows),
                "p50_ms": _percentile(durations, 0.50),
                "p95_ms": _percentile(durations, 0.95),
                "p99_ms": _percentile(durations, 0.99),
                "error_rate_pct": round((errors / len(stage_rows)) * 100, 2) if stage_rows else 0.0,
            }
        )
    return {"window_minutes": minutes, "stages": stages}



def error_rate_dashboard(conn, *, organization_id: str | None = None, bot_id: str | None = None, hours: int = 24) -> dict[str, Any]:
    if not table_exists(conn, "execution_runs"):
        return {"window_hours": hours, "by_hour": []}
    where: list[str] = ["er.created_at >= ?"]
    params: list[Any] = [add_minutes(utcnow_iso(), -(hours * 60))]
    if organization_id:
        where.append("er.organization_id = ?")
        params.append(organization_id)
    if bot_id:
        where.append("er.bot_id = ?")
        params.append(bot_id)
    rows = fetch_all(
        conn,
        f"""
        SELECT er.status, er.created_at, er.bot_id, COALESCE(b.vertical, 'unknown') AS vertical
        FROM execution_runs er
        LEFT JOIN bots b ON b.id = er.bot_id
        WHERE {' AND '.join(where)}
        ORDER BY er.created_at DESC
        LIMIT 5000
        """,
        tuple(params),
    )
    buckets: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        hour = str(row.get("created_at") or "")[:13] + ":00:00Z"
        key = (str(row.get("vertical") or "unknown"), str(row.get("bot_id") or "unknown"), hour)
        bucket = buckets.setdefault(key, {"vertical": key[0], "bot_id": key[1], "hour": key[2], "runs": 0, "errors": 0})
        bucket["runs"] += 1
        if str(row.get("status") or "") == "failed":
            bucket["errors"] += 1
    by_hour = []
    for bucket in sorted(buckets.values(), key=lambda item: (item["hour"], item["vertical"], item["bot_id"])):
        bucket["error_rate_pct"] = round((bucket["errors"] / bucket["runs"]) * 100, 2) if bucket["runs"] else 0.0
        by_hour.append(bucket)
    return {"window_hours": hours, "by_hour": by_hour}



def queue_depth_dashboard(conn, *, organization_id: str | None = None, minutes: int = 60) -> dict[str, Any]:
    if not table_exists(conn, "queue_depth_samples"):
        return {"window_minutes": minutes, "samples": []}
    where = ["sampled_at >= ?"]
    params: list[Any] = [_window_cutoff(minutes)]
    if organization_id:
        where.append("organization_id = ?")
        params.append(organization_id)
    rows = fetch_all(
        conn,
        f"SELECT * FROM queue_depth_samples WHERE {' AND '.join(where)} ORDER BY sampled_at DESC LIMIT 500",
        tuple(params),
    )
    samples = [
        {
            "sampled_at": row.get("sampled_at"),
            "jobs_depth": int(row.get("jobs_depth") or 0),
            "outbox_depth": int(row.get("outbox_depth") or 0),
            "integration_depth": int(row.get("integration_depth") or 0),
            "callbacks_depth": int(row.get("callbacks_depth") or 0),
            "total_depth": int(row.get("total_depth") or 0),
            "oldest_age_seconds": int(row.get("oldest_age_seconds") or 0),
        }
        for row in rows
    ]
    latest = samples[0] if samples else None
    return {"window_minutes": minutes, "latest": latest, "samples": samples[::-1]}



def ai_cost_dashboard(conn, *, organization_id: str | None = None, bot_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    if not table_exists(conn, "ai_usage_events"):
        return {"conversations": []}
    where: list[str] = []
    params: list[Any] = []
    if organization_id:
        where.append("organization_id = ?")
        params.append(organization_id)
    if bot_id:
        where.append("bot_id = ?")
        params.append(bot_id)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    rows = fetch_all(
        conn,
        f"SELECT conversation_id, model, operation, estimated_cost, total_tokens, created_at FROM ai_usage_events {where_sql} ORDER BY created_at DESC LIMIT ?",
        tuple([*params, limit * 20]),
    )
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        conversation_id = str(row.get("conversation_id") or "unknown")
        bucket = grouped.setdefault(conversation_id, {"conversation_id": conversation_id, "events": 0, "estimated_cost": 0.0, "total_tokens": 0, "models": {}})
        bucket["events"] += 1
        bucket["estimated_cost"] = round(bucket["estimated_cost"] + float(row.get("estimated_cost") or 0), 6)
        bucket["total_tokens"] += int(row.get("total_tokens") or 0)
        model = str(row.get("model") or "unknown")
        bucket["models"][model] = round(float(bucket["models"].get(model) or 0) + float(row.get("estimated_cost") or 0), 6)
    conversations = sorted(grouped.values(), key=lambda item: item["estimated_cost"], reverse=True)[:limit]
    return {"conversations": conversations}



def _metric_queue_backlog(conn, organization_id: str, bot_id: str | None, window_minutes: int, config: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    _ = bot_id
    cutoff = _window_cutoff(window_minutes)
    sample = fetch_one(
        conn,
        "SELECT * FROM queue_depth_samples WHERE organization_id = ? AND sampled_at >= ? ORDER BY sampled_at DESC LIMIT 1",
        (organization_id, cutoff),
    )
    latest_total = int((sample or {}).get("total_depth") or 0)
    oldest_age_seconds = int((sample or {}).get("oldest_age_seconds") or 0)
    minimum_age = int(config.get("min_oldest_age_seconds") or (window_minutes * 60))
    effective_value = float(latest_total if oldest_age_seconds >= minimum_age else 0)
    return effective_value, {"latest_total": latest_total, "oldest_age_seconds": oldest_age_seconds, "minimum_age_seconds": minimum_age}



def _metric_execution_error_rate(conn, organization_id: str, bot_id: str | None, window_minutes: int) -> tuple[float, dict[str, Any]]:
    cutoff = _window_cutoff(window_minutes)
    params: list[Any] = [organization_id, cutoff]
    bot_sql = ""
    if bot_id:
        bot_sql = " AND bot_id = ?"
        params.append(bot_id)
    row = fetch_one(
        conn,
        f"SELECT COUNT(*) AS total, SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed FROM execution_runs WHERE organization_id = ? AND created_at >= ?{bot_sql}",
        tuple(params),
    )
    total = int((row or {}).get("total") or 0)
    failed = int((row or {}).get("failed") or 0)
    return (round((failed / total) * 100, 2) if total else 0.0, {"total": total, "failed": failed})



def _metric_pipeline_p95(conn, organization_id: str, bot_id: str | None, window_minutes: int, config: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    stage_name = str(config.get("stage_name") or "pipeline.total")
    params: list[Any] = [organization_id, stage_name, _window_cutoff(window_minutes)]
    bot_sql = ""
    if bot_id:
        bot_sql = " AND bot_id = ?"
        params.append(bot_id)
    rows = fetch_all(
        conn,
        f"SELECT duration_ms FROM pipeline_stage_metrics WHERE organization_id = ? AND stage_name = ? AND created_at >= ?{bot_sql} ORDER BY created_at DESC LIMIT 2000",
        tuple(params),
    )
    durations = [int(row.get("duration_ms") or 0) for row in rows if row.get("duration_ms") is not None]
    return float(_percentile(durations, 0.95) or 0.0), {"samples": len(durations), "stage_name": stage_name}



def compute_alert_metric(conn, rule: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    config = from_json(rule.get("config_json"), {})
    metric_key = str(rule.get("metric_key") or "")
    window_minutes = int(rule.get("window_minutes") or 10)
    organization_id = str(rule.get("organization_id") or "")
    bot_id = rule.get("bot_id")
    if metric_key == "queue_backlog_messages":
        return _metric_queue_backlog(conn, organization_id, bot_id, window_minutes, config)
    if metric_key == "execution_error_rate":
        return _metric_execution_error_rate(conn, organization_id, bot_id, window_minutes)
    if metric_key == "pipeline_p95_latency_ms":
        return _metric_pipeline_p95(conn, organization_id, bot_id, window_minutes, config)
    raise KeyError(metric_key)



def observability_dashboard_summary(conn, *, organization_id: str | None = None, bot_id: str | None = None) -> dict[str, Any]:
    return {
        "latency": pipeline_latency_dashboard(conn, organization_id=organization_id, bot_id=bot_id, minutes=60),
        "errors": error_rate_dashboard(conn, organization_id=organization_id, bot_id=bot_id, hours=24),
        "queues": queue_depth_dashboard(conn, organization_id=organization_id, minutes=60),
        "ai_costs": ai_cost_dashboard(conn, organization_id=organization_id, bot_id=bot_id, limit=100),
        "apm": apm_overview(),
    }
