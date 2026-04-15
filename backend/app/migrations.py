from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .utils import to_json, utcnow_iso


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
    _ensure_column(conn, "schema_migrations", "metadata_json", "TEXT NOT NULL DEFAULT '{}' ")


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


MIGRATIONS = [
    Migration(
        version="2026-04-15-runtime-governance-v1",
        description="runtime governance foundations: migrations, inbox indexes, reasoning trail and inbound locks",
        apply=_migration_runtime_governance,
    )
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
