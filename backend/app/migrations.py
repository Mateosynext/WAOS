from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .utils import to_json, utcnow_iso
from .vertical_onboarding_runtime import ensure_guided_vertical_onboarding_schema
from .vertical_marketplace_runtime import ensure_vertical_marketplace_schema


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

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS message_operational_reasoning (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            intent_detected TEXT,
            urgency_level TEXT,
            urgency_score INTEGER NOT NULL DEFAULT 0,
            takeover_reason TEXT,
            policy_applied TEXT,
            classifier_source TEXT,
            generator_source TEXT,
            summary_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (message_id) REFERENCES messages(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id)
        );

        CREATE TABLE IF NOT EXISTS inbound_message_locks (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            conversation_id TEXT,
            external_id TEXT,
            lock_key TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            correlation_id TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            acquired_at TEXT NOT NULL,
            released_at TEXT,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS domain_events (
            id TEXT PRIMARY KEY,
            event_name TEXT NOT NULL,
            organization_id TEXT,
            bot_id TEXT,
            conversation_id TEXT,
            message_id TEXT,
            correlation_id TEXT,
            status TEXT NOT NULL DEFAULT 'ok',
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (message_id) REFERENCES messages(id)
        );

        CREATE INDEX IF NOT EXISTS idx_conversations_inbox_status ON conversations(organization_id, status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_conversations_owner_status ON conversations(organization_id, assigned_user_id, status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_conversations_takeover ON conversations(organization_id, human_takeover, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_contact_memory_stage_score ON contact_memory(organization_id, lead_stage, lead_score DESC, last_updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_contact_memory_urgency ON contact_memory(organization_id, urgency_level, urgency_score DESC, last_updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON messages(conversation_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_external ON messages(organization_id, external_id);
        CREATE INDEX IF NOT EXISTS idx_message_ai_runs_message ON message_ai_runs(message_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_operational_reasoning_message ON message_operational_reasoning(message_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_domain_events_org_name ON domain_events(organization_id, event_name, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_inbound_locks_status ON inbound_message_locks(organization_id, status, acquired_at DESC);
        """
    )


def _migration_activation_foundations(conn) -> None:
    _ensure_column(conn, "organizations", "tenant_mode", "TEXT NOT NULL DEFAULT 'sandbox'")
    _ensure_column(conn, "organizations", "go_live_at", "TEXT")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS feature_flag_overrides (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            feature_key TEXT NOT NULL,
            is_enabled INTEGER NOT NULL DEFAULT 0,
            rollout_stage TEXT NOT NULL DEFAULT 'pilot',
            note TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, bot_id, feature_key),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS product_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            actor_user_id TEXT,
            event_name TEXT NOT NULL,
            entity_type TEXT,
            entity_id TEXT,
            value_numeric REAL,
            value_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (actor_user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS activation_progress (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL UNIQUE,
            bot_id TEXT,
            vertical TEXT,
            tenant_mode TEXT NOT NULL DEFAULT 'sandbox',
            activated_channels_count INTEGER NOT NULL DEFAULT 0,
            bots_ready_count INTEGER NOT NULL DEFAULT 0,
            catalog_items_count INTEGER NOT NULL DEFAULT 0,
            agenda_ready INTEGER NOT NULL DEFAULT 0,
            readiness_score INTEGER NOT NULL DEFAULT 0,
            first_value_at TEXT,
            ttfv_hours REAL,
            recommended_next_step TEXT,
            blockers_json TEXT NOT NULL DEFAULT '[]',
            checklist_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id)
        );

        CREATE TABLE IF NOT EXISTS inbox_saved_views (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            filter_json TEXT NOT NULL DEFAULT '{}',
            is_default INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, user_id, slug),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_feature_flags_org_bot ON feature_flag_overrides(organization_id, bot_id, feature_key);
        CREATE INDEX IF NOT EXISTS idx_product_events_org_name ON product_events(organization_id, event_name, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_activation_progress_score ON activation_progress(organization_id, readiness_score DESC, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_inbox_saved_views_user ON inbox_saved_views(organization_id, user_id, is_default DESC, updated_at DESC);
        """
    )


def _migration_phase2_ops_quality_commerce(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS work_queue_definitions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            role_key TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            rule_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, role_key),
            FOREIGN KEY (organization_id) REFERENCES organizations(id)
        );

        CREATE TABLE IF NOT EXISTS bot_decision_explanations (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            message_ai_run_id TEXT,
            confidence_score INTEGER NOT NULL DEFAULT 0,
            confidence_band TEXT NOT NULL DEFAULT 'low',
            explanation_json TEXT NOT NULL DEFAULT '{}',
            risk_flags_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (message_ai_run_id) REFERENCES message_ai_runs(id)
        );

        CREATE TABLE IF NOT EXISTS lead_stage_history (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            crm_lead_id TEXT NOT NULL,
            previous_stage TEXT,
            new_stage TEXT NOT NULL,
            reason TEXT,
            changed_by TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (crm_lead_id) REFERENCES crm_leads(id),
            FOREIGN KEY (changed_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS integration_replay_requests (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            webhook_receipt_id TEXT NOT NULL,
            requested_by TEXT,
            dry_run INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'requested',
            result_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (webhook_receipt_id) REFERENCES webhook_event_receipts(id),
            FOREIGN KEY (requested_by) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_work_queue_definitions_org_role ON work_queue_definitions(organization_id, role_key, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_bot_decision_explanations_conv ON bot_decision_explanations(conversation_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_lead_stage_history_lead ON lead_stage_history(crm_lead_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_integration_replay_requests_receipt ON integration_replay_requests(webhook_receipt_id, created_at DESC);
        """
    )


def _migration_phase3_assignment_simulation_capacity(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversation_assignment_history (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            previous_assigned_user_id TEXT,
            new_assigned_user_id TEXT,
            queue_role TEXT,
            assignment_mode TEXT NOT NULL DEFAULT 'manual',
            reasoning_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (previous_assigned_user_id) REFERENCES users(id),
            FOREIGN KEY (new_assigned_user_id) REFERENCES users(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS bot_simulation_cases (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            title TEXT NOT NULL,
            scenario_text TEXT NOT NULL,
            expected_outcome_json TEXT NOT NULL DEFAULT '{}',
            tags_json TEXT NOT NULL DEFAULT '[]',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS bot_simulation_runs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            compare_target TEXT NOT NULL DEFAULT 'draft',
            left_version_id TEXT,
            right_version_id TEXT,
            status TEXT NOT NULL DEFAULT 'completed',
            summary_json TEXT NOT NULL DEFAULT '{}',
            cases_total INTEGER NOT NULL DEFAULT 0,
            passed_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0,
            created_by TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (left_version_id) REFERENCES bot_versions(id),
            FOREIGN KEY (right_version_id) REFERENCES bot_versions(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS bot_simulation_run_results (
            id TEXT PRIMARY KEY,
            simulation_run_id TEXT NOT NULL,
            simulation_case_id TEXT NOT NULL,
            passed INTEGER NOT NULL DEFAULT 0,
            result_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (simulation_run_id) REFERENCES bot_simulation_runs(id),
            FOREIGN KEY (simulation_case_id) REFERENCES bot_simulation_cases(id)
        );

        CREATE TABLE IF NOT EXISTS agenda_resources (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            branch TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS agenda_resource_capacity_rules (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            resource_id TEXT NOT NULL,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            slot_capacity INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (resource_id) REFERENCES agenda_resources(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS appointment_resource_assignments (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            appointment_id TEXT NOT NULL UNIQUE,
            resource_id TEXT NOT NULL,
            assigned_by TEXT,
            note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (appointment_id) REFERENCES appointments(id),
            FOREIGN KEY (resource_id) REFERENCES agenda_resources(id),
            FOREIGN KEY (assigned_by) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_assignment_history_conv ON conversation_assignment_history(conversation_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_assignment_history_org_user ON conversation_assignment_history(organization_id, new_assigned_user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_sim_cases_bot ON bot_simulation_cases(bot_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_sim_runs_bot ON bot_simulation_runs(bot_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_capacity_rules_resource_day ON agenda_resource_capacity_rules(resource_id, day_of_week, start_time, end_time);
        CREATE INDEX IF NOT EXISTS idx_appointment_resource_assignments_resource ON appointment_resource_assignments(resource_id, updated_at DESC);
        """
    )


def _migration_phase4_operational_control(conn) -> None:
    _ensure_column(conn, "bots", "operational_state", "TEXT NOT NULL DEFAULT 'active'")
    _ensure_column(conn, "bots", "temp_unavailability_message", "TEXT")
    _ensure_column(conn, "bots", "operational_resume_at", "TEXT")
    _ensure_column(conn, "bots", "last_operational_command_id", "TEXT")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS authorized_operational_numbers (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            phone_e164 TEXT NOT NULL,
            role TEXT NOT NULL,
            allowed_intents_json TEXT NOT NULL DEFAULT '[]',
            scope_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'verified',
            verified_at TEXT,
            last_used_at TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, bot_id, phone_e164),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS operational_command_requests (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            source_channel TEXT NOT NULL,
            source_message_id TEXT,
            source_webhook_receipt_id TEXT,
            actor_user_id TEXT,
            actor_phone_e164 TEXT,
            actor_role TEXT,
            detected_intent TEXT,
            raw_text TEXT,
            parsed_entities_json TEXT NOT NULL DEFAULT '{}',
            resolved_scope_json TEXT NOT NULL DEFAULT '{}',
            risk_level TEXT NOT NULL DEFAULT 'low',
            requires_confirmation INTEGER NOT NULL DEFAULT 0,
            confirmation_code TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            scheduled_for TEXT,
            executed_at TEXT,
            failed_at TEXT,
            cancelled_at TEXT,
            undoable_until TEXT,
            result_json TEXT NOT NULL DEFAULT '{}',
            error_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (actor_user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS operational_command_impacts (
            id TEXT PRIMARY KEY,
            command_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            impact_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            before_json TEXT NOT NULL DEFAULT '{}',
            after_json TEXT NOT NULL DEFAULT '{}',
            reversible INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY (command_id) REFERENCES operational_command_requests(id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id)
        );

        CREATE TABLE IF NOT EXISTS availability_overrides (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            override_type TEXT NOT NULL,
            start_at TEXT NOT NULL,
            end_at TEXT NOT NULL,
            reason TEXT,
            scope_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            created_by TEXT,
            command_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (created_by) REFERENCES users(id),
            FOREIGN KEY (command_id) REFERENCES operational_command_requests(id)
        );

        CREATE TABLE IF NOT EXISTS vacation_periods (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            reason TEXT,
            scope_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            created_by TEXT,
            command_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (created_by) REFERENCES users(id),
            FOREIGN KEY (command_id) REFERENCES operational_command_requests(id)
        );

        CREATE TABLE IF NOT EXISTS appointment_notification_batches (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            command_id TEXT,
            kind TEXT NOT NULL,
            scope_json TEXT NOT NULL DEFAULT '{}',
            message_text TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (command_id) REFERENCES operational_command_requests(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS appointment_notification_targets (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            appointment_id TEXT NOT NULL,
            contact_id TEXT,
            conversation_id TEXT,
            delivery_status TEXT NOT NULL DEFAULT 'queued',
            created_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES appointment_notification_batches(id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (appointment_id) REFERENCES appointments(id),
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS mass_reschedule_batches (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            command_id TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            strategy TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (command_id) REFERENCES operational_command_requests(id)
        );

        CREATE TABLE IF NOT EXISTS mass_reschedule_items (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            appointment_id TEXT NOT NULL,
            old_scheduled_for TEXT,
            new_scheduled_for TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            created_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES mass_reschedule_batches(id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        );

        CREATE TABLE IF NOT EXISTS bot_operational_state_history (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            command_id TEXT,
            previous_state TEXT,
            new_state TEXT,
            message TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (command_id) REFERENCES operational_command_requests(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS scheduled_operational_actions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            command_id TEXT,
            action_type TEXT NOT NULL,
            execute_at TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'scheduled',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (command_id) REFERENCES operational_command_requests(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS bot_temp_messages (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            command_id TEXT,
            message_text TEXT NOT NULL,
            starts_at TEXT,
            expires_at TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (command_id) REFERENCES operational_command_requests(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS operational_undo_tokens (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            command_id TEXT NOT NULL,
            token TEXT NOT NULL,
            expires_at TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (command_id) REFERENCES operational_command_requests(id)
        );

        CREATE INDEX IF NOT EXISTS idx_operational_commands_bot_created ON operational_command_requests(bot_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_operational_commands_phone_status ON operational_command_requests(actor_phone_e164, status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_authorized_operational_numbers_bot_phone ON authorized_operational_numbers(bot_id, phone_e164);
        CREATE INDEX IF NOT EXISTS idx_availability_overrides_bot_start ON availability_overrides(bot_id, start_at, end_at);
        CREATE INDEX IF NOT EXISTS idx_scheduled_operational_actions_bot_execute ON scheduled_operational_actions(bot_id, execute_at, status);
        """
    )


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
    conn.executescript(
        """
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
        """
    )


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

    conn.executescript(
        """
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
        """
    )


def _migration_phase11_whatsapp_template_lifecycle(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS whatsapp_templates (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            default_language TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            fallback_template_id TEXT,
            latest_version_id TEXT,
            approved_version_id TEXT,
            remote_template_id TEXT,
            last_sync_status TEXT NOT NULL DEFAULT 'draft',
            performance_score REAL NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, bot_id, name),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (fallback_template_id) REFERENCES whatsapp_templates(id),
            FOREIGN KEY (latest_version_id) REFERENCES whatsapp_template_versions(id),
            FOREIGN KEY (approved_version_id) REFERENCES whatsapp_template_versions(id)
        );

        CREATE TABLE IF NOT EXISTS whatsapp_template_versions (
            id TEXT PRIMARY KEY,
            template_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            state TEXT NOT NULL DEFAULT 'draft',
            language_code TEXT NOT NULL,
            category TEXT NOT NULL,
            body_text TEXT NOT NULL,
            header_type TEXT NOT NULL DEFAULT 'NONE',
            header_text TEXT,
            footer_text TEXT,
            buttons_json TEXT NOT NULL DEFAULT '[]',
            variables_json TEXT NOT NULL DEFAULT '[]',
            assets_json TEXT NOT NULL DEFAULT '{}',
            sample_values_json TEXT NOT NULL DEFAULT '{}',
            lint_report_json TEXT NOT NULL DEFAULT '{}',
            coverage_json TEXT NOT NULL DEFAULT '{}',
            approval_status TEXT NOT NULL DEFAULT 'draft',
            remote_template_id TEXT,
            remote_status TEXT,
            remote_quality_rating TEXT,
            synced_at TEXT,
            published_at TEXT,
            rejection_reason TEXT,
            fallback_template_id TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(template_id, version_number),
            FOREIGN KEY (template_id) REFERENCES whatsapp_templates(id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (fallback_template_id) REFERENCES whatsapp_templates(id)
        );

        CREATE TABLE IF NOT EXISTS whatsapp_template_sync_runs (
            id TEXT PRIMARY KEY,
            template_id TEXT NOT NULL,
            version_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'meta',
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            request_json TEXT NOT NULL DEFAULT '{}',
            response_json TEXT NOT NULL DEFAULT '{}',
            validation_errors_json TEXT NOT NULL DEFAULT '[]',
            started_at TEXT NOT NULL,
            finished_at TEXT,
            FOREIGN KEY (template_id) REFERENCES whatsapp_templates(id),
            FOREIGN KEY (version_id) REFERENCES whatsapp_template_versions(id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id)
        );

        CREATE TABLE IF NOT EXISTS whatsapp_template_failovers (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            outbox_id TEXT,
            current_template_id TEXT,
            current_version_id TEXT,
            fallback_template_id TEXT,
            fallback_version_id TEXT,
            reason_code TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'runtime',
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (outbox_id) REFERENCES outbox_messages(id),
            FOREIGN KEY (current_template_id) REFERENCES whatsapp_templates(id),
            FOREIGN KEY (current_version_id) REFERENCES whatsapp_template_versions(id),
            FOREIGN KEY (fallback_template_id) REFERENCES whatsapp_templates(id),
            FOREIGN KEY (fallback_version_id) REFERENCES whatsapp_template_versions(id)
        );

        CREATE INDEX IF NOT EXISTS idx_whatsapp_templates_org_bot ON whatsapp_templates(organization_id, bot_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_whatsapp_templates_status ON whatsapp_templates(status, last_sync_status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_whatsapp_template_versions_template ON whatsapp_template_versions(template_id, version_number DESC);
        CREATE INDEX IF NOT EXISTS idx_whatsapp_template_versions_approval ON whatsapp_template_versions(approval_status, remote_status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_whatsapp_template_sync_runs_template ON whatsapp_template_sync_runs(template_id, started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_whatsapp_template_failovers_template ON whatsapp_template_failovers(organization_id, bot_id, created_at DESC);
        """
    )


def _migration_phase12_governed_knowledge_runtime(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            title TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_uri TEXT,
            source_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            owner_type TEXT NOT NULL DEFAULT 'system',
            refresh_strategy TEXT NOT NULL DEFAULT 'manual',
            refresh_after TEXT,
            freshness_window_days INTEGER NOT NULL DEFAULT 30,
            current_version_id TEXT,
            invalidated_reason TEXT,
            tags_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, bot_id, source_key)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_documents_bot_domain ON knowledge_documents(organization_id, bot_id, domain, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_knowledge_documents_refresh ON knowledge_documents(organization_id, bot_id, status, refresh_after);

        CREATE TABLE IF NOT EXISTS knowledge_document_versions (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            content_text TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            vector_json TEXT NOT NULL DEFAULT '{}',
            source_snapshot_json TEXT NOT NULL DEFAULT '{}',
            supports_json TEXT NOT NULL DEFAULT '[]',
            extracted_entities_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            is_current INTEGER NOT NULL DEFAULT 1,
            freshness_status TEXT NOT NULL DEFAULT 'fresh',
            created_at TEXT NOT NULL,
            UNIQUE(document_id, version_number)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_document_versions_doc ON knowledge_document_versions(document_id, is_current, created_at DESC);

        CREATE TABLE IF NOT EXISTS knowledge_refresh_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            freshness_before TEXT,
            freshness_after TEXT,
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_refresh_events_doc ON knowledge_refresh_events(document_id, created_at DESC);
        """
    )




def _migration_phase16_tool_execution_outcomes_flywheel(conn) -> None:
    sql_path = Path(__file__).resolve().parents[1] / "db" / "migrations" / "006_tool_execution_outcomes_flywheel.sql"
    try:
        conn.executescript(sql_path.read_text(encoding="utf-8"))
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
    sql_path = Path(__file__).resolve().parents[1] / "db" / "migrations" / "007_multi_agent_intent_router.sql"
    conn.executescript(sql_path.read_text(encoding="utf-8"))
    _ensure_column(conn, "outcome_exposures", "specialist_agent_key", "TEXT")
    _ensure_column(conn, "outcome_exposures", "specialist_agent_version", "TEXT")
    _ensure_column(conn, "outcome_exposures", "specialist_prompt_id", "TEXT")
    _ensure_column(conn, "outcome_exposures", "intent_family", "TEXT")
    _ensure_column(conn, "outcome_exposures", "agent_routing_run_id", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome_exposures_specialist_agent ON outcome_exposures(specialist_agent_key, sent_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome_exposures_agent_route ON outcome_exposures(agent_routing_run_id, sent_at DESC)")


def _migration_phase18_agent_policy_engine(conn) -> None:
    sql_path = Path(__file__).resolve().parents[1] / "db" / "migrations" / "008_agent_policy_engine.sql"
    conn.executescript(sql_path.read_text(encoding="utf-8"))
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
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS knowledge_source_connections (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            source_key TEXT NOT NULL,
            connector_key TEXT NOT NULL,
            label TEXT NOT NULL,
            source_uri TEXT,
            owner_user_id TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            watch_mode TEXT NOT NULL DEFAULT 'manual',
            sync_interval_minutes INTEGER NOT NULL DEFAULT 60,
            publish_policy TEXT NOT NULL DEFAULT 'auto_publish',
            validation_policy_json TEXT NOT NULL DEFAULT '{}',
            config_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            current_snapshot_hash TEXT,
            last_seen_source_updated_at TEXT,
            last_synced_at TEXT,
            last_published_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, bot_id, source_key)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_source_connections_bot ON knowledge_source_connections(organization_id, bot_id, status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS knowledge_source_sync_runs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            source_connection_id TEXT NOT NULL,
            trigger_kind TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running',
            full_refresh INTEGER NOT NULL DEFAULT 1,
            validate_only INTEGER NOT NULL DEFAULT 0,
            items_seen INTEGER NOT NULL DEFAULT 0,
            items_published INTEGER NOT NULL DEFAULT 0,
            items_skipped INTEGER NOT NULL DEFAULT 0,
            items_invalidated INTEGER NOT NULL DEFAULT 0,
            snapshot_hash TEXT,
            details_json TEXT NOT NULL DEFAULT '{}',
            error_text TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            FOREIGN KEY (source_connection_id) REFERENCES knowledge_source_connections(id)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_source_sync_runs_source ON knowledge_source_sync_runs(source_connection_id, started_at DESC);

        CREATE TABLE IF NOT EXISTS knowledge_source_sync_items (
            id TEXT PRIMARY KEY,
            sync_run_id TEXT NOT NULL,
            source_connection_id TEXT NOT NULL,
            external_item_key TEXT NOT NULL,
            title TEXT,
            source_uri TEXT,
            validation_status TEXT NOT NULL DEFAULT 'passed',
            publication_state TEXT NOT NULL DEFAULT 'published',
            change_status TEXT NOT NULL DEFAULT 'unchanged',
            knowledge_document_id TEXT,
            knowledge_version_id TEXT,
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (sync_run_id) REFERENCES knowledge_source_sync_runs(id),
            FOREIGN KEY (source_connection_id) REFERENCES knowledge_source_connections(id)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_source_sync_items_run ON knowledge_source_sync_items(sync_run_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS knowledge_source_publications (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            source_connection_id TEXT NOT NULL,
            external_item_key TEXT NOT NULL,
            knowledge_document_id TEXT,
            knowledge_version_id TEXT,
            source_kind TEXT NOT NULL,
            source_uri TEXT,
            state TEXT NOT NULL DEFAULT 'published',
            validation_status TEXT NOT NULL DEFAULT 'passed',
            owner_user_id TEXT,
            source_updated_at TEXT,
            published_at TEXT,
            last_synced_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source_connection_id, external_item_key),
            FOREIGN KEY (source_connection_id) REFERENCES knowledge_source_connections(id)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_source_publications_doc ON knowledge_source_publications(knowledge_document_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_knowledge_source_publications_state ON knowledge_source_publications(source_connection_id, state, updated_at DESC);
        """
    )



def _migration_phase15_tool_execution_native(conn) -> None:
    sql_path = Path(__file__).resolve().parents[1] / "db" / "migrations" / "005_tool_execution_native.sql"
    conn.executescript(sql_path.read_text(encoding="utf-8"))

def _migration_phase14_outcomes_closed_loop(conn) -> None:
    sql_path = Path(__file__).resolve().parents[1] / "db" / "migrations" / "004_outcomes_closed_loop.sql"
    conn.executescript(sql_path.read_text(encoding="utf-8"))
    _ensure_column(conn, "outcome_exposures", "prompt_run_id", "TEXT")
    _ensure_column(conn, "outcome_exposures", "decision_path_id", "TEXT")
    _ensure_column(conn, "outcome_exposures", "handoff_id", "TEXT")
    _ensure_column(conn, "outcome_exposures", "handoff_kind", "TEXT")
    _ensure_column(conn, "outcome_exposures", "vertical", "TEXT")
    _ensure_column(conn, "outcome_exposures", "funnel_stage", "TEXT")
    _ensure_column(conn, "outcome_events", "vertical", "TEXT")
    _ensure_column(conn, "outcome_events", "funnel_stage", "TEXT")



def _migration_phase13_human_ops_supervision_runtime(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversation_internal_notes (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            message_id TEXT,
            author_user_id TEXT,
            category TEXT NOT NULL DEFAULT 'general',
            priority TEXT NOT NULL DEFAULT 'normal',
            visibility TEXT NOT NULL DEFAULT 'internal',
            summary TEXT NOT NULL,
            detail TEXT,
            next_steps_json TEXT NOT NULL DEFAULT '[]',
            sources_json TEXT NOT NULL DEFAULT '[]',
            risk_level TEXT NOT NULL DEFAULT 'low',
            risk_flags_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            FOREIGN KEY (message_id) REFERENCES messages(id),
            FOREIGN KEY (author_user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_internal_notes_conversation ON conversation_internal_notes(conversation_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_internal_notes_org_category ON conversation_internal_notes(organization_id, category, created_at DESC);

        CREATE TABLE IF NOT EXISTS conversation_takeover_briefs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            brief_type TEXT NOT NULL,
            content_json TEXT NOT NULL DEFAULT '{}',
            generated_by TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            FOREIGN KEY (generated_by) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_takeover_briefs_conversation ON conversation_takeover_briefs(conversation_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS human_reply_suggestions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            operator_user_id TEXT,
            objective TEXT NOT NULL DEFAULT 'reply',
            draft_text TEXT,
            suggestion_text TEXT NOT NULL,
            explanation_json TEXT NOT NULL DEFAULT '{}',
            sources_json TEXT NOT NULL DEFAULT '[]',
            risk_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'suggested',
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            FOREIGN KEY (operator_user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_reply_suggestions_conversation ON human_reply_suggestions(conversation_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS supervisor_console_snapshots (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            summary_json TEXT NOT NULL DEFAULT '{}',
            teams_json TEXT NOT NULL DEFAULT '[]',
            qa_json TEXT NOT NULL DEFAULT '{}',
            failed_takeovers_json TEXT NOT NULL DEFAULT '[]',
            created_by TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_supervisor_console_snapshots_org ON supervisor_console_snapshots(organization_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS coaching_recommendations (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            source_kind TEXT NOT NULL DEFAULT 'qa_loop',
            summary TEXT NOT NULL,
            recommendation_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id)
        );
        CREATE INDEX IF NOT EXISTS idx_coaching_recommendations_org ON coaching_recommendations(organization_id, target_type, status, updated_at DESC);
        """
    )

def _migration_phase20_proactive_reasoning_engine(conn) -> None:
    sql_path = Path(__file__).resolve().parents[1] / "db" / "migrations" / "010_proactive_reasoning_engine.sql"
    conn.executescript(sql_path.read_text(encoding="utf-8"))




def _migration_phase22_guided_vertical_onboarding(conn) -> None:
    ensure_guided_vertical_onboarding_schema(conn)


def _migration_phase23_voice_first_class_channel(conn) -> None:
    from .voice_channel_runtime import ensure_voice_channel_schema

    ensure_voice_channel_schema(conn)


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
    ensure_vertical_marketplace_schema(conn)


def _migration_phase25_waos_optimizer(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS optimizer_cycles (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            mode TEXT NOT NULL DEFAULT 'auto',
            targets_json TEXT NOT NULL DEFAULT '[]',
            scorecard_window TEXT NOT NULL DEFAULT '28d',
            status TEXT NOT NULL DEFAULT 'planned',
            summary_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_optimizer_cycles_org ON optimizer_cycles(organization_id, bot_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS optimizer_proposals (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            cycle_id TEXT NOT NULL,
            target_name TEXT NOT NULL,
            proposal_kind TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'proposed',
            champion_entity_type TEXT,
            champion_entity_id TEXT,
            challenger_entity_type TEXT,
            challenger_entity_id TEXT,
            summary TEXT NOT NULL,
            rationale_json TEXT NOT NULL DEFAULT '{}',
            change_set_json TEXT NOT NULL DEFAULT '{}',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            applied_decision_id TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_optimizer_proposals_org ON optimizer_proposals(organization_id, bot_id, status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_optimizer_proposals_cycle ON optimizer_proposals(cycle_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS optimizer_experiments (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            proposal_id TEXT NOT NULL,
            experiment_key TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'shadow',
            status TEXT NOT NULL DEFAULT 'planned',
            champion_entity_type TEXT,
            champion_entity_id TEXT,
            candidate_entity_type TEXT,
            candidate_entity_id TEXT,
            rollout_percentage INTEGER NOT NULL DEFAULT 0,
            guardrails_json TEXT NOT NULL DEFAULT '{}',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, experiment_key)
        );
        CREATE INDEX IF NOT EXISTS idx_optimizer_experiments_org ON optimizer_experiments(organization_id, bot_id, status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS optimizer_control_states (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            target_name TEXT NOT NULL,
            current_state_json TEXT NOT NULL DEFAULT '{}',
            last_decision_action TEXT,
            updated_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_optimizer_control_states_org ON optimizer_control_states(organization_id, bot_id, updated_at DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_optimizer_control_states_unique ON optimizer_control_states(organization_id, IFNULL(bot_id, ''), target_name);

        CREATE TABLE IF NOT EXISTS optimizer_change_audits (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            proposal_id TEXT,
            experiment_id TEXT,
            decision_id TEXT,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_optimizer_change_audits_org ON optimizer_change_audits(organization_id, bot_id, created_at DESC);
        """
    )




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

