
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    global_role TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    timezone TEXT NOT NULL,
    vertical TEXT,
    settings_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS organization_members (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE(organization_id, user_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS bots (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    business_name TEXT NOT NULL,
    vertical TEXT,
    language TEXT NOT NULL,
    timezone TEXT NOT NULL,
    status TEXT NOT NULL,
    ai_paused INTEGER NOT NULL DEFAULT 0,
    current_state TEXT NOT NULL DEFAULT 'draft',
    published_version_id TEXT,
    config_draft_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS bot_versions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    status TEXT NOT NULL,
    config_json TEXT NOT NULL,
    created_by TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    UNIQUE(bot_id, version_number)
);

CREATE TABLE IF NOT EXISTS whatsapp_numbers (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    phone_number_id TEXT NOT NULL UNIQUE,
    waba_id TEXT,
    connection_status TEXT NOT NULL,
    webhook_verify_token TEXT NOT NULL,
    access_token_masked TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    quality_rating TEXT NOT NULL DEFAULT 'unknown',
    quality_status TEXT NOT NULL DEFAULT 'unknown',
    throughput_tier TEXT NOT NULL DEFAULT 'standard',
    provider_degraded_until TEXT,
    last_health_check_at TEXT,
    last_provider_error_code TEXT,
    last_provider_error_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    phone TEXT NOT NULL,
    name TEXT,
    email TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, phone),
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS contact_memory (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    lead_stage TEXT NOT NULL DEFAULT 'new',
    lead_score INTEGER NOT NULL DEFAULT 0,
    interest TEXT,
    objections TEXT,
    summary TEXT,
    next_action TEXT,
    followup_at TEXT,
    memory_json TEXT NOT NULL DEFAULT '{}',
    last_updated_at TEXT NOT NULL,
    UNIQUE(contact_id, bot_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    status TEXT NOT NULL,
    human_takeover INTEGER NOT NULL DEFAULT 0,
    ai_active INTEGER NOT NULL DEFAULT 1,
    paused_until TEXT,
    automation_freeze_until TEXT,
    last_message_at TEXT,
    last_human_at TEXT,
    last_ai_at TEXT,
    assigned_user_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (assigned_user_id) REFERENCES users(id),
    UNIQUE(bot_id, contact_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT,
    bot_id TEXT NOT NULL,
    direction TEXT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT NOT NULL,
    body TEXT NOT NULL,
    external_id TEXT,
    status TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS message_ai_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    classifier_input TEXT,
    classifier_output TEXT,
    decision_input TEXT,
    decision_output TEXT,
    generator_input TEXT,
    generator_output TEXT,
    action_taken TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS automation_rules (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS automation_jobs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT,
    contact_id TEXT,
    rule_id TEXT,
    job_type TEXT NOT NULL,
    dedupe_key TEXT,
    scheduled_for TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 50,
    last_error TEXT,
    locked_at TEXT,
    executed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (rule_id) REFERENCES automation_rules(id)
);


CREATE TABLE IF NOT EXISTS integration_connections (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    integration_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    health_status TEXT NOT NULL,
    credential_status TEXT NOT NULL DEFAULT 'missing',
    last_error TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    last_test_at TEXT,
    last_sync_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS appointments (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT,
    contact_id TEXT,
    scheduled_for TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    timezone TEXT NOT NULL,
    notes TEXT,
    external_id TEXT,
    provider TEXT,
    provider_payload_json TEXT NOT NULL DEFAULT '{}',
    integration_id TEXT,
    synced_at TEXT,
    reminder_scheduled_at TEXT,
    confirmed_at TEXT,
    cancelled_at TEXT,
    no_show_at TEXT,
    followup_status TEXT NOT NULL DEFAULT 'pending',
    followup_sent_at TEXT,
    rescheduled_from_appointment_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (integration_id) REFERENCES integration_connections(id)
);

CREATE TABLE IF NOT EXISTS knowledge_items (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    item_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    actor_user_id TEXT,
    actor_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    action TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    request_id TEXT,
    session_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    severity TEXT NOT NULL DEFAULT 'info',
    trace_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (actor_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS metrics_daily (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    day TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(organization_id, bot_id, day),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);


CREATE TABLE IF NOT EXISTS execution_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    version_id TEXT,
    conversation_id TEXT,
    message_id TEXT,
    job_id TEXT,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    execution_id TEXT NOT NULL,
    queue_name TEXT,
    attempt INTEGER NOT NULL DEFAULT 1,
    input_json TEXT NOT NULL DEFAULT '{}',
    output_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (version_id) REFERENCES bot_versions(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (job_id) REFERENCES automation_jobs(id)
);

CREATE TABLE IF NOT EXISTS technical_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    execution_run_id TEXT,
    conversation_id TEXT,
    level TEXT NOT NULL,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    trace_id TEXT,
    execution_id TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (execution_run_id) REFERENCES execution_runs(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS secret_entries (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    scope TEXT NOT NULL,
    key_name TEXT NOT NULL,
    value_masked TEXT NOT NULL,
    value_encrypted TEXT,
    encryption_version TEXT NOT NULL DEFAULT 'v1',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    expires_at TEXT,
    last_rotated_at TEXT NOT NULL,
    last_accessed_at TEXT,
    last_access_actor_type TEXT,
    last_access_actor_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS bot_builds (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    validation_json TEXT NOT NULL DEFAULT '{}',
    diff_summary_json TEXT NOT NULL DEFAULT '{}',
    artifact_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (version_id) REFERENCES bot_versions(id)
);


CREATE TABLE IF NOT EXISTS whatsapp_opt_outs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    contact_id TEXT,
    conversation_id TEXT,
    phone TEXT,
    keyword TEXT NOT NULL,
    source_message_id TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (source_message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS outbox_messages (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    execution_run_id TEXT,
    conversation_id TEXT,
    channel TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    governance_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    provider_message_id TEXT,
    provider_status_code INTEGER,
    provider_response_json TEXT NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 50,
    next_attempt_at TEXT,
    locked_at TEXT,
    scheduled_for TEXT NOT NULL,
    sent_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (execution_run_id) REFERENCES execution_runs(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);


CREATE TABLE IF NOT EXISTS release_requests (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    version_id TEXT,
    requested_by TEXT,
    approved_by TEXT,
    status TEXT NOT NULL,
    title TEXT,
    notes TEXT,
    validation_json TEXT NOT NULL DEFAULT '{}',
    diff_summary_json TEXT NOT NULL DEFAULT '{}',
    checklist_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    approved_at TEXT,
    published_at TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (version_id) REFERENCES bot_versions(id),
    FOREIGN KEY (requested_by) REFERENCES users(id),
    FOREIGN KEY (approved_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS rate_limit_policies (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    scope TEXT NOT NULL,
    window_seconds INTEGER NOT NULL,
    max_requests INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS request_counters (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    scope TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    window_started_at TEXT NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    last_seen_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    UNIQUE(organization_id, bot_id, scope, scope_key, window_started_at)
);

CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_members(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id);
CREATE INDEX IF NOT EXISTS idx_bots_org ON bots(organization_id);
CREATE INDEX IF NOT EXISTS idx_contacts_org ON contacts(organization_id);
CREATE INDEX IF NOT EXISTS idx_conversations_org ON conversations(organization_id);
CREATE INDEX IF NOT EXISTS idx_conversations_bot ON conversations(bot_id);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_external ON messages(external_id);
CREATE INDEX IF NOT EXISTS idx_ai_runs_message ON message_ai_runs(message_id);
CREATE INDEX IF NOT EXISTS idx_jobs_due ON automation_jobs(status, scheduled_for);
CREATE INDEX IF NOT EXISTS idx_audit_org ON audit_logs(organization_id, created_at);

CREATE INDEX IF NOT EXISTS idx_execution_runs_org_created ON execution_runs(organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_execution_runs_bot_created ON execution_runs(bot_id, created_at);
CREATE INDEX IF NOT EXISTS idx_execution_runs_trace ON execution_runs(trace_id);
CREATE INDEX IF NOT EXISTS idx_technical_logs_run ON technical_logs(execution_run_id, created_at);
CREATE INDEX IF NOT EXISTS idx_integrations_org ON integration_connections(organization_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_secrets_org ON secret_entries(organization_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_bot_builds_bot ON bot_builds(bot_id, created_at);
CREATE INDEX IF NOT EXISTS idx_outbox_status_due ON outbox_messages(status, scheduled_for);


CREATE TABLE IF NOT EXISTS whatsapp_policy_decisions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT,
    contact_id TEXT,
    outbox_id TEXT,
    message_id TEXT,
    decision_status TEXT NOT NULL,
    delivery_mode TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    policy_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (outbox_id) REFERENCES outbox_messages(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);
CREATE INDEX IF NOT EXISTS idx_whatsapp_policy_decisions_org ON whatsapp_policy_decisions(organization_id, bot_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_release_requests_bot ON release_requests(bot_id, created_at);
CREATE INDEX IF NOT EXISTS idx_rate_limit_policies_org ON rate_limit_policies(organization_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_request_counters_lookup ON request_counters(organization_id, bot_id, scope, scope_key, window_started_at);

CREATE TABLE IF NOT EXISTS auth_login_attempts (
    id TEXT PRIMARY KEY,
    scope_key TEXT NOT NULL UNIQUE,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    first_attempt_at TEXT NOT NULL,
    last_attempt_at TEXT NOT NULL,
    blocked_until TEXT,
    last_ip_address TEXT,
    last_user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_auth_login_attempts_blocked ON auth_login_attempts(blocked_until, last_attempt_at);


CREATE TABLE IF NOT EXISTS auth_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    refresh_token_hash TEXT NOT NULL UNIQUE,
    refresh_token_family_id TEXT,
    status TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    max_idle_at TEXT,
    last_authenticated_at TEXT,
    refresh_token_last_rotated_at TEXT,
    refresh_token_reuse_detected_at TEXT,
    revoked_at TEXT,
    last_seen_at TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    family_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    previous_token_hash TEXT,
    status TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    used_at TEXT,
    rotated_at TEXT,
    revoked_at TEXT,
    reuse_detected_at TEXT,
    replaced_by_token_hash TEXT,
    FOREIGN KEY (session_id) REFERENCES auth_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_auth_refresh_tokens_session ON auth_refresh_tokens(session_id, issued_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_refresh_tokens_family ON auth_refresh_tokens(family_id, issued_at DESC);

CREATE TABLE IF NOT EXISTS mfa_factors (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    factor_type TEXT NOT NULL,
    secret TEXT,
    secret_encrypted TEXT,
    secret_masked TEXT,
    recovery_codes_json TEXT NOT NULL DEFAULT '[]',
    label TEXT,
    status TEXT NOT NULL,
    enrolled_at TEXT NOT NULL,
    verified_at TEXT,
    last_used_at TEXT,
    revoked_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS mfa_challenges (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    factor_id TEXT,
    status TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    verified_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (factor_id) REFERENCES mfa_factors(id)
);

CREATE TABLE IF NOT EXISTS oauth_states (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    integration_id TEXT,
    provider TEXT NOT NULL,
    state_token_hash TEXT NOT NULL UNIQUE,
    redirect_uri TEXT,
    scope TEXT,
    code_verifier TEXT,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (integration_id) REFERENCES integration_connections(id)
);

CREATE TABLE IF NOT EXISTS organization_security_policies (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL UNIQUE,
    require_mfa INTEGER NOT NULL DEFAULT 0,
    require_sso INTEGER NOT NULL DEFAULT 0,
    session_ttl_minutes INTEGER NOT NULL DEFAULT 720,
    session_idle_timeout_minutes INTEGER NOT NULL DEFAULT 120,
    step_up_window_minutes INTEGER NOT NULL DEFAULT 15,
    max_sessions_per_user INTEGER NOT NULL DEFAULT 5,
    require_dual_approval_releases INTEGER NOT NULL DEFAULT 1,
    webhook_signature_required INTEGER NOT NULL DEFAULT 1,
    strict_idempotency INTEGER NOT NULL DEFAULT 1,
    ip_allowlist_json TEXT NOT NULL DEFAULT '[]',
    allowed_origins_json TEXT NOT NULL DEFAULT '[]',
    updated_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sso_providers (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    issuer TEXT,
    client_id TEXT,
    status TEXT NOT NULL,
    scopes_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    last_test_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);


CREATE TABLE IF NOT EXISTS sso_identities (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    external_subject TEXT NOT NULL,
    email TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    last_login_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(provider_id, external_subject),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (provider_id) REFERENCES sso_providers(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS runtime_callbacks (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    bot_id TEXT,
    execution_run_id TEXT,
    callback_type TEXT NOT NULL,
    target TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    last_error TEXT,
    created_at TEXT NOT NULL,
    delivered_at TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (execution_run_id) REFERENCES execution_runs(id)
);

CREATE TABLE IF NOT EXISTS integration_sync_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    integration_id TEXT NOT NULL,
    bot_id TEXT,
    status TEXT NOT NULL,
    direction TEXT NOT NULL,
    summary_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (integration_id) REFERENCES integration_connections(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS webhook_event_receipts (
    id TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    organization_id TEXT,
    external_event_id TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_hash TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(channel, external_event_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id, status, expires_at);
CREATE INDEX IF NOT EXISTS idx_mfa_challenges_user ON mfa_challenges(user_id, status, expires_at);
CREATE INDEX IF NOT EXISTS idx_sso_providers_org ON sso_providers(organization_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_sso_identities_org ON sso_identities(organization_id, last_login_at);
CREATE INDEX IF NOT EXISTS idx_runtime_callbacks_org ON runtime_callbacks(organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_integration_sync_runs_org ON integration_sync_runs(organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_webhook_receipts_channel ON webhook_event_receipts(channel, created_at);

CREATE TABLE IF NOT EXISTS crm_leads (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT,
    contact_id TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'nuevo',
    estimated_amount REAL NOT NULL DEFAULT 0,
    owner_user_id TEXT,
    next_action TEXT,
    followup_at TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    notes TEXT,
    lost_reason TEXT,
    pipeline_json TEXT NOT NULL DEFAULT '{}',
    score_buying_intent INTEGER NOT NULL DEFAULT 0,
    close_probability INTEGER NOT NULL DEFAULT 0,
    detected_objections_json TEXT NOT NULL DEFAULT '[]',
    best_next_action TEXT,
    temperature_status TEXT NOT NULL DEFAULT 'templado',
    language TEXT NOT NULL DEFAULT 'es',
    source_channel TEXT NOT NULL DEFAULT 'whatsapp',
    source_campaign TEXT,
    last_qualification_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS commerce_payments (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT,
    contact_id TEXT NOT NULL,
    crm_lead_id TEXT,
    title TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'MXN',
    status TEXT NOT NULL,
    payment_link_url TEXT,
    payment_link_status TEXT NOT NULL DEFAULT 'generated',
    reminder_scheduled_at TEXT,
    confirmed_at TEXT,
    receipt_sent_at TEXT,
    cart_recovery_status TEXT NOT NULL DEFAULT 'inactive',
    send_receipt_on_confirm INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (crm_lead_id) REFERENCES crm_leads(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_flows (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    name TEXT NOT NULL,
    flow_type TEXT NOT NULL,
    status TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'es',
    definition_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    remote_flow_id TEXT,
    remote_status TEXT NOT NULL DEFAULT 'not_synced',
    remote_details_json TEXT NOT NULL DEFAULT '{}',
    fallback_json TEXT NOT NULL DEFAULT '{}',
    runtime_config_json TEXT NOT NULL DEFAULT '{}',
    current_version_id TEXT,
    published_version_id TEXT,
    runtime_endpoint TEXT,
    remote_last_synced_at TEXT,
    remote_last_published_at TEXT,
    last_sync_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_flow_versions (
    id TEXT PRIMARY KEY,
    flow_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'draft',
    flow_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    compatibility_json TEXT NOT NULL DEFAULT '{}',
    rollout_json TEXT NOT NULL DEFAULT '{}',
    remote_asset_status TEXT NOT NULL DEFAULT 'pending',
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    cloned_from_version_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    published_at TEXT,
    FOREIGN KEY (flow_id) REFERENCES whatsapp_flows(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_flow_publications (
    id TEXT PRIMARY KEY,
    flow_id TEXT NOT NULL,
    version_id TEXT,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'meta',
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    remote_flow_id TEXT,
    request_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    FOREIGN KEY (flow_id) REFERENCES whatsapp_flows(id),
    FOREIGN KEY (version_id) REFERENCES whatsapp_flow_versions(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_flow_executions (
    id TEXT PRIMARY KEY,
    flow_id TEXT NOT NULL,
    version_id TEXT,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT,
    contact_id TEXT,
    flow_token TEXT NOT NULL,
    assigned_variant TEXT,
    status TEXT NOT NULL,
    current_screen_id TEXT,
    fallback_reason TEXT,
    fallback_mode TEXT,
    context_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    channel_message_id TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    last_event_at TEXT NOT NULL,
    FOREIGN KEY (flow_id) REFERENCES whatsapp_flows(id),
    FOREIGN KEY (version_id) REFERENCES whatsapp_flow_versions(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_flow_events (
    id TEXT PRIMARY KEY,
    flow_id TEXT NOT NULL,
    version_id TEXT,
    execution_id TEXT,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    screen_id TEXT,
    step_index INTEGER,
    variant TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (flow_id) REFERENCES whatsapp_flows(id),
    FOREIGN KEY (version_id) REFERENCES whatsapp_flow_versions(id),
    FOREIGN KEY (execution_id) REFERENCES whatsapp_flow_executions(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_flow_experiments (
    id TEXT PRIMARY KEY,
    flow_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    version_a_id TEXT NOT NULL,
    version_b_id TEXT NOT NULL,
    rollout_percentage INTEGER NOT NULL DEFAULT 50,
    status TEXT NOT NULL DEFAULT 'draft',
    note TEXT,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (flow_id) REFERENCES whatsapp_flows(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (version_a_id) REFERENCES whatsapp_flow_versions(id),
    FOREIGN KEY (version_b_id) REFERENCES whatsapp_flow_versions(id)
);

CREATE TABLE IF NOT EXISTS conversation_reviews (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    agent_user_id TEXT,
    review_type TEXT NOT NULL,
    quality_score INTEGER NOT NULL,
    response_delay_seconds INTEGER NOT NULL DEFAULT 0,
    tone TEXT NOT NULL,
    missed_opportunities_json TEXT NOT NULL DEFAULT '[]',
    checklist_json TEXT NOT NULL DEFAULT '[]',
    recommendations_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (agent_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS reactivation_recommendations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    crm_lead_id TEXT,
    segment TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 50,
    suggested_channel TEXT NOT NULL DEFAULT 'whatsapp',
    suggested_message TEXT NOT NULL,
    suggested_incentive TEXT,
    suggested_send_at TEXT,
    rationale TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (crm_lead_id) REFERENCES crm_leads(id)
);

CREATE TABLE IF NOT EXISTS executive_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    report_type TEXT NOT NULL,
    summary_json TEXT NOT NULL DEFAULT '{}',
    delivery_channels_json TEXT NOT NULL DEFAULT '[]',
    pdf_path TEXT,
    pdf_filename TEXT,
    pdf_generated_at TEXT,
    updated_at TEXT,
    generated_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS voice_notes (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    message_id TEXT,
    transcript TEXT NOT NULL,
    detected_language TEXT NOT NULL DEFAULT 'es',
    intent TEXT NOT NULL,
    urgency_level TEXT NOT NULL,
    emotion TEXT NOT NULL,
    suggested_response_text TEXT,
    suggested_response_audio_text TEXT,
    summary TEXT,
    media_id TEXT,
    media_url TEXT,
    media_mime_type TEXT,
    media_sha256 TEXT,
    media_size_bytes INTEGER NOT NULL DEFAULT 0,
    consent_status TEXT NOT NULL DEFAULT 'implicit_inbound_whatsapp',
    media_expires_at TEXT,
    transcription_source TEXT NOT NULL DEFAULT 'manual',
    transcription_confidence REAL NOT NULL DEFAULT 0,
    diarization_json TEXT NOT NULL DEFAULT '[]',
    segments_json TEXT NOT NULL DEFAULT '[]',
    audio_quality TEXT NOT NULL DEFAULT 'unknown',
    background_noise_level TEXT NOT NULL DEFAULT 'unknown',
    processing_status TEXT NOT NULL DEFAULT 'completed',
    reply_mode TEXT NOT NULL DEFAULT 'text',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS voice_media_assets (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT,
    message_id TEXT,
    voice_note_id TEXT,
    direction TEXT NOT NULL,
    provider TEXT NOT NULL,
    media_role TEXT NOT NULL,
    provider_media_id TEXT,
    storage_path TEXT,
    public_url TEXT,
    mime_type TEXT,
    sha256 TEXT,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    expires_at TEXT,
    consent_status TEXT NOT NULL DEFAULT 'implicit_inbound_whatsapp',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (voice_note_id) REFERENCES voice_notes(id)
);

CREATE TABLE IF NOT EXISTS voice_processing_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT,
    message_id TEXT,
    voice_note_id TEXT,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (voice_note_id) REFERENCES voice_notes(id)
);

CREATE TABLE IF NOT EXISTS customer_feedback (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT,
    contact_id TEXT,
    score_type TEXT NOT NULL,
    score_value INTEGER NOT NULL,
    reason TEXT,
    detractor_alert INTEGER NOT NULL DEFAULT 0,
    recovery_status TEXT NOT NULL DEFAULT 'not_needed',
    agent_user_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (agent_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS service_requests (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    request_type TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

CREATE TABLE IF NOT EXISTS industry_playbooks (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    industry TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE INDEX IF NOT EXISTS idx_crm_leads_org ON crm_leads(organization_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_crm_leads_bot_stage ON crm_leads(bot_id, stage, updated_at);
CREATE INDEX IF NOT EXISTS idx_commerce_payments_org ON commerce_payments(organization_id, status, updated_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_flows_bot ON whatsapp_flows(bot_id, status, updated_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_flow_versions_flow ON whatsapp_flow_versions(flow_id, version_number DESC, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_flow_publications_flow ON whatsapp_flow_publications(flow_id, status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_flow_executions_flow ON whatsapp_flow_executions(flow_id, status, last_event_at DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_flow_events_flow ON whatsapp_flow_events(flow_id, event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_flow_experiments_flow ON whatsapp_flow_experiments(flow_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_reviews_org ON conversation_reviews(organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_reactivation_org ON reactivation_recommendations(organization_id, status, updated_at);
CREATE INDEX IF NOT EXISTS idx_executive_reports_org ON executive_reports(organization_id, generated_at);
CREATE INDEX IF NOT EXISTS idx_voice_notes_org ON voice_notes(organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_voice_notes_conversation ON voice_notes(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_voice_media_assets_org ON voice_media_assets(organization_id, media_role, created_at);
CREATE INDEX IF NOT EXISTS idx_voice_processing_events_org ON voice_processing_events(organization_id, stage, created_at);
CREATE INDEX IF NOT EXISTS idx_customer_feedback_org ON customer_feedback(organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_service_requests_org ON service_requests(organization_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_playbooks_org ON industry_playbooks(organization_id, updated_at);


CREATE TABLE IF NOT EXISTS bot_language_configs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    default_language TEXT NOT NULL DEFAULT 'es',
    supported_languages_json TEXT NOT NULL DEFAULT '[]',
    detect_contact_language INTEGER NOT NULL DEFAULT 1,
    templates_json TEXT NOT NULL DEFAULT '{}',
    fallback_language TEXT NOT NULL DEFAULT 'en',
    handoff_respect_language INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, bot_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);
CREATE INDEX IF NOT EXISTS idx_language_configs_org ON bot_language_configs(organization_id, updated_at);


CREATE TABLE IF NOT EXISTS operator_training_examples (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    operator_user_id TEXT,
    input_text TEXT,
    output_text TEXT NOT NULL,
    example_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'captured',
    context_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (operator_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS conversation_summaries (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    summary_type TEXT NOT NULL,
    content_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS operator_copilot_suggestions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    operator_user_id TEXT,
    draft_text TEXT,
    suggestion_text TEXT NOT NULL,
    tone TEXT,
    status TEXT NOT NULL DEFAULT 'suggested',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (operator_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS conversation_tags (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(conversation_id, tag),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS contact_memory_history (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    contact_memory_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    changed_by TEXT,
    before_json TEXT NOT NULL DEFAULT '{}',
    after_json TEXT NOT NULL DEFAULT '{}',
    changed_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (contact_memory_id) REFERENCES contact_memory(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (changed_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS alert_rules_v14 (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    name TEXT NOT NULL,
    metric_key TEXT NOT NULL,
    comparator TEXT NOT NULL,
    threshold_value REAL NOT NULL,
    window_minutes INTEGER NOT NULL DEFAULT 60,
    notify_channels_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active',
    config_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS report_schedules (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    name TEXT NOT NULL,
    frequency TEXT NOT NULL,
    next_run_at TEXT NOT NULL,
    delivery_channels_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active',
    config_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS routing_rules (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    name TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 50,
    conditions_json TEXT NOT NULL DEFAULT '{}',
    assigned_user_id TEXT,
    assigned_team TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (assigned_user_id) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS publish_schedules (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    version_id TEXT,
    scheduled_for TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    notes TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    published_at TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (version_id) REFERENCES bot_versions(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS followup_experiments (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    name TEXT NOT NULL,
    vertical TEXT,
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    variant_a_text TEXT NOT NULL,
    variant_b_text TEXT NOT NULL,
    goal_metric TEXT NOT NULL DEFAULT 'reply_rate',
    status TEXT NOT NULL DEFAULT 'draft',
    results_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_training_examples_org ON operator_training_examples(organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_conv ON conversation_summaries(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_copilot_suggestions_conv ON operator_copilot_suggestions(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_tags_conv ON conversation_tags(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_contact_memory_history_mem ON contact_memory_history(contact_memory_id, changed_at);
CREATE INDEX IF NOT EXISTS idx_alert_rules_v14_org ON alert_rules_v14(organization_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_report_schedules_org ON report_schedules(organization_id, next_run_at);
CREATE INDEX IF NOT EXISTS idx_routing_rules_org ON routing_rules(organization_id, priority, updated_at);
CREATE INDEX IF NOT EXISTS idx_publish_schedules_bot ON publish_schedules(bot_id, scheduled_for);
CREATE INDEX IF NOT EXISTS idx_followup_experiments_bot ON followup_experiments(bot_id, updated_at);


CREATE TABLE IF NOT EXISTS operator_notifications (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    user_id TEXT,
    conversation_id TEXT,
    category TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'in_app',
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    status TEXT NOT NULL DEFAULT 'unread',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    read_at TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS alert_events (
    id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    metric_key TEXT NOT NULL,
    comparator TEXT NOT NULL,
    threshold_value REAL NOT NULL,
    observed_value REAL NOT NULL,
    window_started_at TEXT NOT NULL,
    window_ended_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'triggered',
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(rule_id, window_started_at, window_ended_at),
    FOREIGN KEY (rule_id) REFERENCES alert_rules_v14(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS report_schedule_runs (
    id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    report_id TEXT,
    status TEXT NOT NULL,
    run_at TEXT NOT NULL,
    artifact_path TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (schedule_id) REFERENCES report_schedules(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (report_id) REFERENCES executive_reports(id)
);

CREATE TABLE IF NOT EXISTS publish_schedule_runs (
    id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    version_id TEXT,
    status TEXT NOT NULL,
    run_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (schedule_id) REFERENCES publish_schedules(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (version_id) REFERENCES bot_versions(id)
);

CREATE TABLE IF NOT EXISTS routing_assignments (
    id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    assigned_user_id TEXT,
    assigned_team TEXT,
    matched_conditions_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (rule_id) REFERENCES routing_rules(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (assigned_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_operator_notifications_org ON operator_notifications(organization_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_alert_events_rule ON alert_events(rule_id, created_at);
CREATE INDEX IF NOT EXISTS idx_report_schedule_runs_schedule ON report_schedule_runs(schedule_id, created_at);
CREATE INDEX IF NOT EXISTS idx_publish_schedule_runs_schedule ON publish_schedule_runs(schedule_id, created_at);
CREATE INDEX IF NOT EXISTS idx_routing_assignments_conv ON routing_assignments(conversation_id, created_at);


CREATE TABLE IF NOT EXISTS delivery_attempts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    conversation_id TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    target TEXT,
    subject TEXT,
    body TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    provider TEXT,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    scheduled_at TEXT,
    delivered_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS followup_experiment_assignments (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT,
    message_id TEXT,
    variant TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    status TEXT NOT NULL DEFAULT 'sent',
    assigned_at TEXT NOT NULL,
    replied_at TEXT,
    booked_at TEXT,
    won_at TEXT,
    last_event_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (experiment_id) REFERENCES followup_experiments(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE INDEX IF NOT EXISTS idx_delivery_attempts_entity ON delivery_attempts(entity_type, entity_id, created_at);
CREATE INDEX IF NOT EXISTS idx_delivery_attempts_org ON delivery_attempts(organization_id, channel, created_at);

CREATE TABLE IF NOT EXISTS whatsapp_delivery_status_facts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    conversation_id TEXT,
    outbox_id TEXT,
    message_id TEXT,
    provider_message_id TEXT NOT NULL,
    phone_number_id TEXT,
    recipient_id TEXT,
    status TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'webhook',
    pricing_json TEXT NOT NULL DEFAULT '{}',
    error_code INTEGER,
    error_message TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    event_fingerprint TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (outbox_id) REFERENCES outbox_messages(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_delivery_projection (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    conversation_id TEXT,
    contact_id TEXT,
    outbox_id TEXT,
    message_id TEXT,
    provider_message_id TEXT NOT NULL UNIQUE,
    phone_number_id TEXT,
    recipient_id TEXT,
    template_name TEXT,
    message_kind TEXT NOT NULL DEFAULT 'text',
    vertical TEXT,
    accepted_at TEXT,
    sent_at TEXT,
    delivered_at TEXT,
    read_at TEXT,
    failed_at TEXT,
    current_status TEXT NOT NULL DEFAULT 'accepted',
    first_event_at TEXT,
    last_event_at TEXT,
    last_error_code INTEGER,
    last_error_message TEXT,
    pricing_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (outbox_id) REFERENCES outbox_messages(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_delivery_facts_provider ON whatsapp_delivery_status_facts(provider_message_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_delivery_facts_org ON whatsapp_delivery_status_facts(organization_id, status, observed_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_delivery_projection_org ON whatsapp_delivery_projection(organization_id, current_status, accepted_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_delivery_projection_number ON whatsapp_delivery_projection(phone_number_id, accepted_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_delivery_projection_template ON whatsapp_delivery_projection(template_name, accepted_at);
CREATE INDEX IF NOT EXISTS idx_followup_assignments_experiment ON followup_experiment_assignments(experiment_id, assigned_at);
CREATE INDEX IF NOT EXISTS idx_followup_assignments_conversation ON followup_experiment_assignments(conversation_id, assigned_at);


CREATE TABLE IF NOT EXISTS agenda_reminder_preferences (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL UNIQUE,
    tone TEXT NOT NULL DEFAULT 'amable',
    hours_before INTEGER NOT NULL DEFAULT 24,
    last_hours INTEGER NOT NULL DEFAULT 2,
    count INTEGER NOT NULL DEFAULT 2,
    updated_by_user_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (updated_by_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS agenda_blocked_slots (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    reason TEXT,
    created_by_user_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_agenda_reminder_preferences_org ON agenda_reminder_preferences(organization_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_agenda_blocked_slots_org ON agenda_blocked_slots(organization_id, start_at);
CREATE INDEX IF NOT EXISTS idx_agenda_blocked_slots_bot ON agenda_blocked_slots(bot_id, start_at);


CREATE TABLE IF NOT EXISTS conversation_assignment_history (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    previous_assigned_user_id TEXT,
    new_assigned_user_id TEXT,
    queue_role TEXT,
    assignment_mode TEXT NOT NULL DEFAULT 'manual',
    reasoning_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (previous_assigned_user_id) REFERENCES users(id),
    FOREIGN KEY (new_assigned_user_id) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS bot_simulation_cases (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    title TEXT NOT NULL,
    scenario_text TEXT NOT NULL,
    expected_outcome_json TEXT NOT NULL DEFAULT '{}',
    tags_json TEXT NOT NULL DEFAULT '[]',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS bot_simulation_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    compare_target TEXT NOT NULL DEFAULT 'draft',
    left_version_id TEXT,
    right_version_id TEXT,
    status TEXT NOT NULL DEFAULT 'completed',
    summary_json TEXT NOT NULL DEFAULT '{}',
    cases_total INTEGER NOT NULL DEFAULT 0,
    passed_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    created_by TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (left_version_id) REFERENCES bot_versions(id),
    FOREIGN KEY (right_version_id) REFERENCES bot_versions(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS bot_simulation_run_results (
    id TEXT PRIMARY KEY,
    simulation_run_id TEXT NOT NULL,
    simulation_case_id TEXT NOT NULL,
    passed INTEGER NOT NULL DEFAULT 0,
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (simulation_run_id) REFERENCES bot_simulation_runs(id),
    FOREIGN KEY (simulation_case_id) REFERENCES bot_simulation_cases(id)
);

CREATE TABLE IF NOT EXISTS agenda_resources (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    name TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    branch TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS agenda_resource_capacity_rules (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    resource_id TEXT NOT NULL,
    day_of_week INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    slot_capacity INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (resource_id) REFERENCES agenda_resources(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS appointment_resource_assignments (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    appointment_id TEXT NOT NULL UNIQUE,
    resource_id TEXT NOT NULL,
    assigned_by TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id),
    FOREIGN KEY (resource_id) REFERENCES agenda_resources(id),
    FOREIGN KEY (assigned_by) REFERENCES users(id)
);


CREATE TABLE IF NOT EXISTS legal_acceptance_events (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL,
    version TEXT NOT NULL,
    acceptance_type TEXT NOT NULL DEFAULT 'other',
    subject_type TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    organization_id TEXT,
    contact_id TEXT,
    user_id TEXT,
    source TEXT NOT NULL DEFAULT 'product',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS legal_consent_records (
    id TEXT PRIMARY KEY,
    subject_type TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    organization_id TEXT,
    contact_id TEXT,
    user_id TEXT,
    consent_key TEXT NOT NULL,
    status TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0',
    categories_json TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'product',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(subject_type, subject_key, consent_key)
);

CREATE TABLE IF NOT EXISTS privacy_requests (
    id TEXT PRIMARY KEY,
    request_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'received',
    requester_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    organization_id TEXT,
    contact_id TEXT,
    country TEXT,
    message TEXT,
    source TEXT NOT NULL DEFAULT 'privacy_center',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    requested_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS legal_audit_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    subject_type TEXT,
    subject_key TEXT,
    actor_type TEXT,
    actor_id TEXT,
    request_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_legal_acceptance_subject ON legal_acceptance_events(subject_type, subject_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_legal_acceptance_slug ON legal_acceptance_events(slug, version, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_legal_consent_subject ON legal_consent_records(subject_type, subject_key, consent_key, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_privacy_requests_status ON privacy_requests(status, requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_legal_audit_events_subject ON legal_audit_events(subject_type, subject_key, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_whatsapp_opt_outs_bot_contact ON whatsapp_opt_outs(organization_id, bot_id, contact_id, active, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_opt_outs_bot_phone ON whatsapp_opt_outs(organization_id, bot_id, phone, active, updated_at DESC);
