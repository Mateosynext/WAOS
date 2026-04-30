-- 003_telemetry.sql
-- Cumulative schema slice for WAOS production hardened artifact.

CREATE TABLE IF NOT EXISTS alert_events (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS alert_rules_v14 (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    comparator TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    created_by TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    metric_key TEXT,
    name TEXT,
    notify_channels_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    threshold_value REAL NOT NULL DEFAULT 0,
    updated_at TEXT,
    window_minutes INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS otel_span_exports (
    id TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL DEFAULT 0,
    bot_id TEXT,
    created_at TEXT,
    endpoint TEXT,
    exported_at TEXT,
    last_error TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    span_id TEXT,
    status TEXT,
    trace_id TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS pipeline_stage_metrics (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    conversation_id TEXT,
    correlation_id TEXT,
    created_at TEXT,
    duration_ms REAL NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    source_type TEXT,
    stage_name TEXT,
    status TEXT,
    trace_id TEXT,
    updated_at TEXT,
    vertical TEXT
);

CREATE TABLE IF NOT EXISTS queue_depth_samples (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    callbacks_depth TEXT,
    created_at TEXT,
    integration_depth TEXT,
    jobs_depth TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    oldest_age_seconds INTEGER NOT NULL DEFAULT 0,
    organization_id TEXT,
    outbox_depth TEXT,
    sampled_at TEXT,
    status TEXT,
    total_depth INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT
);

