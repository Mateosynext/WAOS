CREATE TABLE IF NOT EXISTS pipeline_stage_metrics (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            bot_id TEXT,
            conversation_id TEXT,
            trace_id TEXT,
            correlation_id TEXT,
            vertical TEXT,
            source_type TEXT,
            stage_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ok',
            duration_ms INTEGER,
            metrics_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_pipeline_stage_metrics_stage ON pipeline_stage_metrics(organization_id, bot_id, stage_name, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_pipeline_stage_metrics_trace ON pipeline_stage_metrics(trace_id, created_at ASC);

        CREATE TABLE IF NOT EXISTS queue_depth_samples (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            jobs_depth INTEGER NOT NULL DEFAULT 0,
            outbox_depth INTEGER NOT NULL DEFAULT 0,
            integration_depth INTEGER NOT NULL DEFAULT 0,
            callbacks_depth INTEGER NOT NULL DEFAULT 0,
            total_depth INTEGER NOT NULL DEFAULT 0,
            oldest_age_seconds INTEGER NOT NULL DEFAULT 0,
            sampled_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_queue_depth_samples_org ON queue_depth_samples(organization_id, sampled_at DESC);

        CREATE TABLE IF NOT EXISTS alert_rules_v14 (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            name TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            comparator TEXT NOT NULL,
            threshold_value REAL NOT NULL,
            window_minutes INTEGER NOT NULL DEFAULT 10,
            notify_channels_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'active',
            config_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_alert_rules_v14_org ON alert_rules_v14(organization_id, status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS alert_events (
            id TEXT PRIMARY KEY,
            rule_id TEXT,
            organization_id TEXT,
            bot_id TEXT,
            metric_key TEXT NOT NULL,
            comparator TEXT,
            threshold_value REAL,
            observed_value REAL,
            window_started_at TEXT,
            window_ended_at TEXT,
            status TEXT NOT NULL DEFAULT 'triggered',
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_alert_events_org ON alert_events(organization_id, metric_key, created_at DESC);
