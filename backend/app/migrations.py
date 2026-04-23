from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .utils import to_json, utcnow_iso
from .vertical_marketplace_runtime import ensure_vertical_marketplace_schema
from .schema_sql import apply_migration_sql, load_migration_sql
from .runtime_schema_migration import apply_runtime_schema_ownership_migration, VOICE_CHANNEL_SCHEMA_SQL
from .platform_schema_migration import apply_platform_schema_governance_migration


@dataclass(frozen=True)
class Migration:
    version: str
    description: str
    apply: Callable


def _table_exists(conn, table: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "sqlite":
        row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
        return bool(row)
    row = conn.execute(
        """
        SELECT 1 AS present
        FROM information_schema.tables
        WHERE table_schema = current_schema() AND table_name = ?
        LIMIT 1
        """,
        (table,),
    ).fetchone()
    return bool(row)


def _column_exists(conn, table: str, column: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "sqlite":
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(row[1] == column for row in rows)
    row = conn.execute(
        """
        SELECT 1 AS present
        FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = ? AND column_name = ?
        LIMIT 1
        """,
        (table, column),
    ).fetchone()
    return bool(row)


def _ensure_column(conn, table: str, column: str, definition: str) -> None:
    if not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _ensure_schema_migrations_table(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            description TEXT,
            applied_at TEXT NOT NULL
        );
        """
    )
    _ensure_column(conn, "schema_migrations", "metadata_json", "TEXT NOT NULL DEFAULT '{}'")


def _migration_runtime_governance(conn) -> None:
    _ensure_column(conn, "contact_memory", "memory_version", "TEXT NOT NULL DEFAULT 'v1'")
    _ensure_column(conn, "contact_memory", "memory_etag", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "contact_memory", "operational_state_json", "TEXT NOT NULL DEFAULT '{}' ")
    _ensure_column(conn, "contact_memory", "urgency_level", "TEXT NOT NULL DEFAULT 'normal'")
    _ensure_column(conn, "contact_memory", "urgency_score", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "contact_memory", "known_contact", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "contact_memory", "current_intent", "TEXT")
    _ensure_column(conn, "contact_memory", "current_mode", "TEXT")
    _ensure_column(conn, "contact_memory", "last_classifier_source", "TEXT")
    _ensure_column(conn, "contact_memory", "last_generator_source", "TEXT")

    _ensure_column(conn, "messages", "correlation_id", "TEXT")

    _ensure_column(conn, "message_ai_runs", "correlation_id", "TEXT")
    _ensure_column(conn, "message_ai_runs", "classifier_source", "TEXT")
    _ensure_column(conn, "message_ai_runs", "decision_policy", "TEXT")
    _ensure_column(conn, "message_ai_runs", "generator_source", "TEXT")
    _ensure_column(conn, "message_ai_runs", "fallback_chain_json", "TEXT NOT NULL DEFAULT '[]'")

    apply_migration_sql(conn, '101_runtime_governance_v1.sql')


def _migration_activation_foundations(conn) -> None:
    _ensure_column(conn, "organizations", "tenant_mode", "TEXT NOT NULL DEFAULT 'sandbox'")
    _ensure_column(conn, "organizations", "go_live_at", "TEXT")

    apply_migration_sql(conn, '102_activation_foundations_v1.sql')


def _migration_phase2_ops_quality_commerce(conn) -> None:
    apply_migration_sql(conn, '103_phase2_ops_quality_commerce_v1.sql')


def _migration_phase3_assignment_simulation_capacity(conn) -> None:
    apply_migration_sql(conn, '104_phase3_assignment_simulation_capacity_v1.sql')


def _migration_phase4_operational_control(conn) -> None:
    _ensure_column(conn, "bots", "operational_state", "TEXT NOT NULL DEFAULT 'active'")
    _ensure_column(conn, "bots", "temp_unavailability_message", "TEXT")
    _ensure_column(conn, "bots", "operational_resume_at", "TEXT")
    _ensure_column(conn, "bots", "last_operational_command_id", "TEXT")

    apply_migration_sql(conn, '105_phase4_operational_control_v1.sql')


def _migration_phase5_operational_control_enterprise(conn) -> None:
    _ensure_column(conn, "operational_command_requests", "approved_by_user_id", "TEXT")
    _ensure_column(conn, "operational_command_requests", "approved_at", "TEXT")
    _ensure_column(conn, "operational_command_requests", "approval_note", "TEXT")

    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_operational_commands_status_risk ON operational_command_requests(status, risk_level, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_operational_commands_approved_by ON operational_command_requests(approved_by_user_id, approved_at DESC);
        """
    )


def _migration_phase9_whatsapp_governance(conn) -> None:
    _ensure_column(conn, "whatsapp_numbers", "quality_rating", "TEXT NOT NULL DEFAULT 'unknown'")
    _ensure_column(conn, "whatsapp_numbers", "quality_status", "TEXT NOT NULL DEFAULT 'unknown'")
    _ensure_column(conn, "whatsapp_numbers", "throughput_tier", "TEXT NOT NULL DEFAULT 'standard'")
    _ensure_column(conn, "whatsapp_numbers", "provider_degraded_until", "TEXT")
    _ensure_column(conn, "whatsapp_numbers", "last_health_check_at", "TEXT")
    _ensure_column(conn, "whatsapp_numbers", "last_provider_error_code", "TEXT")
    _ensure_column(conn, "whatsapp_numbers", "last_provider_error_at", "TEXT")
    _ensure_column(conn, "outbox_messages", "governance_json", "TEXT NOT NULL DEFAULT '{}'")

    conn.executescript(
        """
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
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            FOREIGN KEY (outbox_id) REFERENCES outbox_messages(id),
            FOREIGN KEY (message_id) REFERENCES messages(id)
        );

        CREATE INDEX IF NOT EXISTS idx_whatsapp_policy_decisions_org ON whatsapp_policy_decisions(organization_id, bot_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_whatsapp_numbers_health ON whatsapp_numbers(organization_id, quality_status, updated_at DESC);
        """
    )


def _migration_phase9_whatsapp_guardrails_v2(conn) -> None:
    conn.executescript(
        """
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

        CREATE INDEX IF NOT EXISTS idx_whatsapp_opt_outs_bot_contact ON whatsapp_opt_outs(organization_id, bot_id, contact_id, active, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_whatsapp_opt_outs_bot_phone ON whatsapp_opt_outs(organization_id, bot_id, phone, active, updated_at DESC);
        """
    )

def _migration_phase6_operational_control_enterprise_hardening(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS operational_command_alerts (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            command_id TEXT,
            severity TEXT NOT NULL DEFAULT 'warning',
            alert_type TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            acknowledged_at TEXT,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (command_id) REFERENCES operational_command_requests(id)
        );

        CREATE INDEX IF NOT EXISTS idx_operational_alerts_org_bot_created ON operational_command_alerts(organization_id, bot_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_operational_alerts_status_created ON operational_command_alerts(status, created_at DESC);
        """
    )


def _migration_phase9_whatsapp_delivery_truth(conn) -> None:
    apply_migration_sql(conn, '106_phase9_whatsapp_delivery_truth_v1.sql')


def _migration_voice_pipeline_foundations(conn) -> None:
    _ensure_column(conn, "voice_notes", "media_id", "TEXT")
    _ensure_column(conn, "voice_notes", "media_url", "TEXT")
    _ensure_column(conn, "voice_notes", "media_mime_type", "TEXT")
    _ensure_column(conn, "voice_notes", "media_sha256", "TEXT")
    _ensure_column(conn, "voice_notes", "media_size_bytes", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "voice_notes", "consent_status", "TEXT NOT NULL DEFAULT 'implicit_inbound_whatsapp'")
    _ensure_column(conn, "voice_notes", "media_expires_at", "TEXT")
    _ensure_column(conn, "voice_notes", "transcription_source", "TEXT NOT NULL DEFAULT 'manual'")
    _ensure_column(conn, "voice_notes", "transcription_confidence", "REAL NOT NULL DEFAULT 0")
    _ensure_column(conn, "voice_notes", "diarization_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(conn, "voice_notes", "segments_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(conn, "voice_notes", "audio_quality", "TEXT NOT NULL DEFAULT 'unknown'")
    _ensure_column(conn, "voice_notes", "background_noise_level", "TEXT NOT NULL DEFAULT 'unknown'")
    _ensure_column(conn, "voice_notes", "processing_status", "TEXT NOT NULL DEFAULT 'completed'")
    _ensure_column(conn, "voice_notes", "reply_mode", "TEXT NOT NULL DEFAULT 'text'")
    _ensure_column(conn, "voice_notes", "metadata_json", "TEXT NOT NULL DEFAULT '{}' ")

    apply_migration_sql(conn, '107_voice_pipeline_foundations_v1.sql')


def _migration_phase11_whatsapp_template_lifecycle(conn) -> None:
    apply_migration_sql(conn, '108_phase11_whatsapp_template_lifecycle_v1.sql')


def _migration_phase12_governed_knowledge_runtime(conn) -> None:
    apply_migration_sql(conn, '109_phase12_governed_knowledge_runtime_v1.sql')


def _migration_phase16_tool_execution_outcomes_flywheel(conn) -> None:
    try:
        conn.executescript(load_migration_sql('006_tool_execution_outcomes_flywheel.sql'))
    except Exception:
        pass
    _ensure_column(conn, "outcome_exposures", "tool_execution_run_id", "TEXT")
    _ensure_column(conn, "outcome_exposures", "tool_action", "TEXT")
    _ensure_column(conn, "outcome_exposures", "tool_adapter_key", "TEXT")
    _ensure_column(conn, "outcome_exposures", "tool_provider", "TEXT")
    _ensure_column(conn, "outcome_events", "source_execution_run_id", "TEXT")
    _ensure_column(conn, "outcome_events", "source_tool_action", "TEXT")
    _ensure_column(conn, "outcome_events", "source_tool_provider", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome_exposures_tool_run ON outcome_exposures(tool_execution_run_id, sent_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome_exposures_tool_action ON outcome_exposures(tool_action, sent_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome_exposures_tool_provider ON outcome_exposures(tool_provider, sent_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome_events_source_execution ON outcome_events(source_execution_run_id, event_timestamp DESC)")


def _migration_phase17_multi_agent_intent_router(conn) -> None:
    conn.executescript(load_migration_sql('007_multi_agent_intent_router.sql'))
    _ensure_column(conn, "outcome_exposures", "specialist_agent_key", "TEXT")
    _ensure_column(conn, "outcome_exposures", "specialist_agent_version", "TEXT")
    _ensure_column(conn, "outcome_exposures", "specialist_prompt_id", "TEXT")
    _ensure_column(conn, "outcome_exposures", "intent_family", "TEXT")
    _ensure_column(conn, "outcome_exposures", "agent_routing_run_id", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome_exposures_specialist_agent ON outcome_exposures(specialist_agent_key, sent_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome_exposures_agent_route ON outcome_exposures(agent_routing_run_id, sent_at DESC)")


def _migration_phase18_agent_policy_engine(conn) -> None:
    conn.executescript(load_migration_sql('008_agent_policy_engine.sql'))
    _ensure_column(conn, "agent_routing_runs", "policy_profile_key", "TEXT")
    _ensure_column(conn, "agent_routing_runs", "policy_profile_version", "TEXT")
    _ensure_column(conn, "agent_routing_runs", "policy_evaluation_id", "TEXT")
    _ensure_column(conn, "agent_routing_runs", "policy_json", "TEXT")
    _ensure_column(conn, "tool_execution_runs", "specialist_agent_key", "TEXT")
    _ensure_column(conn, "tool_execution_runs", "agent_routing_run_id", "TEXT")
    _ensure_column(conn, "tool_execution_runs", "policy_profile_key", "TEXT")
    _ensure_column(conn, "tool_execution_runs", "policy_profile_version", "TEXT")
    _ensure_column(conn, "tool_execution_runs", "policy_evaluation_id", "TEXT")
    _ensure_column(conn, "tool_execution_runs", "policy_json", "TEXT")
    _ensure_column(conn, "outcome_exposures", "policy_profile_key", "TEXT")
    _ensure_column(conn, "outcome_exposures", "policy_profile_version", "TEXT")
    _ensure_column(conn, "outcome_exposures", "policy_evaluation_id", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_routing_runs_policy_profile ON agent_routing_runs(policy_profile_key, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_execution_runs_policy_profile ON tool_execution_runs(policy_profile_key, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_execution_runs_specialist_agent ON tool_execution_runs(specialist_agent_key, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome_exposures_policy_profile ON outcome_exposures(policy_profile_key, sent_at DESC)")


def _migration_phase19_live_knowledge_ingestion(conn) -> None:
    apply_migration_sql(conn, '009_live_knowledge_ingestion.sql')


def _migration_phase15_tool_execution_native(conn) -> None:
    conn.executescript(load_migration_sql('005_tool_execution_native.sql'))

def _migration_phase14_outcomes_closed_loop(conn) -> None:
    conn.executescript(load_migration_sql('004_outcomes_closed_loop.sql'))
    _ensure_column(conn, "outcome_exposures", "prompt_run_id", "TEXT")
    _ensure_column(conn, "outcome_exposures", "decision_path_id", "TEXT")
    _ensure_column(conn, "outcome_exposures", "handoff_id", "TEXT")
    _ensure_column(conn, "outcome_exposures", "handoff_kind", "TEXT")
    _ensure_column(conn, "outcome_exposures", "vertical", "TEXT")
    _ensure_column(conn, "outcome_exposures", "funnel_stage", "TEXT")
    _ensure_column(conn, "outcome_events", "vertical", "TEXT")
    _ensure_column(conn, "outcome_events", "funnel_stage", "TEXT")


def _migration_phase13_human_ops_supervision_runtime(conn) -> None:
    apply_migration_sql(conn, '110_phase13_human_ops_supervision_runtime_v1.sql')

def _migration_phase20_proactive_reasoning_engine(conn) -> None:
    conn.executescript(load_migration_sql('010_proactive_reasoning_engine.sql'))


def _migration_phase22_guided_vertical_onboarding(conn) -> None:
    apply_migration_sql(conn, '012_guided_vertical_onboarding.sql')
    _ensure_column(conn, "vertical_onboarding_wizards", "validation_snapshot_json", "TEXT NOT NULL DEFAULT '{}' ")
    _ensure_column(conn, "vertical_onboarding_wizards", "recompute_state_json", "TEXT NOT NULL DEFAULT '{}' ")
    _ensure_column(conn, "vertical_onboarding_wizards", "wizard_revision", "INTEGER NOT NULL DEFAULT 1")


def _migration_phase23_voice_first_class_channel(conn) -> None:
    conn.executescript(VOICE_CHANNEL_SCHEMA_SQL)


def _migration_phase21_multi_candidate_ranking(conn) -> None:
    _ensure_column(conn, "message_ai_runs", "selected_variant", "TEXT")
    _ensure_column(conn, "message_ai_runs", "candidate_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "message_ai_runs", "ranking_version", "TEXT")
    _ensure_column(conn, "message_ai_runs", "ranking_summary_json", "TEXT NOT NULL DEFAULT '{}' ")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS response_candidate_rankings (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            message_ai_run_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            candidate_index INTEGER NOT NULL,
            variant_key TEXT NOT NULL,
            tone TEXT,
            cta_style TEXT,
            length TEXT,
            framing TEXT,
            source TEXT,
            response_text TEXT NOT NULL,
            verification_status TEXT,
            verification_json TEXT NOT NULL DEFAULT '{}',
            score_total REAL NOT NULL DEFAULT 0,
            score_json TEXT NOT NULL DEFAULT '{}',
            selected INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (message_ai_run_id) REFERENCES message_ai_runs(id),
            FOREIGN KEY (message_id) REFERENCES messages(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_response_candidate_rankings_run ON response_candidate_rankings(message_ai_run_id, candidate_index)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_response_candidate_rankings_selected ON response_candidate_rankings(selected, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_response_candidate_rankings_variant ON response_candidate_rankings(variant_key, created_at DESC)")


def _migration_phase24_vertical_marketplace(conn) -> None:
    apply_migration_sql(conn, '014_vertical_marketplace.sql')


def _migration_phase25_waos_optimizer(conn) -> None:
    apply_migration_sql(conn, '111_phase25_waos_optimizer_v1.sql')


def _migration_phase26_self_state_runtime(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_state_turns (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            conversation_id TEXT NOT NULL,
            contact_id TEXT,
            message_id TEXT,
            confidence REAL NOT NULL DEFAULT 0,
            uncertainty_reason TEXT NOT NULL DEFAULT '[]',
            evidence_coverage REAL NOT NULL DEFAULT 0,
            execution_readiness REAL NOT NULL DEFAULT 0,
            risk_if_send TEXT NOT NULL DEFAULT 'low',
            need_verification INTEGER NOT NULL DEFAULT 0,
            need_tool INTEGER NOT NULL DEFAULT 0,
            need_human INTEGER NOT NULL DEFAULT 0,
            next_best_action TEXT NOT NULL DEFAULT 'respond',
            learning_opportunity TEXT NOT NULL DEFAULT '[]',
            state_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_runtime_self_state_turns_conv ON runtime_self_state_turns(conversation_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_runtime_self_state_turns_msg ON runtime_self_state_turns(message_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS runtime_self_state_conversations (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            conversation_id TEXT NOT NULL UNIQUE,
            contact_id TEXT,
            confidence REAL NOT NULL DEFAULT 0,
            uncertainty_reason TEXT NOT NULL DEFAULT '[]',
            evidence_coverage REAL NOT NULL DEFAULT 0,
            execution_readiness REAL NOT NULL DEFAULT 0,
            risk_if_send TEXT NOT NULL DEFAULT 'low',
            need_verification INTEGER NOT NULL DEFAULT 0,
            need_tool INTEGER NOT NULL DEFAULT 0,
            need_human INTEGER NOT NULL DEFAULT 0,
            next_best_action TEXT NOT NULL DEFAULT 'respond',
            learning_opportunity TEXT NOT NULL DEFAULT '[]',
            state_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_runtime_self_state_conversations_org ON runtime_self_state_conversations(organization_id, updated_at DESC);
        """
    )


def _migration_phase30_runtime_schema_ownership(conn) -> None:
    apply_runtime_schema_ownership_migration(conn, _ensure_column)


def _migration_phase31_platform_schema_governance(conn) -> None:
    apply_platform_schema_governance_migration(conn, _ensure_column)


def _migration_phase27_growth_os_runtime(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS growth_os_runs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'recommend',
            status TEXT NOT NULL DEFAULT 'completed',
            goals_json TEXT NOT NULL DEFAULT '[]',
            summary_json TEXT NOT NULL DEFAULT '{}',
            decision_policy_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_growth_os_runs_org ON growth_os_runs(organization_id, bot_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS growth_os_targets (
            id TEXT PRIMARY KEY,
            growth_run_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            candidate_id TEXT,
            proactive_run_id TEXT,
            contact_id TEXT,
            conversation_id TEXT,
            objective TEXT NOT NULL,
            goal TEXT NOT NULL,
            specialist_agent_key TEXT NOT NULL,
            timing_decision TEXT,
            channel TEXT NOT NULL DEFAULT 'whatsapp',
            action_type TEXT NOT NULL DEFAULT 'materialize_playbook',
            priority_score REAL NOT NULL DEFAULT 0,
            expected_value REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'selected',
            scorecard_json TEXT NOT NULL DEFAULT '{}',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (growth_run_id) REFERENCES growth_os_runs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_growth_os_targets_run ON growth_os_targets(growth_run_id, priority_score DESC);
        CREATE INDEX IF NOT EXISTS idx_growth_os_targets_contact ON growth_os_targets(organization_id, contact_id, created_at DESC);
        """
    )

def _migration_phase28_payment_delete_cleanup(conn) -> None:
    if getattr(conn, "backend", "sqlite") == "postgresql":
        conn.executescript(
            """
            CREATE OR REPLACE FUNCTION fn_commerce_payments_cleanup_before_delete()
            RETURNS TRIGGER
            LANGUAGE plpgsql
            AS $$
            BEGIN
                DELETE FROM outcome_attribution_facts
                WHERE outcome_event_id IN (SELECT id FROM outcome_events WHERE payment_id = OLD.id)
                   OR exposure_id IN (SELECT id FROM outcome_exposures WHERE payment_id = OLD.id);
                DELETE FROM outcome_events WHERE payment_id = OLD.id;
                DELETE FROM outcome_exposures WHERE payment_id = OLD.id;
                RETURN OLD;
            END;
            $$;

            DROP TRIGGER IF EXISTS trg_commerce_payments_cleanup_before_delete ON commerce_payments;
            CREATE TRIGGER trg_commerce_payments_cleanup_before_delete
            BEFORE DELETE ON commerce_payments
            FOR EACH ROW
            EXECUTE FUNCTION fn_commerce_payments_cleanup_before_delete();
            """
        )
        return
    conn.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS trg_commerce_payments_cleanup_before_delete
        BEFORE DELETE ON commerce_payments
        FOR EACH ROW
        BEGIN
            DELETE FROM outcome_attribution_facts
            WHERE outcome_event_id IN (SELECT id FROM outcome_events WHERE payment_id = OLD.id)
               OR exposure_id IN (SELECT id FROM outcome_exposures WHERE payment_id = OLD.id);
            DELETE FROM outcome_events WHERE payment_id = OLD.id;
            DELETE FROM outcome_exposures WHERE payment_id = OLD.id;
        END;
        """
    )


def _migration_phase29_catalog_domain_schema(conn) -> None:
    apply_migration_sql(conn, '015_catalog_v9.sql')


MIGRATIONS = [
    Migration(
        version="2026-04-15-runtime-governance-v1",
        description="runtime governance foundations: migrations, inbox indexes, reasoning trail and inbound locks",
        apply=_migration_runtime_governance,
    ),
    Migration(
        version="2026-04-16-activation-foundations-v1",
        description="activation progress, feature flags, product events and inbox saved views",
        apply=_migration_activation_foundations,
    ),
    Migration(
        version="2026-04-16-phase2-ops-quality-commerce-integrations-v1",
        description="work queues, explainability snapshots, lead stage history and integration replay requests",
        apply=_migration_phase2_ops_quality_commerce,
    ),
    Migration(
        version="2026-04-16-phase3-assignment-simulation-capacity-v1",
        description="assignment history, bot simulations and agenda resource capacity foundations",
        apply=_migration_phase3_assignment_simulation_capacity,
    ),
    Migration(
        version="2026-04-16-phase4-operational-control-v1",
        description="operational control commands, authorized numbers, availability overrides and bot operational state history",
        apply=_migration_phase4_operational_control,
    ),
    Migration(
        version="2026-04-16-phase5-operational-control-enterprise-v1",
        description="operational control dual approval and execution hardening",
        apply=_migration_phase5_operational_control_enterprise,
    ),
    Migration(
        version="2026-04-16-phase6-operational-control-enterprise-hardening-v1",
        description="operational control scopes, alerts and undo hardening",
        apply=_migration_phase6_operational_control_enterprise_hardening,
    ),
    Migration(
        version="2026-04-17-phase9-whatsapp-governance-v1",
        description="whatsapp policy engine, customer care window enforcement, health and throughput governance",
        apply=_migration_phase9_whatsapp_governance,
    ),
    Migration(
        version="2026-04-17-phase9-whatsapp-delivery-truth-v1",
        description="whatsapp delivery truth facts, projections, reconciliation and analytics foundations",
        apply=_migration_phase9_whatsapp_delivery_truth,
    ),
    Migration(
        version="2026-04-17-phase9-whatsapp-guardrails-v2",
        description="whatsapp opt-out suppression, outbound content safety and anti-blocking guardrails",
        apply=_migration_phase9_whatsapp_guardrails_v2,
    ),
    Migration(
        version="2026-04-17-phase10-voice-pipeline-foundations-v1",
        description="voice media retrieval, transcription quality, reply orchestration and analytics foundations",
        apply=_migration_voice_pipeline_foundations,
    ),
    Migration(
        version="2026-04-17-phase11-whatsapp-template-lifecycle-v1",
        description="whatsapp template lifecycle, sync, approvals, linting, failover and analytics foundations",
        apply=_migration_phase11_whatsapp_template_lifecycle,
    ),
    Migration(
        version="2026-04-17-phase12-governed-knowledge-runtime-v1",
        description="governed knowledge documents, versions, freshness and refresh events",
        apply=_migration_phase12_governed_knowledge_runtime,
    ),
    Migration(
        version="2026-04-17-phase13-human-ops-supervision-v1",
        description="human ops supervision runtime: structured notes, takeover briefs, reply suggestions, QA loops and supervisor console",
        apply=_migration_phase13_human_ops_supervision_runtime,
    ),
    Migration(
        version="2026-04-17-phase14-outcomes-closed-loop-v1",
        description="closed-loop outcomes runtime: exposures, outcome events, attribution facts, scorecards and optimization decisions",
        apply=_migration_phase14_outcomes_closed_loop,
    ),
    Migration(
        version="2026-04-17-phase15-tool-execution-native-v1",
        description="native external tool execution runtime: typed actions, adapters, confirmation, idempotency and execution logs",
        apply=_migration_phase15_tool_execution_native,
    ),
    Migration(
        version="2026-04-17-phase16-tool-execution-outcomes-flywheel-v1",
        description="tool execution and outcomes flywheel: automatic exposure attribution, action scorecards and revenue/show-rate feedback",
        apply=_migration_phase16_tool_execution_outcomes_flywheel,
    ),
    Migration(
        version="2026-04-17-phase17-multi-agent-intent-router-v1",
        description="multi-agent runtime: intent router, specialist agents, shared memory and supervisor orchestration",
        apply=_migration_phase17_multi_agent_intent_router,
    ),
    Migration(
        version="2026-04-17-phase18-agent-policy-engine-v1",
        description="specialist policy engine: per-agent budgets, SLAs, enforcement and policy evaluations",
        apply=_migration_phase18_agent_policy_engine,
    ),
    Migration(
        version="2026-04-17-phase19-live-knowledge-ingestion-v1",
        description="continuous knowledge ingestion: native sources, watchers, sync runs, validation and publication into governed knowledge",
        apply=_migration_phase19_live_knowledge_ingestion,
    ),
    Migration(
        version="2026-04-17-phase20-proactive-reasoning-engine-v1",
        description="proactive reasoning engine: business signals, scored candidates, proactive playbooks and closed-loop exposures",
        apply=_migration_phase20_proactive_reasoning_engine,
    ),
    Migration(
        version="2026-04-17-phase21-multi-candidate-ranking-v1",
        description="response ranker: generate multiple reply candidates, score them and select the best before send",
        apply=_migration_phase21_multi_candidate_ranking,
    ),
    Migration(
        version="2026-04-17-phase22-guided-vertical-onboarding-v1",
        description="guided vertical onboarding wizard: verticalized setup, smart defaults, seeded knowledge, templates, catalog and integrations",
        apply=_migration_phase22_guided_vertical_onboarding,
    ),
    Migration(
        version="2026-04-17-phase23-voice-first-class-channel-v1",
        description="voice native runtime: sessions, turns, interruption, urgency detection and voice-text handoff on shared memory",
        apply=_migration_phase23_voice_first_class_channel,
    ),
    Migration(
        version="2026-04-17-phase24-vertical-marketplace-v1",
        description="vertical marketplace: publish, version, install, upgrade and monetize reusable vertical packages",
        apply=_migration_phase24_vertical_marketplace,
    ),
    Migration(
        version="2026-04-18-phase25-waos-optimizer-v1",
        description="waos optimizer: scorecard-driven proposals, shadow or a-b experiments, guarded auto-promotion and full audit trail",
        apply=_migration_phase25_waos_optimizer,
    ),
    Migration(
        version="2026-04-18-phase26-self-state-runtime-v1",
        description="runtime self state: turn and conversation operational self-awareness with decision traces and persistence",
        apply=_migration_phase26_self_state_runtime,
    ),
    Migration(
        version="2026-04-18-phase27-growth-os-runtime-v1",
        description="growth os runtime: opportunity detection, objective prioritization, execution loops and impact iteration for proactive revenue ops",
        apply=_migration_phase27_growth_os_runtime,
    ),
    Migration(
        version="2026-04-18-phase28-payment-delete-cleanup-v1",
        description="sqlite cleanup trigger so test and replay fixtures can replace commerce payments without foreign key residue",
        apply=_migration_phase28_payment_delete_cleanup,
    ),
    Migration(
        version="2026-04-22-phase29-catalog-domain-schema-v1",
        description="catalog v9 schema sourced from versioned sql migration instead of domain modules",
        apply=_migration_phase29_catalog_domain_schema,
    ),
    Migration(
        version="2026-04-22-phase30-runtime-schema-ownership-v1",
        description="move runtime-owned ddl into versioned migrations and keep runtime schema checks minimal",
        apply=_migration_phase30_runtime_schema_ownership,
    ),
    Migration(
        version="2026-04-22-phase31-platform-schema-governance-v1",
        description="move platform and telemetry ddl into versioned migrations and keep runtime checks guard-only",
        apply=_migration_phase31_platform_schema_governance,
    ),

]


def apply_migrations(conn) -> list[str]:
    _ensure_schema_migrations_table(conn)
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    applied = {row[0] if not isinstance(row, dict) else row.get("version") for row in rows}
    executed: list[str] = []
    for migration in MIGRATIONS:
        if migration.version in applied:
            continue
        migration.apply(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, description, applied_at, metadata_json) VALUES (?, ?, ?, ?)",
            (migration.version, migration.description, utcnow_iso(), to_json({"kind": "python_migration"})),
        )
        executed.append(migration.version)
    return executed


def migration_status(conn) -> dict[str, object]:
    _ensure_schema_migrations_table(conn)
    rows = conn.execute("SELECT version, description, applied_at FROM schema_migrations ORDER BY applied_at ASC").fetchall()
    applied_rows = [dict(row) if not isinstance(row, dict) else row for row in rows]
    applied = {row.get("version") for row in applied_rows}
    pending = [migration.version for migration in MIGRATIONS if migration.version not in applied]
    return {
        "applied_count": len(applied_rows),
        "pending_count": len(pending),
        "current_version": applied_rows[-1]["version"] if applied_rows else None,
        "pending_versions": pending,
        "applied": applied_rows,
    }


