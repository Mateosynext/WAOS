CREATE TABLE IF NOT EXISTS provider_circuit_breakers (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            circuit_key TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'closed',
            consecutive_failures INTEGER NOT NULL DEFAULT 0,
            failure_threshold INTEGER NOT NULL DEFAULT 3,
            opened_at TEXT,
            half_open_after TEXT,
            last_error TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(provider, circuit_key)
        );
        CREATE INDEX IF NOT EXISTS idx_circuit_breakers_provider ON provider_circuit_breakers(provider, state, updated_at DESC);

        CREATE TABLE IF NOT EXISTS retry_budget_windows (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            scope_key TEXT NOT NULL,
            window_started_at TEXT NOT NULL,
            window_seconds INTEGER NOT NULL,
            max_retries INTEGER NOT NULL,
            retries_used INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(provider, scope_key)
        );
        CREATE INDEX IF NOT EXISTS idx_retry_budget_provider ON retry_budget_windows(provider, updated_at DESC);

        CREATE TABLE IF NOT EXISTS dead_letter_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            channel TEXT NOT NULL,
            source_table TEXT NOT NULL,
            source_id TEXT NOT NULL,
            reason_code TEXT NOT NULL,
            payload_snapshot_json TEXT NOT NULL DEFAULT '{}',
            error_json TEXT NOT NULL DEFAULT '{}',
            quarantined_until TEXT,
            replay_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source_table, source_id)
        );
        CREATE INDEX IF NOT EXISTS idx_dead_letter_events_org ON dead_letter_events(organization_id, channel, created_at DESC);

        CREATE TABLE IF NOT EXISTS ai_cache_entries (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            bot_id TEXT,
            cache_scope TEXT NOT NULL,
            cache_type TEXT NOT NULL,
            cache_key TEXT NOT NULL UNIQUE,
            prompt_hash TEXT NOT NULL,
            canonical_prompt TEXT NOT NULL,
            response_text TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            hit_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ai_cache_scope ON ai_cache_entries(organization_id, bot_id, cache_type, updated_at DESC);

        CREATE TABLE IF NOT EXISTS ai_usage_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            bot_id TEXT,
            conversation_id TEXT,
            model TEXT NOT NULL,
            operation TEXT NOT NULL,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            estimated_cost REAL NOT NULL DEFAULT 0,
            latency_ms INTEGER,
            cache_hit INTEGER NOT NULL DEFAULT 0,
            fallback_source TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ai_usage_events_org ON ai_usage_events(organization_id, bot_id, operation, created_at DESC);

        CREATE TABLE IF NOT EXISTS memory_vectors (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            contact_id TEXT,
            bot_id TEXT,
            scope TEXT NOT NULL,
            content_text TEXT NOT NULL,
            vector_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            score REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memory_vectors_scope ON memory_vectors(organization_id, contact_id, bot_id, scope, updated_at DESC);

        CREATE TABLE IF NOT EXISTS memory_episodes (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            contact_id TEXT,
            bot_id TEXT,
            conversation_id TEXT,
            source_message_id TEXT,
            episode_type TEXT NOT NULL,
            session_key TEXT,
            summary_text TEXT NOT NULL,
            vector_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            score REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memory_episodes_scope ON memory_episodes(organization_id, contact_id, bot_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_memory_episodes_conversation ON memory_episodes(conversation_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS knowledge_query_cache (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            query_hash TEXT NOT NULL,
            query_text TEXT NOT NULL,
            result_json TEXT NOT NULL DEFAULT '[]',
            hit_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT,
            UNIQUE(organization_id, bot_id, query_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_query_cache_scope ON knowledge_query_cache(organization_id, bot_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS knowledge_embeddings (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            knowledge_type TEXT NOT NULL,
            source_key TEXT NOT NULL,
            content_text TEXT NOT NULL,
            vector_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(bot_id, knowledge_type, source_key)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings_bot ON knowledge_embeddings(organization_id, bot_id, knowledge_type, updated_at DESC);


        CREATE TABLE IF NOT EXISTS trace_spans (
            id TEXT PRIMARY KEY,
            trace_id TEXT NOT NULL,
            span_id TEXT NOT NULL,
            parent_span_id TEXT,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ok',
            organization_id TEXT,
            bot_id TEXT,
            conversation_id TEXT,
            execution_run_id TEXT,
            request_id TEXT,
            correlation_id TEXT,
            attributes_json TEXT NOT NULL DEFAULT '{}',
            started_at TEXT NOT NULL,
            ended_at TEXT,
            duration_ms INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_trace_spans_trace ON trace_spans(trace_id, started_at ASC);

        CREATE TABLE IF NOT EXISTS conversation_checkpoints (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            checkpoint_type TEXT NOT NULL,
            summary_text TEXT NOT NULL,
            facts_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_conversation_checkpoints_conv ON conversation_checkpoints(conversation_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS revenue_optimization_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            conversation_id TEXT,
            contact_id TEXT,
            event_type TEXT NOT NULL,
            recommendation_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'pending',
            expected_value REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_revenue_optimization_events_org ON revenue_optimization_events(organization_id, bot_id, event_type, created_at DESC);
        

        CREATE TABLE IF NOT EXISTS omnichannel_identities (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            contact_id TEXT,
            identity_key TEXT NOT NULL,
            identity_type TEXT NOT NULL,
            identity_value TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, identity_key)
        );
        CREATE INDEX IF NOT EXISTS idx_omnichannel_identities_org ON omnichannel_identities(organization_id, contact_id, identity_type, updated_at DESC);

        CREATE TABLE IF NOT EXISTS channel_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            conversation_id TEXT,
            contact_id TEXT,
            channel TEXT NOT NULL,
            external_thread_id TEXT,
            external_user_id TEXT,
            direction TEXT NOT NULL,
            event_type TEXT NOT NULL,
            body TEXT,
            status TEXT NOT NULL DEFAULT 'received',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_channel_events_org ON channel_events(organization_id, channel, updated_at DESC);

        CREATE TABLE IF NOT EXISTS shadow_runs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            conversation_id TEXT,
            experiment_key TEXT NOT NULL,
            production_output_json TEXT NOT NULL DEFAULT '{}',
            candidate_output_json TEXT NOT NULL DEFAULT '{}',
            diff_json TEXT NOT NULL DEFAULT '{}',
            verdict TEXT NOT NULL DEFAULT 'observe',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_shadow_runs_org ON shadow_runs(organization_id, experiment_key, created_at DESC);

        CREATE TABLE IF NOT EXISTS prompt_artifacts (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            artifact_type TEXT NOT NULL,
            artifact_key TEXT NOT NULL,
            title TEXT,
            body TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, artifact_type, artifact_key)
        );
        CREATE INDEX IF NOT EXISTS idx_prompt_artifacts_org ON prompt_artifacts(organization_id, bot_id, artifact_type, updated_at DESC);

        CREATE TABLE IF NOT EXISTS public_api_credentials (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            name TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            scopes_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'active',
            last_used_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_public_api_credentials_org ON public_api_credentials(organization_id, status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS otel_span_exports (
            id TEXT PRIMARY KEY,
            trace_id TEXT NOT NULL,
            span_id TEXT NOT NULL,
            organization_id TEXT,
            endpoint TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            exported_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_otel_span_exports_status ON otel_span_exports(status, updated_at DESC);
