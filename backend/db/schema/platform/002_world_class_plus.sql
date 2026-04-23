CREATE TABLE IF NOT EXISTS defensive_rate_limit_windows (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            scope_key TEXT NOT NULL UNIQUE,
            channel TEXT,
            direction TEXT,
            window_started_at TEXT NOT NULL,
            window_seconds INTEGER NOT NULL,
            max_events INTEGER NOT NULL,
            events_used INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_defensive_rate_limit_org ON defensive_rate_limit_windows(organization_id, channel, updated_at DESC);

        CREATE TABLE IF NOT EXISTS immutable_audit_chain (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            previous_hash TEXT,
            entry_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_immutable_audit_chain_org ON immutable_audit_chain(organization_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS deletion_workflows (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            subject_type TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            requested_by TEXT,
            reason TEXT,
            target_stores_json TEXT NOT NULL DEFAULT '[]',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'planned',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, subject_type, subject_id)
        );
        CREATE INDEX IF NOT EXISTS idx_deletion_workflows_org ON deletion_workflows(organization_id, status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS compliance_postures (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL UNIQUE,
            data_region TEXT NOT NULL,
            backup_region TEXT NOT NULL,
            residency_mode TEXT NOT NULL DEFAULT 'regional',
            encryption_status TEXT NOT NULL DEFAULT 'enabled',
            encrypted_backups INTEGER NOT NULL DEFAULT 1,
            backup_last_tested_at TEXT,
            soc2_status TEXT NOT NULL DEFAULT 'readiness',
            iso27001_status TEXT NOT NULL DEFAULT 'readiness',
            controls_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_compliance_postures_org ON compliance_postures(organization_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS prompt_experiments (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            experiment_key TEXT NOT NULL,
            artifact_a_key TEXT NOT NULL,
            artifact_b_key TEXT NOT NULL,
            rollout_percentage INTEGER NOT NULL DEFAULT 50,
            status TEXT NOT NULL DEFAULT 'active',
            winner_variant TEXT,
            metrics_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, experiment_key)
        );
        CREATE INDEX IF NOT EXISTS idx_prompt_experiments_org ON prompt_experiments(organization_id, bot_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS chaos_test_runs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            scenario_key TEXT NOT NULL,
            target TEXT NOT NULL,
            blast_radius TEXT NOT NULL DEFAULT 'low',
            status TEXT NOT NULL DEFAULT 'planned',
            findings_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_chaos_test_runs_org ON chaos_test_runs(organization_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS load_test_runs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            scenario_key TEXT NOT NULL,
            target_rps INTEGER NOT NULL DEFAULT 0,
            peak_rps INTEGER NOT NULL DEFAULT 0,
            p95_ms INTEGER NOT NULL DEFAULT 0,
            error_rate REAL NOT NULL DEFAULT 0,
            queue_depth INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'planned',
            findings_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_load_test_runs_org ON load_test_runs(organization_id, created_at DESC);
