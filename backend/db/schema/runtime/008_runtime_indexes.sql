-- Runtime indexes for hardened production artifact.
CREATE INDEX IF NOT EXISTS idx_job_idempotency_keys_org_action ON job_idempotency_keys (organization_id, action_type);
CREATE INDEX IF NOT EXISTS idx_report_generation_jobs_status ON report_generation_jobs (status, priority);
CREATE INDEX IF NOT EXISTS idx_webhook_event_receipts_org ON webhook_event_receipts (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_tool_execution_runs_org ON tool_execution_runs (organization_id, created_at);
