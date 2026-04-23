CREATE TABLE IF NOT EXISTS optimizer_cycles (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    mode TEXT NOT NULL DEFAULT 'auto',
    targets_json TEXT NOT NULL DEFAULT '[]',
    scorecard_window TEXT NOT NULL DEFAULT '28d',
    status TEXT NOT NULL DEFAULT 'planned',
    summary_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_optimizer_cycles_org ON optimizer_cycles(organization_id, bot_id, created_at DESC);

CREATE TABLE IF NOT EXISTS optimizer_proposals (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    cycle_id TEXT NOT NULL,
    target_name TEXT NOT NULL,
    proposal_kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    champion_entity_type TEXT,
    champion_entity_id TEXT,
    challenger_entity_type TEXT,
    challenger_entity_id TEXT,
    summary TEXT NOT NULL,
    rationale_json TEXT NOT NULL DEFAULT '{}',
    change_set_json TEXT NOT NULL DEFAULT '{}',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    applied_decision_id TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_optimizer_proposals_org ON optimizer_proposals(organization_id, bot_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_optimizer_proposals_cycle ON optimizer_proposals(cycle_id, created_at DESC);

CREATE TABLE IF NOT EXISTS optimizer_experiments (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    proposal_id TEXT NOT NULL,
    experiment_key TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'shadow',
    status TEXT NOT NULL DEFAULT 'planned',
    champion_entity_type TEXT,
    champion_entity_id TEXT,
    candidate_entity_type TEXT,
    candidate_entity_id TEXT,
    rollout_percentage INTEGER NOT NULL DEFAULT 0,
    guardrails_json TEXT NOT NULL DEFAULT '{}',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, experiment_key)
);
CREATE INDEX IF NOT EXISTS idx_optimizer_experiments_org ON optimizer_experiments(organization_id, bot_id, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS optimizer_control_states (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    target_name TEXT NOT NULL,
    current_state_json TEXT NOT NULL DEFAULT '{}',
    last_decision_action TEXT,
    updated_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_optimizer_control_states_org ON optimizer_control_states(organization_id, bot_id, updated_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_optimizer_control_states_unique ON optimizer_control_states(organization_id, COALESCE(bot_id, ''), target_name);

CREATE TABLE IF NOT EXISTS optimizer_change_audits (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    proposal_id TEXT,
    experiment_id TEXT,
    decision_id TEXT,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_optimizer_change_audits_org ON optimizer_change_audits(organization_id, bot_id, created_at DESC);
