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

CREATE INDEX IF NOT EXISTS idx_assignment_history_conv ON conversation_assignment_history(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assignment_history_org_user ON conversation_assignment_history(organization_id, new_assigned_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sim_cases_bot ON bot_simulation_cases(bot_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sim_runs_bot ON bot_simulation_runs(bot_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_capacity_rules_resource_day ON agenda_resource_capacity_rules(resource_id, day_of_week, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_appointment_resource_assignments_resource ON appointment_resource_assignments(resource_id, updated_at DESC);
