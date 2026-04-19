CREATE TABLE IF NOT EXISTS whatsapp_opt_outs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    contact_id TEXT,
    conversation_id TEXT,
    phone TEXT,
    keyword TEXT NOT NULL,
    source_message_id TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (source_message_id) REFERENCES messages(id)
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_opt_outs_bot_contact
ON whatsapp_opt_outs(organization_id, bot_id, contact_id, active, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_whatsapp_opt_outs_bot_phone
ON whatsapp_opt_outs(organization_id, bot_id, phone, active, updated_at DESC);
