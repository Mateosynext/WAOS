CREATE TABLE IF NOT EXISTS agent_routing_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT,
    contact_id TEXT,
    message_id TEXT,
    routing_status TEXT NOT NULL DEFAULT 'routed',
    text_preview TEXT,
    intent_detected TEXT,
    intent_family TEXT,
    router_version TEXT NOT NULL,
    router_confidence REAL NOT NULL DEFAULT 0,
    specialist_agent_key TEXT NOT NULL,
    specialist_agent_version TEXT NOT NULL,
    prompt_base_id TEXT,
    allowed_tools_json TEXT NOT NULL DEFAULT '[]',
    risk_policy_json TEXT NOT NULL DEFAULT '{}',
    success_metrics_json TEXT NOT NULL DEFAULT '[]',
    route_reason_json TEXT NOT NULL DEFAULT '[]',
    shared_memory_json TEXT NOT NULL DEFAULT '{}',
    plan_json TEXT NOT NULL DEFAULT '{}',
    supervisor_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE INDEX IF NOT EXISTS idx_agent_routing_runs_conversation ON agent_routing_runs(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_routing_runs_agent ON agent_routing_runs(organization_id, bot_id, specialist_agent_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_routing_runs_intent ON agent_routing_runs(organization_id, intent_family, created_at DESC);
