CREATE TABLE IF NOT EXISTS talent_candidates (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            conversation_id TEXT,
            contact_id TEXT NOT NULL,
            vacancy_id TEXT,
            vacancy_title TEXT,
            status TEXT NOT NULL DEFAULT 'interview_confirmed',
            source TEXT NOT NULL DEFAULT 'bot',
            interview_confirmed_at TEXT,
            profile_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(bot_id, contact_id, vacancy_id)
        );
        CREATE INDEX IF NOT EXISTS idx_talent_candidates_bot ON talent_candidates(bot_id, status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_talent_candidates_org ON talent_candidates(organization_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_talent_candidates_contact ON talent_candidates(contact_id, updated_at DESC);
