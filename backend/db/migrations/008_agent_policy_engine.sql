CREATE TABLE IF NOT EXISTS agent_policy_evaluations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    conversation_id TEXT,
    contact_id TEXT,
    specialist_agent_key TEXT,
    policy_profile_key TEXT NOT NULL,
    policy_profile_version TEXT NOT NULL,
    requested_action TEXT,
    enforcement_status TEXT NOT NULL DEFAULT 'allow',
    requires_human_review INTEGER NOT NULL DEFAULT 0,
    decision_json TEXT NOT NULL DEFAULT '{}',
    budget_state_json TEXT NOT NULL DEFAULT '{}',
    sla_state_json TEXT NOT NULL DEFAULT '{}',
    observed_json TEXT NOT NULL DEFAULT '{}',
    agent_routing_run_id TEXT,
    tool_execution_run_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_policy_evaluations_org_created ON agent_policy_evaluations(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_policy_evaluations_agent ON agent_policy_evaluations(organization_id, specialist_agent_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_policy_evaluations_profile ON agent_policy_evaluations(organization_id, policy_profile_key, created_at DESC);
