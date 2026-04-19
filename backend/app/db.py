from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Iterable

try:  # pragma: no cover - postgres dependency may not exist in local test env
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

try:  # pragma: no cover - optional in local dev
    from psycopg_pool import ConnectionPool
except Exception:  # pragma: no cover
    ConnectionPool = None

from .config import settings
from .backend_runtime import ensure_backend_runtime_schema
from .domains.schema_setup import ensure_v9_schema
from .vertical_transactions import ensure_vertical_transaction_schema
from .vertical_domain_runtime import ensure_vertical_domain_schema
from .talent_runtime import ensure_talent_schema
from .migrations import apply_migrations, migration_status as _migration_status
from .world_class import ensure_world_class_schema
from .world_class_plus import ensure_world_class_plus_schema
from .telemetry_runtime import ensure_telemetry_schema, seed_default_alert_rules

THIS_FILE = Path(__file__).resolve()
ROOT = next(
    (parent for parent in THIS_FILE.parents if (parent / "db" / "schema.sql").exists()),
    THIS_FILE.parents[1],
)
SCHEMA_PATH = ROOT / "db" / "schema.sql"

_POOL_LOCK = Lock()
_PG_POOL: ConnectionPool | None = None


def _build_pg_pool() -> ConnectionPool | None:
    if settings.database_backend != "postgresql" or ConnectionPool is None:
        return None
    return ConnectionPool(
        conninfo=settings.normalized_database_url,
        min_size=max(1, settings.db_pool_min_size),
        max_size=max(settings.db_pool_min_size, settings.db_pool_max_size),
        timeout=max(1, settings.db_pool_timeout_seconds),
        kwargs={"row_factory": dict_row},
        open=True,
    )


def init_connection_pool() -> ConnectionPool | None:
    global _PG_POOL
    if settings.database_backend != "postgresql":
        return None
    with _POOL_LOCK:
        if _PG_POOL is None:
            _PG_POOL = _build_pg_pool()
    return _PG_POOL


def close_connection_pool() -> None:
    global _PG_POOL
    with _POOL_LOCK:
        if _PG_POOL is not None:
            _PG_POOL.close()
            _PG_POOL = None


def get_pool_stats() -> dict[str, int | str]:
    if settings.database_backend != "postgresql":
        return {"backend": settings.database_backend, "pooling": "disabled"}
    pool = init_connection_pool()
    if pool is None:
        return {"backend": settings.database_backend, "pooling": "unavailable"}
    return {
        "backend": settings.database_backend,
        "pooling": "enabled",
        "min_size": settings.db_pool_min_size,
        "max_size": settings.db_pool_max_size,
        "current_size": pool.get_stats().get("pool_size", 0),
        "available": pool.get_stats().get("pool_available", 0),
        "checked_out": pool.get_stats().get("requests_num", 0),
    }


class DBConnection:
    def __init__(self, backend: str, connection: Any, releaser: Callable[[Any], None] | None = None):
        self.backend = backend
        self._connection = connection
        self._releaser = releaser

    def execute(self, sql: str, params: Iterable = ()):
        prepared_sql = _prepare_sql(sql, self.backend)
        return self._connection.execute(prepared_sql, tuple(params))

    def executemany(self, sql: str, params_seq: list[Iterable]):
        prepared_sql = _prepare_sql(sql, self.backend)
        params = [tuple(item) for item in params_seq]
        if self.backend == "postgresql":
            with self._connection.cursor() as cur:
                cur.executemany(prepared_sql, params)
            return
        return self._connection.executemany(prepared_sql, params)

    def executescript(self, script: str) -> None:
        if self.backend == "sqlite":
            self._connection.executescript(script)
            return
        for statement in _split_sql_statements(script):
            cleaned = statement.strip()
            if not cleaned or cleaned.upper().startswith("PRAGMA "):
                continue
            sql = _prepare_sql(cleaned, self.backend)
            with self._connection.cursor() as cur:
                cur.execute(sql)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        if self._releaser is not None:
            self._releaser(self._connection)
            return
        self._connection.close()

    def __enter__(self) -> "DBConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def get_db_path() -> str:
    path = settings.sqlite_path
    if path.startswith("./"):
        return str((Path(__file__).resolve().parents[1] / path[2:]).resolve())
    return path


