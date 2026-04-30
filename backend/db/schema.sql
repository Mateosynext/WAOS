
-- WAOS release-candidate baseline schema.
-- The app still applies versioned migrations after this file.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    description TEXT,
    applied_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);


CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL DEFAULT '',
    full_name TEXT,
    global_role TEXT NOT NULL DEFAULT 'operator',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    tenant_mode TEXT NOT NULL DEFAULT 'sandbox',
    settings_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT,
    go_live_at TEXT
);

CREATE TABLE IF NOT EXISTS organization_members (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'operator',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT,
    updated_at TEXT,
    status TEXT NOT NULL DEFAULT 'active'
);
CREATE INDEX IF NOT EXISTS idx_organization_members_user ON organization_members(user_id);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    refresh_token_hash TEXT,
    refresh_token TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    expires_at TEXT,
    max_idle_at TEXT,
    created_at TEXT,
    updated_at TEXT,
    revoked_at TEXT,
    ip_address TEXT,
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS mfa_factors (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS mfa_challenges (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS sso_providers (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS security_policies (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS bots (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT,
    slug TEXT,
    vertical TEXT NOT NULL DEFAULT 'general',
    config_json TEXT NOT NULL DEFAULT '{}',
    readiness_json TEXT NOT NULL DEFAULT '{}',
    created_by_user_id TEXT,
    client_request_id TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS contact_memory (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS message_ai_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS integration_connections (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS outbox_messages (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS automation_jobs (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS job_idempotency_keys (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS outcome_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS outcome_exposures (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS tool_execution_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_routing_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS operational_command_requests (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_numbers (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS voice_notes (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS bot_creation_workflows (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS commercial_documents (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS commerce_payments (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS growth_os_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS growth_os_targets (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS runtime_self_state_conversations (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS runtime_self_state_turns (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS response_candidate_rankings (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_opt_outs (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_policy_decisions (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS operational_command_alerts (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    name TEXT,
    type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_bots_org ON bots(organization_id);
CREATE INDEX IF NOT EXISTS idx_messages_org_bot ON messages(organization_id, bot_id);
CREATE INDEX IF NOT EXISTS idx_outbox_org ON outbox_messages(organization_id);


-- Production hardening cumulative core tables.
CREATE TABLE IF NOT EXISTS bot_versions (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'v1',
    config_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft',
    created_by_user_id TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    phone TEXT,
    email TEXT,
    name TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    contact_id TEXT,
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    status TEXT NOT NULL DEFAULT 'open',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_items (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    title TEXT,
    body TEXT,
    source TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT
);
