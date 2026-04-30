-- 002_talent.sql
-- Cumulative schema slice for WAOS production hardened artifact.

CREATE TABLE IF NOT EXISTS talent_candidates (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    interview_confirmed_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    profile_json TEXT NOT NULL DEFAULT '{}',
    source TEXT,
    status TEXT,
    updated_at TEXT,
    vacancy_id TEXT,
    vacancy_title TEXT
);

