CREATE TABLE IF NOT EXISTS vertical_marketplace_packages (
    id TEXT PRIMARY KEY,
    package_slug TEXT NOT NULL UNIQUE,
    package_type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    vertical_key TEXT,
    subvertical TEXT,
    publisher_type TEXT NOT NULL DEFAULT 'core',
    publisher_user_id TEXT,
    publisher_org_id TEXT,
    monetization_model TEXT NOT NULL DEFAULT 'internal',
    price_amount REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL DEFAULT 'draft',
    latest_version_id TEXT,
    compatibility_json TEXT NOT NULL DEFAULT '{}',
    dependencies_json TEXT NOT NULL DEFAULT '[]',
    metrics_expected_json TEXT NOT NULL DEFAULT '{}',
    manifest_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vertical_marketplace_package_versions (
    id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL,
    version TEXT NOT NULL,
    release_notes TEXT,
    status TEXT NOT NULL DEFAULT 'published',
    bundle_json TEXT NOT NULL DEFAULT '{}',
    compatibility_json TEXT NOT NULL DEFAULT '{}',
    dependencies_json TEXT NOT NULL DEFAULT '[]',
    checklist_json TEXT NOT NULL DEFAULT '[]',
    metrics_expected_json TEXT NOT NULL DEFAULT '{}',
    published_at TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT,
    UNIQUE(package_id, version)
);

CREATE TABLE IF NOT EXISTS vertical_marketplace_installs (
    id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL,
    package_version_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    install_scope TEXT NOT NULL DEFAULT 'organization',
    status TEXT NOT NULL DEFAULT 'installed',
    compatibility_snapshot_json TEXT NOT NULL DEFAULT '{}',
    installed_manifest_json TEXT NOT NULL DEFAULT '{}',
    install_summary_json TEXT NOT NULL DEFAULT '{}',
    current_version TEXT NOT NULL,
    source_channel TEXT NOT NULL DEFAULT 'marketplace',
    upgrade_available INTEGER NOT NULL DEFAULT 0,
    installed_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    installed_by TEXT
);

CREATE TABLE IF NOT EXISTS vertical_marketplace_install_items (
    id TEXT PRIMARY KEY,
    install_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    item_type TEXT NOT NULL,
    item_key TEXT NOT NULL,
    entity_id TEXT,
    status TEXT NOT NULL DEFAULT 'installed',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vertical_marketplace_upgrade_runs (
    id TEXT PRIMARY KEY,
    install_id TEXT NOT NULL,
    package_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    from_version TEXT NOT NULL,
    to_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    plan_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    executed_at TEXT,
    executed_by TEXT
);
