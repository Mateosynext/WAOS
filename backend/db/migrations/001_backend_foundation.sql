CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    description TEXT,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_idempotency_keys (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    dedupe_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    payload_hash TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    error_text TEXT,
    last_run_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_job_idempotency_status ON job_idempotency_keys(job_type, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS report_generation_jobs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    requested_by_user_id TEXT,
    dedupe_key TEXT NOT NULL UNIQUE,
    request_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    report_id TEXT,
    scheduled_for TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_report_generation_jobs_status ON report_generation_jobs(status, scheduled_for ASC, updated_at DESC);
