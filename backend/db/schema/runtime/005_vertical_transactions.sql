CREATE TABLE IF NOT EXISTS vertical_transaction_accounts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    contact_id TEXT,
    vertical_id TEXT NOT NULL,
    aggregate_root TEXT NOT NULL,
    main_business_entity TEXT NOT NULL,
    transaction_unit TEXT NOT NULL,
    external_reference TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    commercial_status TEXT,
    operations_status TEXT,
    finance_status TEXT,
    continuity_status TEXT,
    last_command TEXT,
    last_event TEXT,
    quote_status TEXT,
    booking_status TEXT,
    execution_status TEXT,
    payment_status TEXT,
    continuity_plan_status TEXT,
    amount_expected REAL NOT NULL DEFAULT 0,
    amount_collected REAL NOT NULL DEFAULT 0,
    amount_outstanding REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'MXN',
    profile_json TEXT NOT NULL DEFAULT '{}',
    state_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT,
    UNIQUE(organization_id, vertical_id, external_reference)
);
CREATE INDEX IF NOT EXISTS idx_vtx_accounts_org ON vertical_transaction_accounts(organization_id, vertical_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_vtx_accounts_bot ON vertical_transaction_accounts(bot_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_commands (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    command_name TEXT NOT NULL,
    command_key TEXT NOT NULL,
    actor_user_id TEXT,
    actor_type TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    processed_at TEXT,
    UNIQUE(organization_id, account_id, command_key),
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_commands_account ON vertical_transaction_commands(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    event_name TEXT NOT NULL,
    command_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id),
    FOREIGN KEY (command_id) REFERENCES vertical_transaction_commands(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_events_account ON vertical_transaction_events(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_ledger (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'MXN',
    reference_type TEXT,
    reference_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_ledger_account ON vertical_transaction_ledger(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_documents (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    document_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    signed_at TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, document_name),
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_docs_account ON vertical_transaction_documents(account_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_resources (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_reference TEXT,
    status TEXT NOT NULL DEFAULT 'reserved',
    starts_at TEXT,
    ends_at TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_resources_account ON vertical_transaction_resources(account_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_views (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    view_name TEXT NOT NULL,
    summary TEXT,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    payload_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, view_name),
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_views_account ON vertical_transaction_views(account_id, updated_at DESC);
