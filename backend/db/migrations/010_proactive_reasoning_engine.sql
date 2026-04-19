-- Proactive reasoning engine: signals, scored candidates and playbook runs.
CREATE TABLE IF NOT EXISTS proactive_signal_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    conversation_id TEXT,
    appointment_id TEXT,
    payment_id TEXT,
    lead_id TEXT,
    signal_key TEXT NOT NULL,
    signal_family TEXT NOT NULL,
    strength_score REAL NOT NULL DEFAULT 0,
    facts_json TEXT NOT NULL DEFAULT '{}',
    event_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_proactive_signal_events_contact ON proactive_signal_events(organization_id, bot_id, contact_id, event_at DESC);
CREATE INDEX IF NOT EXISTS idx_proactive_signal_events_signal ON proactive_signal_events(signal_key, event_at DESC);

CREATE TABLE IF NOT EXISTS proactive_contact_candidates (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    conversation_id TEXT,
    appointment_id TEXT,
    payment_id TEXT,
    lead_id TEXT,
    signal_event_id TEXT,
    signal_key TEXT NOT NULL,
    signal_family TEXT NOT NULL,
    playbook_id TEXT NOT NULL,
    playbook_version_id TEXT NOT NULL,
    specialist_agent_key TEXT NOT NULL,
    policy_profile_key TEXT,
    policy_profile_version TEXT,
    objective TEXT NOT NULL,
    recommended_action TEXT,
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    priority_score REAL NOT NULL DEFAULT 0,
    priority_band TEXT NOT NULL DEFAULT 'medium',
    eligible INTEGER NOT NULL DEFAULT 1,
    suppression_reason TEXT,
    suggested_send_at TEXT,
    title TEXT,
    message_text TEXT,
    timing_policy_id TEXT,
    nba_policy_id TEXT,
    policy_json TEXT NOT NULL DEFAULT '{}',
    reasoning_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    candidate_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(candidate_key)
);
CREATE INDEX IF NOT EXISTS idx_proactive_contact_candidates_org ON proactive_contact_candidates(organization_id, bot_id, status, priority_score DESC, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_proactive_contact_candidates_contact ON proactive_contact_candidates(contact_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_proactive_contact_candidates_specialist ON proactive_contact_candidates(specialist_agent_key, priority_score DESC);

CREATE TABLE IF NOT EXISTS proactive_playbook_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    conversation_id TEXT,
    appointment_id TEXT,
    payment_id TEXT,
    lead_id TEXT,
    specialist_agent_key TEXT NOT NULL,
    playbook_id TEXT NOT NULL,
    playbook_version_id TEXT NOT NULL,
    objective TEXT NOT NULL,
    recommended_action TEXT,
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    status TEXT NOT NULL DEFAULT 'materialized',
    scheduled_for TEXT,
    message_text TEXT,
    action_payload_json TEXT NOT NULL DEFAULT '{}',
    outcome_exposure_id TEXT,
    tool_execution_run_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_proactive_playbook_runs_org ON proactive_playbook_runs(organization_id, bot_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_proactive_playbook_runs_contact ON proactive_playbook_runs(contact_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_proactive_playbook_runs_playbook ON proactive_playbook_runs(playbook_id, created_at DESC);
