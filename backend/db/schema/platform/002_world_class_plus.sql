-- 002_world_class_plus.sql
-- Cumulative schema slice for WAOS production hardened artifact.

CREATE TABLE IF NOT EXISTS defensive_rate_limits (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS immutable_audit_events (
    id TEXT PRIMARY KEY,
    actor_user_id TEXT,
    bot_id TEXT,
    created_at TEXT,
    event_type TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS prompt_experiments (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    status TEXT,
    updated_at TEXT,
    variants_json TEXT NOT NULL DEFAULT '{}'
);

