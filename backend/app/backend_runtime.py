from __future__ import annotations


def _column_exists(conn, table: str, column: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "sqlite":
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any((row[1] if not isinstance(row, dict) else row.get("name")) == column for row in rows)
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
    if _column_exists(conn, table, column):
        return
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except Exception as exc:
        if "duplicate column" in str(exc).lower() or "already exists" in str(exc).lower():
            return
        raise


def ensure_backend_runtime_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            description TEXT,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS job_idempotency_keys (
            id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            dedupe_key TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            payload_hash TEXT,
            result_json TEXT NOT NULL DEFAULT '{}',
            error_text TEXT,
            last_run_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_job_idempotency_status ON job_idempotency_keys(job_type, status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS report_generation_jobs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            requested_by_user_id TEXT,
            dedupe_key TEXT NOT NULL UNIQUE,
            request_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            report_id TEXT,
            scheduled_for TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 50,
            started_at TEXT,
            completed_at TEXT,
            locked_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (requested_by_user_id) REFERENCES users(id),
            FOREIGN KEY (report_id) REFERENCES executive_reports(id)
        );
        """
    )

    # Existing installations may have report_generation_jobs without priority because
    # CREATE TABLE IF NOT EXISTS does not retrofit new columns onto an existing table.
    # Add it explicitly before creating indexes or issuing ORDER BY priority queries.
    _ensure_column(conn, "report_generation_jobs", "priority", "INTEGER NOT NULL DEFAULT 50")

    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_report_generation_jobs_status ON report_generation_jobs(status, scheduled_for ASC, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_report_generation_jobs_priority ON report_generation_jobs(status, priority DESC, scheduled_for ASC);
        """
    )
