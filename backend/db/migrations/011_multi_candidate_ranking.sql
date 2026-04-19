-- phase 21: response multi-candidate ranking
ALTER TABLE message_ai_runs ADD COLUMN selected_variant TEXT;
ALTER TABLE message_ai_runs ADD COLUMN candidate_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE message_ai_runs ADD COLUMN ranking_version TEXT;
ALTER TABLE message_ai_runs ADD COLUMN ranking_summary_json TEXT NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS response_candidate_rankings (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    message_ai_run_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    candidate_index INTEGER NOT NULL,
    variant_key TEXT NOT NULL,
    tone TEXT,
    cta_style TEXT,
    length TEXT,
    framing TEXT,
    source TEXT,
    response_text TEXT NOT NULL,
    verification_status TEXT,
    verification_json TEXT NOT NULL DEFAULT '{}',
    score_total REAL NOT NULL DEFAULT 0,
    score_json TEXT NOT NULL DEFAULT '{}',
    selected INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_response_candidate_rankings_run ON response_candidate_rankings(message_ai_run_id, candidate_index);
CREATE INDEX IF NOT EXISTS idx_response_candidate_rankings_selected ON response_candidate_rankings(selected, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_response_candidate_rankings_variant ON response_candidate_rankings(variant_key, created_at DESC);
