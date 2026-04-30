-- 001_world_class.sql
-- Cumulative schema slice for WAOS production hardened artifact.

CREATE TABLE IF NOT EXISTS ai_cache (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    cache_key TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT,
    value_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS ai_cost_ledger (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    completion_tokens TEXT,
    created_at TEXT,
    estimated_cost_usd REAL NOT NULL DEFAULT 0,
    latency_ms REAL NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    model TEXT,
    operation TEXT,
    organization_id TEXT,
    prompt_tokens TEXT,
    provider TEXT,
    run_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS ai_usage_events (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    cost_estimate REAL NOT NULL DEFAULT 0,
    created_at TEXT,
    input_tokens TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    model TEXT,
    organization_id TEXT,
    output_tokens TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS circuit_breakers (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS trace_spans (
    id TEXT PRIMARY KEY,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    correlation_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    parent_span_id TEXT,
    request_id TEXT,
    span_id TEXT,
    started_at TEXT,
    status TEXT,
    trace_id TEXT,
    updated_at TEXT
);

