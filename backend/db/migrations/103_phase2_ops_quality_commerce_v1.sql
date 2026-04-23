CREATE TABLE IF NOT EXISTS work_queue_definitions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    role_key TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    rule_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, role_key),
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS bot_decision_explanations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    message_ai_run_id TEXT,
    confidence_score INTEGER NOT NULL DEFAULT 0,
    confidence_band TEXT NOT NULL DEFAULT 'low',
    explanation_json TEXT NOT NULL DEFAULT '{}',
    risk_flags_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (message_ai_run_id) REFERENCES message_ai_runs(id)
);

CREATE TABLE IF NOT EXISTS lead_stage_history (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    crm_lead_id TEXT NOT NULL,
    previous_stage TEXT,
    new_stage TEXT NOT NULL,
    reason TEXT,
    changed_by TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (crm_lead_id) REFERENCES crm_leads(id),
    FOREIGN KEY (changed_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS integration_replay_requests (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    webhook_receipt_id TEXT NOT NULL,
    requested_by TEXT,
    dry_run INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'requested',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (webhook_receipt_id) REFERENCES webhook_event_receipts(id),
    FOREIGN KEY (requested_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_work_queue_definitions_org_role ON work_queue_definitions(organization_id, role_key, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_decision_explanations_conv ON bot_decision_explanations(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lead_stage_history_lead ON lead_stage_history(crm_lead_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_integration_replay_requests_receipt ON integration_replay_requests(webhook_receipt_id, created_at DESC);
