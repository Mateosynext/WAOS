CREATE TABLE IF NOT EXISTS conversation_internal_notes (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    message_id TEXT,
    author_user_id TEXT,
    category TEXT NOT NULL DEFAULT 'general',
    priority TEXT NOT NULL DEFAULT 'normal',
    visibility TEXT NOT NULL DEFAULT 'internal',
    summary TEXT NOT NULL,
    detail TEXT,
    next_steps_json TEXT NOT NULL DEFAULT '[]',
    sources_json TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT NOT NULL DEFAULT 'low',
    risk_flags_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (author_user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_internal_notes_conversation ON conversation_internal_notes(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_internal_notes_org_category ON conversation_internal_notes(organization_id, category, created_at DESC);

CREATE TABLE IF NOT EXISTS conversation_takeover_briefs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    brief_type TEXT NOT NULL,
    content_json TEXT NOT NULL DEFAULT '{}',
    generated_by TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (generated_by) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_takeover_briefs_conversation ON conversation_takeover_briefs(conversation_id, created_at DESC);

CREATE TABLE IF NOT EXISTS human_reply_suggestions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    operator_user_id TEXT,
    objective TEXT NOT NULL DEFAULT 'reply',
    draft_text TEXT,
    suggestion_text TEXT NOT NULL,
    explanation_json TEXT NOT NULL DEFAULT '{}',
    sources_json TEXT NOT NULL DEFAULT '[]',
    risk_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'suggested',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (operator_user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_reply_suggestions_conversation ON human_reply_suggestions(conversation_id, created_at DESC);

CREATE TABLE IF NOT EXISTS supervisor_console_snapshots (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    summary_json TEXT NOT NULL DEFAULT '{}',
    teams_json TEXT NOT NULL DEFAULT '[]',
    qa_json TEXT NOT NULL DEFAULT '{}',
    failed_takeovers_json TEXT NOT NULL DEFAULT '[]',
    created_by TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_supervisor_console_snapshots_org ON supervisor_console_snapshots(organization_id, created_at DESC);

CREATE TABLE IF NOT EXISTS coaching_recommendations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    source_kind TEXT NOT NULL DEFAULT 'qa_loop',
    summary TEXT NOT NULL,
    recommendation_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);
CREATE INDEX IF NOT EXISTS idx_coaching_recommendations_org ON coaching_recommendations(organization_id, target_type, status, updated_at DESC);
