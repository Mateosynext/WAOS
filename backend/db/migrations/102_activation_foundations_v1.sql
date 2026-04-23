CREATE TABLE IF NOT EXISTS feature_flag_overrides (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    feature_key TEXT NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 0,
    rollout_stage TEXT NOT NULL DEFAULT 'pilot',
    note TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, bot_id, feature_key),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS product_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    actor_user_id TEXT,
    event_name TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    value_numeric REAL,
    value_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (actor_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS activation_progress (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL UNIQUE,
    bot_id TEXT,
    vertical TEXT,
    tenant_mode TEXT NOT NULL DEFAULT 'sandbox',
    activated_channels_count INTEGER NOT NULL DEFAULT 0,
    bots_ready_count INTEGER NOT NULL DEFAULT 0,
    catalog_items_count INTEGER NOT NULL DEFAULT 0,
    agenda_ready INTEGER NOT NULL DEFAULT 0,
    readiness_score INTEGER NOT NULL DEFAULT 0,
    first_value_at TEXT,
    ttfv_hours REAL,
    recommended_next_step TEXT,
    blockers_json TEXT NOT NULL DEFAULT '[]',
    checklist_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS inbox_saved_views (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    filter_json TEXT NOT NULL DEFAULT '{}',
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, user_id, slug),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_feature_flags_org_bot ON feature_flag_overrides(organization_id, bot_id, feature_key);
CREATE INDEX IF NOT EXISTS idx_product_events_org_name ON product_events(organization_id, event_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activation_progress_score ON activation_progress(organization_id, readiness_score DESC, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_inbox_saved_views_user ON inbox_saved_views(organization_id, user_id, is_default DESC, updated_at DESC);
