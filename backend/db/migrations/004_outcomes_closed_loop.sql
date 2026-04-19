CREATE TABLE IF NOT EXISTS outcome_exposures (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT,
    contact_id TEXT,
    lead_id TEXT,
    appointment_id TEXT,
    payment_id TEXT,
    message_id TEXT,
    source_type TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    prompt_run_id TEXT,
    prompt_version_id TEXT,
    flow_id TEXT,
    flow_version_id TEXT,
    template_id TEXT,
    template_version_id TEXT,
    routing_rule_id TEXT,
    decision_path_id TEXT,
    timing_policy_id TEXT,
    tone_policy_id TEXT,
    nba_policy_id TEXT,
    escalation_policy_id TEXT,
    playbook_id TEXT,
    playbook_version_id TEXT,
    handoff_id TEXT,
    handoff_kind TEXT,
    operator_user_id TEXT,
    assigned_variant TEXT,
    vertical TEXT,
    funnel_stage TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    sent_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id),
    FOREIGN KEY (payment_id) REFERENCES commerce_payments(id),
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (routing_rule_id) REFERENCES routing_rules(id)
);

CREATE TABLE IF NOT EXISTS outcome_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    conversation_id TEXT,
    contact_id TEXT,
    lead_id TEXT,
    appointment_id TEXT,
    payment_id TEXT,
    review_id TEXT,
    event_name TEXT NOT NULL,
    event_category TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    source_system TEXT NOT NULL,
    external_event_id TEXT,
    status TEXT NOT NULL DEFAULT 'recorded',
    value_number REAL,
    value_text TEXT,
    value_json TEXT NOT NULL DEFAULT '{}',
    operator_user_id TEXT,
    vertical TEXT,
    funnel_stage TEXT,
    dedupe_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id),
    FOREIGN KEY (payment_id) REFERENCES commerce_payments(id),
    FOREIGN KEY (review_id) REFERENCES conversation_reviews(id),
    UNIQUE(organization_id, dedupe_key)
);

CREATE TABLE IF NOT EXISTS outcome_attribution_facts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    outcome_event_id TEXT NOT NULL,
    exposure_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    attribution_model TEXT NOT NULL,
    attribution_window_hours INTEGER NOT NULL,
    attribution_weight REAL NOT NULL DEFAULT 1,
    contribution_value REAL NOT NULL DEFAULT 0,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (outcome_event_id) REFERENCES outcome_events(id),
    FOREIGN KEY (exposure_id) REFERENCES outcome_exposures(id)
);

CREATE TABLE IF NOT EXISTS outcome_scorecard_snapshots (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    scorecard_window TEXT NOT NULL,
    computed_at TEXT NOT NULL,
    traffic_count INTEGER NOT NULL DEFAULT 0,
    primary_metric TEXT NOT NULL,
    primary_metric_value REAL NOT NULL DEFAULT 0,
    outcome_score REAL NOT NULL DEFAULT 0,
    confidence_score REAL NOT NULL DEFAULT 0,
    guardrail_state TEXT NOT NULL DEFAULT 'pass',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    guardrails_json TEXT NOT NULL DEFAULT '{}',
    recommendation TEXT NOT NULL DEFAULT 'hold',
    rationale_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS outcome_optimization_decisions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    decision_source TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    previous_state_json TEXT NOT NULL DEFAULT '{}',
    new_state_json TEXT NOT NULL DEFAULT '{}',
    evidence_snapshot_json TEXT NOT NULL DEFAULT '{}',
    rollback_of_decision_id TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    applied_at TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (rollback_of_decision_id) REFERENCES outcome_optimization_decisions(id)
);

CREATE INDEX IF NOT EXISTS idx_outcome_exposures_org_bot ON outcome_exposures(organization_id, bot_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_exposures_conversation ON outcome_exposures(conversation_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_exposures_prompt_run ON outcome_exposures(prompt_run_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_exposures_prompt ON outcome_exposures(prompt_version_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_exposures_flow ON outcome_exposures(flow_version_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_exposures_template ON outcome_exposures(template_version_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_exposures_vertical_stage ON outcome_exposures(vertical, funnel_stage, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_events_org_category ON outcome_events(organization_id, event_category, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_events_conversation ON outcome_events(conversation_id, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_events_contact ON outcome_events(contact_id, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_events_name ON outcome_events(event_name, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_attribution_entity ON outcome_attribution_facts(entity_type, entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_attribution_event ON outcome_attribution_facts(outcome_event_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_scorecards_entity ON outcome_scorecard_snapshots(organization_id, entity_type, entity_id, computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_scorecards_window ON outcome_scorecard_snapshots(scorecard_window, computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_decisions_entity ON outcome_optimization_decisions(organization_id, entity_type, entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_decisions_status ON outcome_optimization_decisions(status, created_at DESC);