def _split_sql_statements(script: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    escape_next = False
    for char in script:
        if escape_next:
            current.append(char)
            escape_next = False
            continue
        if char == "\\":
            current.append(char)
            escape_next = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if char == ";" and not in_single and not in_double:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            continue
        current.append(char)
    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements


def _convert_qmark_to_percent_s(sql: str) -> str:
    chunks = sql.split("?")
    if len(chunks) == 1:
        return sql
    return "%s".join(chunks)


def _prepare_sql(sql: str, backend: str) -> str:
    cleaned = sql.strip()
    if backend == "postgresql":
        if cleaned.upper().startswith("PRAGMA "):
            return "SELECT 1"
        return _convert_qmark_to_percent_s(sql)
    return sql


def get_connection() -> DBConnection:
    if settings.database_backend == "sqlite":
        conn = sqlite3.connect(get_db_path(), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        return DBConnection("sqlite", conn)

    if psycopg is None:  # pragma: no cover - triggered only when postgres env is used without dependency installed
        raise RuntimeError(
            "PostgreSQL support requires psycopg. Install dependencies from backend/requirements.txt before running in production."
        )

    pool = init_connection_pool()
    if pool is not None:
        conn = pool.getconn()
        return DBConnection("postgresql", conn, releaser=pool.putconn)

    conn = psycopg.connect(settings.normalized_database_url, row_factory=dict_row)
    return DBConnection("postgresql", conn)


def _column_exists(conn: DBConnection, table: str, column: str) -> bool:
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


def _ensure_column(conn: DBConnection, table: str, column: str, definition: str) -> None:
    if not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def has_column(conn: DBConnection, table: str, column: str) -> bool:
    return _column_exists(conn, table, column)


def table_exists(conn: DBConnection, table: str) -> bool:
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


def migration_status(conn: DBConnection) -> dict[str, object]:
    return _migration_status(conn)


def init_db() -> None:
    if settings.database_backend == "sqlite":
        Path(get_db_path()).parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        ensure_v9_schema(conn)
        ensure_backend_runtime_schema(conn)
        ensure_vertical_transaction_schema(conn)
        ensure_vertical_domain_schema(conn)
        ensure_talent_schema(conn)
        ensure_world_class_schema(conn)
        ensure_world_class_plus_schema(conn)
        ensure_telemetry_schema(conn)
        seed_default_alert_rules(conn)
        _ensure_column(conn, "secret_entries", "value_encrypted", "TEXT")
        _ensure_column(conn, "secret_entries", "encryption_version", "TEXT NOT NULL DEFAULT 'v1'")
        _ensure_column(conn, "secret_entries", "metadata_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "secret_entries", "expires_at", "TEXT")
        _ensure_column(conn, "secret_entries", "last_accessed_at", "TEXT")
        _ensure_column(conn, "secret_entries", "last_access_actor_type", "TEXT")
        _ensure_column(conn, "secret_entries", "last_access_actor_id", "TEXT")

        _ensure_column(conn, "outbox_messages", "provider_message_id", "TEXT")
        _ensure_column(conn, "outbox_messages", "provider_status_code", "INTEGER")
        _ensure_column(conn, "outbox_messages", "provider_response_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "outbox_messages", "next_attempt_at", "TEXT")
        _ensure_column(conn, "outbox_messages", "priority", "INTEGER NOT NULL DEFAULT 50")
        _ensure_column(conn, "outbox_messages", "locked_at", "TEXT")
        _ensure_column(conn, "outbox_messages", "governance_json", "TEXT NOT NULL DEFAULT '{}'")

        _ensure_column(conn, "automation_jobs", "priority", "INTEGER NOT NULL DEFAULT 50")

        _ensure_column(conn, "appointments", "external_id", "TEXT")
        _ensure_column(conn, "appointments", "provider", "TEXT")
        _ensure_column(conn, "appointments", "provider_payload_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "appointments", "integration_id", "TEXT")
        _ensure_column(conn, "appointments", "synced_at", "TEXT")
        _ensure_column(conn, "appointments", "reminder_scheduled_at", "TEXT")
        _ensure_column(conn, "appointments", "confirmed_at", "TEXT")
        _ensure_column(conn, "appointments", "cancelled_at", "TEXT")
        _ensure_column(conn, "appointments", "no_show_at", "TEXT")
        _ensure_column(conn, "appointments", "followup_status", "TEXT NOT NULL DEFAULT 'pending'")
        _ensure_column(conn, "appointments", "followup_sent_at", "TEXT")
        _ensure_column(conn, "appointments", "rescheduled_from_appointment_id", "TEXT")

        _ensure_column(conn, "mfa_factors", "secret_encrypted", "TEXT")
        _ensure_column(conn, "mfa_factors", "secret_masked", "TEXT")
        _ensure_column(conn, "mfa_factors", "recovery_codes_json", "TEXT NOT NULL DEFAULT '[]'")
        _ensure_column(conn, "mfa_factors", "revoked_at", "TEXT")
        _ensure_column(conn, "audit_logs", "request_id", "TEXT")
        _ensure_column(conn, "audit_logs", "session_id", "TEXT")
        _ensure_column(conn, "audit_logs", "ip_address", "TEXT")
        _ensure_column(conn, "audit_logs", "user_agent", "TEXT")
        _ensure_column(conn, "audit_logs", "severity", "TEXT NOT NULL DEFAULT 'info'")
        _ensure_column(conn, "audit_logs", "trace_id", "TEXT")

        _ensure_column(conn, "auth_sessions", "refresh_token_family_id", "TEXT")
        _ensure_column(conn, "auth_sessions", "max_idle_at", "TEXT")
        _ensure_column(conn, "auth_sessions", "idle_timeout_minutes", "INTEGER NOT NULL DEFAULT 120")
        _ensure_column(conn, "auth_sessions", "last_authenticated_at", "TEXT")
        _ensure_column(conn, "auth_sessions", "refresh_token_last_rotated_at", "TEXT")
        _ensure_column(conn, "auth_sessions", "refresh_token_reuse_detected_at", "TEXT")

        _ensure_column(conn, "organization_security_policies", "session_idle_timeout_minutes", "INTEGER NOT NULL DEFAULT 120")
        _ensure_column(conn, "organization_security_policies", "step_up_window_minutes", "INTEGER NOT NULL DEFAULT 15")
        _ensure_column(conn, "organization_security_policies", "max_sessions_per_user", "INTEGER NOT NULL DEFAULT 5")
        _ensure_column(conn, "organization_security_policies", "require_dual_approval_releases", "INTEGER NOT NULL DEFAULT 1")

        _ensure_column(conn, "mfa_factors", "label", "TEXT")

        _ensure_column(conn, "whatsapp_flows", "remote_flow_id", "TEXT")
        _ensure_column(conn, "whatsapp_flows", "remote_status", "TEXT NOT NULL DEFAULT 'not_synced'")
        _ensure_column(conn, "whatsapp_flows", "remote_details_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "whatsapp_flows", "fallback_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "whatsapp_flows", "runtime_config_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "whatsapp_flows", "current_version_id", "TEXT")
        _ensure_column(conn, "whatsapp_flows", "published_version_id", "TEXT")
        _ensure_column(conn, "whatsapp_flows", "runtime_endpoint", "TEXT")
        _ensure_column(conn, "whatsapp_flows", "remote_last_synced_at", "TEXT")
        _ensure_column(conn, "whatsapp_flows", "remote_last_published_at", "TEXT")
        _ensure_column(conn, "whatsapp_flows", "last_sync_error", "TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_whatsapp_flows_remote ON whatsapp_flows(remote_flow_id, remote_status, updated_at)"
        )

        _ensure_column(conn, "whatsapp_numbers", "quality_rating", "TEXT NOT NULL DEFAULT 'unknown'")
        _ensure_column(conn, "whatsapp_numbers", "quality_status", "TEXT NOT NULL DEFAULT 'unknown'")
        _ensure_column(conn, "whatsapp_numbers", "throughput_tier", "TEXT NOT NULL DEFAULT 'standard'")
        _ensure_column(conn, "whatsapp_numbers", "provider_degraded_until", "TEXT")
        _ensure_column(conn, "whatsapp_numbers", "last_health_check_at", "TEXT")
        _ensure_column(conn, "whatsapp_numbers", "last_provider_error_code", "TEXT")
        _ensure_column(conn, "whatsapp_numbers", "last_provider_error_at", "TEXT")

        _ensure_column(conn, "integration_connections", "credential_status", "TEXT NOT NULL DEFAULT 'unknown'")
        _ensure_column(conn, "integration_connections", "last_error", "TEXT")
        _ensure_column(conn, "integration_connections", "last_provider_event_at", "TEXT")
        _ensure_column(conn, "integration_connections", "last_provider_status_code", "INTEGER")
        _ensure_column(conn, "integration_connections", "auto_sync_enabled", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "integration_connections", "sync_frequency_minutes", "INTEGER NOT NULL DEFAULT 30")
        _ensure_column(conn, "integration_connections", "next_sync_at", "TEXT")
        _ensure_column(conn, "integration_connections", "retry_count", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "integration_connections", "last_success_at", "TEXT")
        _ensure_column(conn, "integration_connections", "locked_at", "TEXT")

        _ensure_column(conn, "commerce_payments", "provider", "TEXT")
        _ensure_column(conn, "commerce_payments", "integration_id", "TEXT")
        _ensure_column(conn, "commerce_payments", "provider_reference", "TEXT")
        _ensure_column(conn, "commerce_payments", "external_payment_id", "TEXT")
        _ensure_column(conn, "commerce_payments", "provider_status", "TEXT")
        _ensure_column(conn, "commerce_payments", "provider_status_code", "INTEGER")
        _ensure_column(conn, "commerce_payments", "provider_response_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "commerce_payments", "checkout_expires_at", "TEXT")
        _ensure_column(conn, "commerce_payments", "paid_at", "TEXT")
        _ensure_column(conn, "commerce_payments", "appointment_id", "TEXT")
        _ensure_column(conn, "commerce_payments", "reconciliation_status", "TEXT NOT NULL DEFAULT 'pending'")
        _ensure_column(conn, "commerce_payments", "reconciled_at", "TEXT")
        _ensure_column(conn, "commerce_payments", "next_reconciliation_at", "TEXT")
        _ensure_column(conn, "commerce_payments", "reconciliation_attempts", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "commerce_payments", "last_reconciliation_error", "TEXT")
        _ensure_column(conn, "commerce_payments", "locked_at", "TEXT")

        _ensure_column(conn, "appointments", "payment_id", "TEXT")
        _ensure_column(conn, "appointments", "payment_status", "TEXT")
        _ensure_column(conn, "appointments", "reconciliation_status", "TEXT")

        _ensure_column(conn, "executive_reports", "pdf_path", "TEXT")
        _ensure_column(conn, "executive_reports", "pdf_filename", "TEXT")
        _ensure_column(conn, "executive_reports", "pdf_generated_at", "TEXT")
        _ensure_column(conn, "executive_reports", "updated_at", "TEXT")
        _ensure_column(conn, "report_generation_jobs", "locked_at", "TEXT")

        apply_migrations(conn)

        conn.executescript(
            """
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
            """
        )

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
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_whatsapp_policy_decisions_org ON whatsapp_policy_decisions(organization_id, bot_id, created_at DESC);
            """
        )

        conn.executescript(
            """
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
            """
        )

        conn.executescript(
            """
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
            """
        )
        conn.commit()


def _normalize_row(row: Any) -> dict | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def fetch_one(conn: DBConnection, sql: str, params: Iterable = ()) -> dict | None:
    row = conn.execute(sql, tuple(params)).fetchone()
    return _normalize_row(row)


def fetch_all(conn: DBConnection, sql: str, params: Iterable = ()) -> list[dict]:
    rows = conn.execute(sql, tuple(params)).fetchall()
    return [_normalize_row(row) or {} for row in rows]


def execute(conn: DBConnection, sql: str, params: Iterable = ()) -> None:
    conn.execute(sql, tuple(params))
    conn.commit()


def execute_many(conn: DBConnection, sql: str, params_seq: list[Iterable]) -> None:
    conn.executemany(sql, [tuple(item) for item in params_seq])
    conn.commit()
