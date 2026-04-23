CREATE TABLE IF NOT EXISTS whatsapp_flow_versions (
                id TEXT PRIMARY KEY,
                flow_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                state TEXT NOT NULL DEFAULT 'draft',
                flow_json TEXT NOT NULL DEFAULT '{}',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                compatibility_json TEXT NOT NULL DEFAULT '{}',
                rollout_json TEXT NOT NULL DEFAULT '{}',
                remote_asset_status TEXT NOT NULL DEFAULT 'pending',
                validation_errors_json TEXT NOT NULL DEFAULT '[]',
                cloned_from_version_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT,
                FOREIGN KEY (flow_id) REFERENCES whatsapp_flows(id),
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (bot_id) REFERENCES bots(id)
            );
            CREATE INDEX IF NOT EXISTS idx_whatsapp_flow_versions_flow ON whatsapp_flow_versions(flow_id, version_number DESC, updated_at DESC);

            CREATE TABLE IF NOT EXISTS whatsapp_flow_publications (
                id TEXT PRIMARY KEY,
                flow_id TEXT NOT NULL,
                version_id TEXT,
                organization_id TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT 'meta',
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                remote_flow_id TEXT,
                request_json TEXT NOT NULL DEFAULT '{}',
                response_json TEXT NOT NULL DEFAULT '{}',
                validation_errors_json TEXT NOT NULL DEFAULT '[]',
                started_at TEXT NOT NULL,
                finished_at TEXT,
                FOREIGN KEY (flow_id) REFERENCES whatsapp_flows(id),
                FOREIGN KEY (version_id) REFERENCES whatsapp_flow_versions(id),
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (bot_id) REFERENCES bots(id)
            );
            CREATE INDEX IF NOT EXISTS idx_whatsapp_flow_publications_flow ON whatsapp_flow_publications(flow_id, status, started_at DESC);

            CREATE TABLE IF NOT EXISTS whatsapp_flow_executions (
                id TEXT PRIMARY KEY,
                flow_id TEXT NOT NULL,
                version_id TEXT,
                organization_id TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                conversation_id TEXT,
                contact_id TEXT,
                flow_token TEXT NOT NULL,
                assigned_variant TEXT,
                status TEXT NOT NULL,
                current_screen_id TEXT,
                fallback_reason TEXT,
                fallback_mode TEXT,
                context_json TEXT NOT NULL DEFAULT '{}',
                result_json TEXT NOT NULL DEFAULT '{}',
                channel_message_id TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                last_event_at TEXT NOT NULL,
                FOREIGN KEY (flow_id) REFERENCES whatsapp_flows(id),
                FOREIGN KEY (version_id) REFERENCES whatsapp_flow_versions(id),
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (bot_id) REFERENCES bots(id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            );
            CREATE INDEX IF NOT EXISTS idx_whatsapp_flow_executions_flow ON whatsapp_flow_executions(flow_id, status, last_event_at DESC);

            CREATE TABLE IF NOT EXISTS whatsapp_flow_events (
                id TEXT PRIMARY KEY,
                flow_id TEXT NOT NULL,
                version_id TEXT,
                execution_id TEXT,
                organization_id TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                screen_id TEXT,
                step_index INTEGER,
                variant TEXT,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (flow_id) REFERENCES whatsapp_flows(id),
                FOREIGN KEY (version_id) REFERENCES whatsapp_flow_versions(id),
                FOREIGN KEY (execution_id) REFERENCES whatsapp_flow_executions(id),
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (bot_id) REFERENCES bots(id)
            );
            CREATE INDEX IF NOT EXISTS idx_whatsapp_flow_events_flow ON whatsapp_flow_events(flow_id, event_type, created_at DESC);

            CREATE TABLE IF NOT EXISTS whatsapp_flow_experiments (
                id TEXT PRIMARY KEY,
                flow_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                version_a_id TEXT NOT NULL,
                version_b_id TEXT NOT NULL,
                rollout_percentage INTEGER NOT NULL DEFAULT 50,
                status TEXT NOT NULL DEFAULT 'draft',
                note TEXT,
                metrics_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (flow_id) REFERENCES whatsapp_flows(id),
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (bot_id) REFERENCES bots(id),
                FOREIGN KEY (version_a_id) REFERENCES whatsapp_flow_versions(id),
                FOREIGN KEY (version_b_id) REFERENCES whatsapp_flow_versions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_whatsapp_flow_experiments_flow ON whatsapp_flow_experiments(flow_id, status, updated_at DESC);
            

            CREATE TABLE IF NOT EXISTS whatsapp_policy_decisions (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                conversation_id TEXT,
                contact_id TEXT,
                outbox_id TEXT,
                message_id TEXT,
                decision_status TEXT NOT NULL,
                delivery_mode TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                policy_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_whatsapp_policy_decisions_org ON whatsapp_policy_decisions(organization_id, bot_id, created_at DESC);
            

            CREATE TABLE IF NOT EXISTS bot_language_configs (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                default_language TEXT NOT NULL DEFAULT 'es',
                supported_languages_json TEXT NOT NULL DEFAULT '[]',
                detect_contact_language INTEGER NOT NULL DEFAULT 1,
                templates_json TEXT NOT NULL DEFAULT '{}',
                fallback_language TEXT NOT NULL DEFAULT 'en',
                handoff_respect_language INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(organization_id, bot_id),
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (bot_id) REFERENCES bots(id)
            );
            CREATE INDEX IF NOT EXISTS idx_language_configs_org ON bot_language_configs(organization_id, updated_at);
            

            CREATE TABLE IF NOT EXISTS oauth_states (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                integration_id TEXT,
                provider TEXT NOT NULL,
                state_token_hash TEXT NOT NULL UNIQUE,
                redirect_uri TEXT,
                scope TEXT,
                code_verifier TEXT,
                expires_at TEXT NOT NULL,
                consumed_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (integration_id) REFERENCES integration_connections(id)
            );
            CREATE TABLE IF NOT EXISTS sso_identities (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                external_subject TEXT NOT NULL,
                email TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                last_login_at TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(provider_id, external_subject),
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (provider_id) REFERENCES sso_providers(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_oauth_states_provider ON oauth_states(provider, expires_at);
            CREATE INDEX IF NOT EXISTS idx_sso_identities_org ON sso_identities(organization_id, last_login_at);

            CREATE TABLE IF NOT EXISTS integration_events (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                integration_id TEXT,
                bot_id TEXT,
                provider TEXT NOT NULL,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'info',
                summary TEXT,
                external_reference TEXT,
                request_json TEXT NOT NULL DEFAULT '{}',
                response_json TEXT NOT NULL DEFAULT '{}',
                error_json TEXT NOT NULL DEFAULT '{}',
                provider_status_code INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (integration_id) REFERENCES integration_connections(id),
                FOREIGN KEY (bot_id) REFERENCES bots(id)
            );
            CREATE INDEX IF NOT EXISTS idx_integration_events_org ON integration_events(organization_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_integration_events_integration ON integration_events(integration_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                family_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                previous_token_hash TEXT,
                status TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                used_at TEXT,
                rotated_at TEXT,
                revoked_at TEXT,
                reuse_detected_at TEXT,
                replaced_by_token_hash TEXT,
                FOREIGN KEY (session_id) REFERENCES auth_sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_auth_refresh_tokens_session ON auth_refresh_tokens(session_id, issued_at DESC);
            CREATE INDEX IF NOT EXISTS idx_auth_refresh_tokens_family ON auth_refresh_tokens(family_id, issued_at DESC);

            CREATE TABLE IF NOT EXISTS auth_login_attempts (
                id TEXT PRIMARY KEY,
                scope_key TEXT NOT NULL UNIQUE,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                first_attempt_at TEXT NOT NULL,
                last_attempt_at TEXT NOT NULL,
                blocked_until TEXT,
                last_ip_address TEXT,
                last_user_agent TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_auth_login_attempts_blocked ON auth_login_attempts(blocked_until, last_attempt_at);

            CREATE TABLE IF NOT EXISTS agenda_reminder_preferences (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL UNIQUE,
                tone TEXT NOT NULL DEFAULT 'amable',
                hours_before INTEGER NOT NULL DEFAULT 24,
                last_hours INTEGER NOT NULL DEFAULT 2,
                count INTEGER NOT NULL DEFAULT 2,
                updated_by_user_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (updated_by_user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_agenda_reminder_preferences_org ON agenda_reminder_preferences(organization_id, updated_at DESC);

            CREATE TABLE IF NOT EXISTS agenda_blocked_slots (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                bot_id TEXT,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                reason TEXT,
                created_by_user_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (bot_id) REFERENCES bots(id),
                FOREIGN KEY (created_by_user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_agenda_blocked_slots_org ON agenda_blocked_slots(organization_id, start_at);
            CREATE INDEX IF NOT EXISTS idx_agenda_blocked_slots_bot ON agenda_blocked_slots(bot_id, start_at);
