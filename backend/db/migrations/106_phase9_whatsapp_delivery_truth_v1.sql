CREATE TABLE IF NOT EXISTS whatsapp_delivery_status_facts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    conversation_id TEXT,
    outbox_id TEXT,
    message_id TEXT,
    provider_message_id TEXT NOT NULL,
    phone_number_id TEXT,
    recipient_id TEXT,
    status TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'webhook',
    pricing_json TEXT NOT NULL DEFAULT '{}',
    error_code INTEGER,
    error_message TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    event_fingerprint TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (outbox_id) REFERENCES outbox_messages(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_delivery_projection (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    conversation_id TEXT,
    contact_id TEXT,
    outbox_id TEXT,
    message_id TEXT,
    provider_message_id TEXT NOT NULL UNIQUE,
    phone_number_id TEXT,
    recipient_id TEXT,
    template_name TEXT,
    message_kind TEXT NOT NULL DEFAULT 'text',
    vertical TEXT,
    accepted_at TEXT,
    sent_at TEXT,
    delivered_at TEXT,
    read_at TEXT,
    failed_at TEXT,
    current_status TEXT NOT NULL DEFAULT 'accepted',
    first_event_at TEXT,
    last_event_at TEXT,
    last_error_code INTEGER,
    last_error_message TEXT,
    pricing_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (outbox_id) REFERENCES outbox_messages(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_delivery_facts_provider ON whatsapp_delivery_status_facts(provider_message_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_delivery_facts_org ON whatsapp_delivery_status_facts(organization_id, status, observed_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_delivery_projection_org ON whatsapp_delivery_projection(organization_id, current_status, accepted_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_delivery_projection_number ON whatsapp_delivery_projection(phone_number_id, accepted_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_delivery_projection_template ON whatsapp_delivery_projection(template_name, accepted_at);
