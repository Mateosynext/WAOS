CREATE TABLE IF NOT EXISTS organization_branding (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL UNIQUE,
    business_name TEXT NOT NULL DEFAULT '',
    legal_name TEXT,
    logo_url TEXT,
    primary_color TEXT NOT NULL DEFAULT '#25D366',
    secondary_color TEXT NOT NULL DEFAULT '#111827',
    phone TEXT,
    whatsapp TEXT,
    email TEXT,
    website TEXT,
    address TEXT,
    footer_note TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);
CREATE INDEX IF NOT EXISTS idx_organization_branding_org ON organization_branding(organization_id);

CREATE TABLE IF NOT EXISTS commercial_document_templates (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    name TEXT NOT NULL,
    layout TEXT NOT NULL DEFAULT 'premium',
    default_terms TEXT,
    default_footer TEXT,
    variables_json TEXT NOT NULL DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);
CREATE INDEX IF NOT EXISTS idx_commercial_templates_org_type ON commercial_document_templates(organization_id, document_type, is_active);

CREATE TABLE IF NOT EXISTS commercial_documents (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    conversation_id TEXT,
    contact_id TEXT,
    template_id TEXT,
    document_type TEXT NOT NULL DEFAULT 'quote',
    folio TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    title TEXT NOT NULL,
    customer_name TEXT,
    customer_phone TEXT,
    customer_email TEXT,
    customer_address TEXT,
    summary TEXT,
    currency TEXT NOT NULL DEFAULT 'MXN',
    subtotal REAL NOT NULL DEFAULT 0,
    discount_total REAL NOT NULL DEFAULT 0,
    tax_total REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    deposit_required REAL NOT NULL DEFAULT 0,
    balance_due REAL NOT NULL DEFAULT 0,
    valid_until TEXT,
    accepted_at TEXT,
    paid_at TEXT,
    sent_at TEXT,
    pdf_path TEXT,
    pdf_filename TEXT,
    pdf_generated_at TEXT,
    public_url TEXT,
    payment_url TEXT,
    terms TEXT,
    notes TEXT,
    missing_questions_json TEXT NOT NULL DEFAULT '[]',
    approval_reasons_json TEXT NOT NULL DEFAULT '[]',
    next_actions_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_by_user_id TEXT,
    approved_by_user_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (template_id) REFERENCES commercial_document_templates(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_commercial_documents_org_folio ON commercial_documents(organization_id, folio);
CREATE INDEX IF NOT EXISTS idx_commercial_documents_org_status ON commercial_documents(organization_id, document_type, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_commercial_documents_conversation ON commercial_documents(conversation_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS commercial_document_items (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'custom',
    source_id TEXT,
    name TEXT NOT NULL,
    description TEXT,
    quantity REAL NOT NULL DEFAULT 1,
    unit TEXT NOT NULL DEFAULT 'unidad',
    unit_price REAL NOT NULL DEFAULT 0,
    discount REAL NOT NULL DEFAULT 0,
    tax REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (document_id) REFERENCES commercial_documents(id)
);
CREATE INDEX IF NOT EXISTS idx_commercial_document_items_doc ON commercial_document_items(document_id, sort_order);

CREATE TABLE IF NOT EXISTS commercial_document_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL DEFAULT 'system',
    actor_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (document_id) REFERENCES commercial_documents(id)
);
CREATE INDEX IF NOT EXISTS idx_commercial_document_events_doc ON commercial_document_events(document_id, created_at DESC);

CREATE TABLE IF NOT EXISTS catalog_quote_rules (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    catalog_item_type TEXT NOT NULL,
    catalog_item_id TEXT NOT NULL,
    pricing_model TEXT NOT NULL DEFAULT 'fixed',
    unit_label TEXT NOT NULL DEFAULT 'unidad',
    base_price REAL,
    minimum_quantity REAL NOT NULL DEFAULT 1,
    travel_fee REAL NOT NULL DEFAULT 0,
    urgency_modifier_percent REAL NOT NULL DEFAULT 0,
    deposit_percent REAL NOT NULL DEFAULT 0,
    required_questions_json TEXT NOT NULL DEFAULT '[]',
    approval_rules_json TEXT NOT NULL DEFAULT '{}',
    terms TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_quote_rules_item ON catalog_quote_rules(organization_id, catalog_item_type, catalog_item_id, is_active);
