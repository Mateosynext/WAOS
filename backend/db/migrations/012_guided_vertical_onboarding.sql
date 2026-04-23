-- phase 22: guided vertical onboarding wizard
CREATE TABLE IF NOT EXISTS vertical_onboarding_wizards (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    vertical_id TEXT NOT NULL,
    subvertical TEXT,
    wizard_version TEXT NOT NULL DEFAULT 'guided_vertical_onboarding_v1',
    status TEXT NOT NULL DEFAULT 'draft',
    current_step TEXT,
    progress_percent INTEGER NOT NULL DEFAULT 0,
    business_name TEXT,
    bot_name TEXT,
    tone TEXT,
    language TEXT,
    timezone TEXT,
    primary_objective TEXT,
    answers_json TEXT NOT NULL DEFAULT '{}',
    setup_json TEXT NOT NULL DEFAULT '{}',
    checklist_json TEXT NOT NULL DEFAULT '[]',
    recommended_integrations_json TEXT NOT NULL DEFAULT '[]',
    recommended_playbooks_json TEXT NOT NULL DEFAULT '[]',
    recommended_ctas_json TEXT NOT NULL DEFAULT '[]',
    applied_summary_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    applied_at TEXT
);

CREATE TABLE IF NOT EXISTS vertical_onboarding_step_runs (
    id TEXT PRIMARY KEY,
    wizard_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    step_key TEXT NOT NULL,
    step_status TEXT NOT NULL DEFAULT 'pending',
    is_required INTEGER NOT NULL DEFAULT 1,
    payload_json TEXT NOT NULL DEFAULT '{}',
    generated_patch_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE(wizard_id, step_key)
);

CREATE INDEX IF NOT EXISTS idx_vertical_onboarding_wizards_org ON vertical_onboarding_wizards(organization_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_vertical_onboarding_wizards_bot ON vertical_onboarding_wizards(bot_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_vertical_onboarding_step_runs_wizard ON vertical_onboarding_step_runs(wizard_id, step_key);


CREATE TABLE IF NOT EXISTS vertical_onboarding_wizard_events (
    id TEXT PRIMARY KEY,
    wizard_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    event_type TEXT NOT NULL,
    step_key TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (wizard_id) REFERENCES vertical_onboarding_wizards(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);
CREATE INDEX IF NOT EXISTS idx_vertical_onboarding_wizard_events_wizard ON vertical_onboarding_wizard_events(wizard_id, created_at DESC);
