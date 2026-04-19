ALTER TABLE outcome_exposures ADD COLUMN IF NOT EXISTS tool_execution_run_id TEXT;
ALTER TABLE outcome_exposures ADD COLUMN IF NOT EXISTS tool_action TEXT;
ALTER TABLE outcome_exposures ADD COLUMN IF NOT EXISTS tool_adapter_key TEXT;
ALTER TABLE outcome_exposures ADD COLUMN IF NOT EXISTS tool_provider TEXT;

ALTER TABLE outcome_events ADD COLUMN IF NOT EXISTS source_execution_run_id TEXT;
ALTER TABLE outcome_events ADD COLUMN IF NOT EXISTS source_tool_action TEXT;
ALTER TABLE outcome_events ADD COLUMN IF NOT EXISTS source_tool_provider TEXT;

CREATE INDEX IF NOT EXISTS idx_outcome_exposures_tool_run ON outcome_exposures(tool_execution_run_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_exposures_tool_action ON outcome_exposures(tool_action, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_exposures_tool_provider ON outcome_exposures(tool_provider, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_events_source_execution ON outcome_events(source_execution_run_id, event_timestamp DESC);
