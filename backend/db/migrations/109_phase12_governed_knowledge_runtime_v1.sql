CREATE TABLE IF NOT EXISTS knowledge_documents (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    title TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_uri TEXT,
    source_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    owner_type TEXT NOT NULL DEFAULT 'system',
    refresh_strategy TEXT NOT NULL DEFAULT 'manual',
    refresh_after TEXT,
    freshness_window_days INTEGER NOT NULL DEFAULT 30,
    current_version_id TEXT,
    invalidated_reason TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, bot_id, source_key)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_bot_domain ON knowledge_documents(organization_id, bot_id, domain, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_refresh ON knowledge_documents(organization_id, bot_id, status, refresh_after);

CREATE TABLE IF NOT EXISTS knowledge_document_versions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    content_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    vector_json TEXT NOT NULL DEFAULT '{}',
    source_snapshot_json TEXT NOT NULL DEFAULT '{}',
    supports_json TEXT NOT NULL DEFAULT '[]',
    extracted_entities_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    is_current INTEGER NOT NULL DEFAULT 1,
    freshness_status TEXT NOT NULL DEFAULT 'fresh',
    created_at TEXT NOT NULL,
    UNIQUE(document_id, version_number)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_document_versions_doc ON knowledge_document_versions(document_id, is_current, created_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_refresh_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    freshness_before TEXT,
    freshness_after TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_knowledge_refresh_events_doc ON knowledge_refresh_events(document_id, created_at DESC);
