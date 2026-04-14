-- backend scale foundation
CREATE INDEX IF NOT EXISTS idx_conversations_org_bot_status_updated ON conversations(organization_id, bot_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON messages(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_org_user_created ON operator_notifications(organization_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_integrations_org_bot_updated ON integration_connections(organization_id, bot_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_jobs_status_schedule ON automation_jobs(status, scheduled_for, priority);
CREATE INDEX IF NOT EXISTS idx_outbox_messages_status_schedule ON outbox_messages(status, scheduled_for, priority);
CREATE INDEX IF NOT EXISTS idx_report_jobs_status_schedule ON report_generation_jobs(status, scheduled_for);
