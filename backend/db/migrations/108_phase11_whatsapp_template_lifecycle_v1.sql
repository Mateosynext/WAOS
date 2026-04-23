CREATE TABLE IF NOT EXISTS whatsapp_templates (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    default_language TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    fallback_template_id TEXT,
    latest_version_id TEXT,
    approved_version_id TEXT,
    remote_template_id TEXT,
    last_sync_status TEXT NOT NULL DEFAULT 'draft',
    performance_score REAL NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, bot_id, name),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (fallback_template_id) REFERENCES whatsapp_templates(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_template_versions (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'draft',
    language_code TEXT NOT NULL,
    category TEXT NOT NULL,
    body_text TEXT NOT NULL,
    header_type TEXT NOT NULL DEFAULT 'NONE',
    header_text TEXT,
    footer_text TEXT,
    buttons_json TEXT NOT NULL DEFAULT '[]',
    variables_json TEXT NOT NULL DEFAULT '[]',
    assets_json TEXT NOT NULL DEFAULT '{}',
    sample_values_json TEXT NOT NULL DEFAULT '{}',
    lint_report_json TEXT NOT NULL DEFAULT '{}',
    coverage_json TEXT NOT NULL DEFAULT '{}',
    approval_status TEXT NOT NULL DEFAULT 'draft',
    remote_template_id TEXT,
    remote_status TEXT,
    remote_quality_rating TEXT,
    synced_at TEXT,
    published_at TEXT,
    rejection_reason TEXT,
    fallback_template_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(template_id, version_number),
    FOREIGN KEY (template_id) REFERENCES whatsapp_templates(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (fallback_template_id) REFERENCES whatsapp_templates(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_template_sync_runs (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'meta',
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    request_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    FOREIGN KEY (template_id) REFERENCES whatsapp_templates(id),
    FOREIGN KEY (version_id) REFERENCES whatsapp_template_versions(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_template_failovers (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    outbox_id TEXT,
    current_template_id TEXT,
    current_version_id TEXT,
    fallback_template_id TEXT,
    fallback_version_id TEXT,
    reason_code TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'runtime',
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (outbox_id) REFERENCES outbox_messages(id),
    FOREIGN KEY (current_template_id) REFERENCES whatsapp_templates(id),
    FOREIGN KEY (current_version_id) REFERENCES whatsapp_template_versions(id),
    FOREIGN KEY (fallback_template_id) REFERENCES whatsapp_templates(id),
    FOREIGN KEY (fallback_version_id) REFERENCES whatsapp_template_versions(id)
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_templates_org_bot ON whatsapp_templates(organization_id, bot_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_templates_status ON whatsapp_templates(status, last_sync_status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_template_versions_template ON whatsapp_template_versions(template_id, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_template_versions_approval ON whatsapp_template_versions(approval_status, remote_status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_template_sync_runs_template ON whatsapp_template_sync_runs(template_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_template_failovers_template ON whatsapp_template_failovers(organization_id, bot_id, created_at DESC);
