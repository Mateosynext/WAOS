CREATE TABLE IF NOT EXISTS message_operational_reasoning (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    intent_detected TEXT,
    urgency_level TEXT,
    urgency_score INTEGER NOT NULL DEFAULT 0,
    takeover_reason TEXT,
    policy_applied TEXT,
    classifier_source TEXT,
    generator_source TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS inbound_message_locks (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT,
    external_id TEXT,
    lock_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    correlation_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    acquired_at TEXT NOT NULL,
    released_at TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS domain_events (
    id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL,
    organization_id TEXT,
    bot_id TEXT,
    conversation_id TEXT,
    message_id TEXT,
    correlation_id TEXT,
    status TEXT NOT NULL DEFAULT 'ok',
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE INDEX IF NOT EXISTS idx_conversations_inbox_status ON conversations(organization_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_owner_status ON conversations(organization_id, assigned_user_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_takeover ON conversations(organization_id, human_takeover, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_contact_memory_stage_score ON contact_memory(organization_id, lead_stage, lead_score DESC, last_updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_contact_memory_urgency ON contact_memory(organization_id, urgency_level, urgency_score DESC, last_updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON messages(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_external ON messages(organization_id, external_id);
CREATE INDEX IF NOT EXISTS idx_message_ai_runs_message ON message_ai_runs(message_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_operational_reasoning_message ON message_operational_reasoning(message_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_domain_events_org_name ON domain_events(organization_id, event_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inbound_locks_status ON inbound_message_locks(organization_id, status, acquired_at DESC);
