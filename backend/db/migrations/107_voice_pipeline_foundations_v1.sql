CREATE TABLE IF NOT EXISTS voice_media_assets (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT,
    message_id TEXT,
    voice_note_id TEXT,
    direction TEXT NOT NULL,
    provider TEXT NOT NULL,
    media_role TEXT NOT NULL,
    provider_media_id TEXT,
    storage_path TEXT,
    public_url TEXT,
    mime_type TEXT,
    sha256 TEXT,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    expires_at TEXT,
    consent_status TEXT NOT NULL DEFAULT 'implicit_inbound_whatsapp',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (voice_note_id) REFERENCES voice_notes(id)
);

CREATE TABLE IF NOT EXISTS voice_processing_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    contact_id TEXT,
    message_id TEXT,
    voice_note_id TEXT,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (voice_note_id) REFERENCES voice_notes(id)
);

CREATE INDEX IF NOT EXISTS idx_voice_notes_conversation ON voice_notes(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_notes_processing ON voice_notes(organization_id, processing_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_media_assets_org ON voice_media_assets(organization_id, media_role, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_processing_events_org ON voice_processing_events(organization_id, stage, created_at DESC);
