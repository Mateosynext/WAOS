-- 001_backend_runtime.sql
-- Cumulative schema slice for WAOS production hardened artifact.

CREATE TABLE IF NOT EXISTS executive_reports (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    delivery_channels_json TEXT NOT NULL DEFAULT '{}',
    generated_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    pdf_filename TEXT,
    pdf_generated_at TEXT,
    pdf_path TEXT,
    period_end TEXT,
    period_start TEXT,
    report_type TEXT,
    status TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS job_idempotency_keys (
    id TEXT PRIMARY KEY,
    action_type TEXT,
    bot_id TEXT,
    completed_at TEXT,
    created_at TEXT,
    dedupe_key TEXT,
    error_text TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_hash TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS report_generation_jobs (
    id TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL DEFAULT 0,
    bot_id TEXT,
    completed_at TEXT,
    created_at TEXT,
    dedupe_key TEXT,
    last_error TEXT,
    locked_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    report_id TEXT,
    request_json TEXT NOT NULL DEFAULT '{}',
    requested_by_user_id TEXT,
    scheduled_for TEXT,
    started_at TEXT,
    status TEXT,
    updated_at TEXT
);

