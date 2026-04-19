CREATE TABLE IF NOT EXISTS legal_acceptance_events (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL,
    version TEXT NOT NULL,
    acceptance_type TEXT NOT NULL DEFAULT 'other',
    subject_type TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    organization_id TEXT,
    contact_id TEXT,
    user_id TEXT,
    source TEXT NOT NULL DEFAULT 'product',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS legal_consent_records (
    id TEXT PRIMARY KEY,
    subject_type TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    organization_id TEXT,
    contact_id TEXT,
    user_id TEXT,
    consent_key TEXT NOT NULL,
    status TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0',
    categories_json TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'product',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(subject_type, subject_key, consent_key)
);

CREATE TABLE IF NOT EXISTS privacy_requests (
    id TEXT PRIMARY KEY,
    request_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'received',
    requester_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    organization_id TEXT,
    contact_id TEXT,
    country TEXT,
    message TEXT,
    source TEXT NOT NULL DEFAULT 'privacy_center',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    requested_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS legal_audit_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    subject_type TEXT,
    subject_key TEXT,
    actor_type TEXT,
    actor_id TEXT,
    request_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_legal_acceptance_subject ON legal_acceptance_events(subject_type, subject_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_legal_acceptance_slug ON legal_acceptance_events(slug, version, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_legal_consent_subject ON legal_consent_records(subject_type, subject_key, consent_key, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_privacy_requests_status ON privacy_requests(status, requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_legal_audit_events_subject ON legal_audit_events(subject_type, subject_key, created_at DESC);
