-- 004_vertical_domain.sql
-- Cumulative schema slice for WAOS production hardened artifact.

CREATE TABLE IF NOT EXISTS vertical_domains (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

