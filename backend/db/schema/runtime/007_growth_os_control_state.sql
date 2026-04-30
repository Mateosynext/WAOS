-- 007_growth_os_control_state.sql
-- Cumulative schema slice for WAOS production hardened artifact.

CREATE TABLE IF NOT EXISTS growth_os_control_states (
    id TEXT PRIMARY KEY,
    auto_execute TEXT,
    bot_id TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    contact_focus_hours TEXT,
    created_at TEXT,
    cycle_interval_minutes INTEGER NOT NULL DEFAULT 0,
    default_goals_json TEXT NOT NULL DEFAULT '{}',
    include_suppressed TEXT,
    is_enabled INTEGER NOT NULL DEFAULT 0,
    last_completed_at TEXT,
    last_started_at TEXT,
    last_status TEXT,
    last_summary_json TEXT NOT NULL DEFAULT '{}',
    latest_run_id TEXT,
    max_targets TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    next_scheduled_at TEXT,
    organization_id TEXT,
    prioritize_handoffs TEXT,
    prioritize_playbooks TEXT,
    prioritize_specialist TEXT,
    prioritize_tools TEXT,
    scheduler_enabled INTEGER NOT NULL DEFAULT 0,
    scheduler_mode TEXT,
    scorecard_window REAL NOT NULL DEFAULT 0,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS growth_os_runs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    decision_policy_json TEXT NOT NULL DEFAULT '{}',
    goals_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    mode TEXT,
    organization_id TEXT,
    status TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS growth_os_targets (
    id TEXT PRIMARY KEY,
    action_type TEXT,
    bot_id TEXT,
    candidate_id TEXT,
    channel TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    expected_value TEXT,
    goal TEXT,
    growth_run_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    objective TEXT,
    organization_id TEXT,
    priority_score REAL NOT NULL DEFAULT 0,
    proactive_run_id TEXT,
    scorecard_json TEXT NOT NULL DEFAULT '{}',
    specialist_agent_key TEXT,
    status TEXT,
    timing_decision TEXT,
    updated_at TEXT
);

