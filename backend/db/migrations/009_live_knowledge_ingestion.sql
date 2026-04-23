-- Continuous knowledge ingestion: source registry, watcher runs, publication logs.
CREATE TABLE IF NOT EXISTS knowledge_source_connections (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    source_key TEXT NOT NULL,
    connector_key TEXT NOT NULL,
    label TEXT NOT NULL,
    source_uri TEXT,
    owner_user_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    watch_mode TEXT NOT NULL DEFAULT 'manual',
    sync_interval_minutes INTEGER NOT NULL DEFAULT 60,
    publish_policy TEXT NOT NULL DEFAULT 'auto_publish',
    validation_policy_json TEXT NOT NULL DEFAULT '{}',
    config_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    current_snapshot_hash TEXT,
    last_seen_source_updated_at TEXT,
    last_synced_at TEXT,
    last_published_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, bot_id, source_key)
);


CREATE INDEX IF NOT EXISTS idx_knowledge_source_connections_bot ON knowledge_source_connections(organization_id, bot_id, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_source_sync_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    source_connection_id TEXT NOT NULL,
    trigger_kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    full_refresh INTEGER NOT NULL DEFAULT 1,
    validate_only INTEGER NOT NULL DEFAULT 0,
    items_seen INTEGER NOT NULL DEFAULT 0,
    items_published INTEGER NOT NULL DEFAULT 0,
    items_skipped INTEGER NOT NULL DEFAULT 0,
    items_invalidated INTEGER NOT NULL DEFAULT 0,
    snapshot_hash TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    error_text TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    FOREIGN KEY (source_connection_id) REFERENCES knowledge_source_connections(id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_source_sync_runs_source ON knowledge_source_sync_runs(source_connection_id, started_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_source_sync_items (
    id TEXT PRIMARY KEY,
    sync_run_id TEXT NOT NULL,
    source_connection_id TEXT NOT NULL,
    external_item_key TEXT NOT NULL,
    title TEXT,
    source_uri TEXT,
    validation_status TEXT NOT NULL DEFAULT 'passed',
    publication_state TEXT NOT NULL DEFAULT 'published',
    change_status TEXT NOT NULL DEFAULT 'unchanged',
    knowledge_document_id TEXT,
    knowledge_version_id TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (sync_run_id) REFERENCES knowledge_source_sync_runs(id),
    FOREIGN KEY (source_connection_id) REFERENCES knowledge_source_connections(id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_source_sync_items_run ON knowledge_source_sync_items(sync_run_id, created_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_source_publications (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    source_connection_id TEXT NOT NULL,
    external_item_key TEXT NOT NULL,
    knowledge_document_id TEXT,
    knowledge_version_id TEXT,
    source_kind TEXT NOT NULL,
    source_uri TEXT,
    state TEXT NOT NULL DEFAULT 'published',
    validation_status TEXT NOT NULL DEFAULT 'passed',
    owner_user_id TEXT,
    source_updated_at TEXT,
    published_at TEXT,
    last_synced_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_connection_id, external_item_key),
    FOREIGN KEY (source_connection_id) REFERENCES knowledge_source_connections(id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_source_publications_doc ON knowledge_source_publications(knowledge_document_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_source_publications_state ON knowledge_source_publications(source_connection_id, state, updated_at DESC);
