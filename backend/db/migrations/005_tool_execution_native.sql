CREATE TABLE IF NOT EXISTS tool_execution_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    action TEXT NOT NULL,
    adapter_key TEXT NOT NULL,
    provider TEXT,
    execution_mode TEXT NOT NULL DEFAULT 'execute',
    status TEXT NOT NULL DEFAULT 'requested',
    permission_required TEXT NOT NULL,
    requires_confirmation INTEGER NOT NULL DEFAULT 0,
    confirmation_token_hash TEXT,
    confirmed_by TEXT,
    confirmed_at TEXT,
    preview_run_id TEXT,
    idempotency_key TEXT,
    idempotent_replay_of_run_id TEXT,
    request_json TEXT NOT NULL DEFAULT '{}',
    normalized_payload_json TEXT NOT NULL DEFAULT '{}',
    validation_json TEXT NOT NULL DEFAULT '{}',
    target_ref_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    prompt_run_id TEXT,
    flow_id TEXT,
    template_id TEXT,
    decision_path_id TEXT,
    handoff_id TEXT,
    conversation_id TEXT,
    contact_id TEXT,
    lead_id TEXT,
    appointment_id TEXT,
    payment_id TEXT,
    requested_by TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (preview_run_id) REFERENCES tool_execution_runs(id),
    FOREIGN KEY (idempotent_replay_of_run_id) REFERENCES tool_execution_runs(id),
    FOREIGN KEY (requested_by) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_tool_execution_runs_org_action ON tool_execution_runs(organization_id, action, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_execution_runs_status ON tool_execution_runs(organization_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_execution_runs_idempotency ON tool_execution_runs(organization_id, idempotency_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_execution_runs_entities ON tool_execution_runs(organization_id, conversation_id, contact_id, appointment_id, payment_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tool_execution_step_logs (
    id TEXT PRIMARY KEY,
    execution_run_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    action TEXT NOT NULL,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    adapter_key TEXT,
    provider TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (execution_run_id) REFERENCES tool_execution_runs(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);
CREATE INDEX IF NOT EXISTS idx_tool_execution_steps_run ON tool_execution_step_logs(execution_run_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_tool_execution_steps_org_action ON tool_execution_step_logs(organization_id, action, created_at DESC);
