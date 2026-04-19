ALTER TABLE message_ai_runs ADD COLUMN IF NOT EXISTS selected_variant TEXT;
ALTER TABLE message_ai_runs ADD COLUMN IF NOT EXISTS candidate_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE message_ai_runs ADD COLUMN IF NOT EXISTS ranking_version TEXT;
ALTER TABLE message_ai_runs ADD COLUMN IF NOT EXISTS ranking_summary_json TEXT NOT NULL DEFAULT '{}';
