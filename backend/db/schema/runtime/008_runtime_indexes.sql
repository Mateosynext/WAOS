CREATE INDEX IF NOT EXISTS idx_report_generation_jobs_status ON report_generation_jobs(status, scheduled_for ASC, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_report_generation_jobs_priority ON report_generation_jobs(status, priority DESC, scheduled_for ASC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_flows_remote ON whatsapp_flows(remote_flow_id, remote_status, updated_at);
