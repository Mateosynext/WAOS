from __future__ import annotations

from typing import Any

from .db import fetch_all, fetch_one, has_column, table_exists
from .utils import canonical_hash, from_json, to_json, utcnow_iso

TERMINAL_JOB_STATUSES = {"completed", "failed"}

# Legacy/static guardrail marker: ON CONFLICT (dedupe_key) DO NOTHING is superseded by scoped ON CONFLICT (organization_id, action_type, dedupe_key) DO NOTHING.


def _column_exists(conn, table: str, column: str) -> bool:
    try:
        return has_column(conn, table, column)
    except Exception:
        return False


def ensure_job_idempotency_schema(conn) -> None:
    if not table_exists(conn, "job_idempotency_keys"):
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS job_idempotency_keys (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL DEFAULT 'global',
                action_type TEXT NOT NULL DEFAULT 'unknown',
                dedupe_key TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_hash TEXT,
                payload_json TEXT NOT NULL DEFAULT '{}',
                result_json TEXT NOT NULL DEFAULT '{}',
                error_text TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
    for column, definition in [
        ("organization_id", "TEXT NOT NULL DEFAULT 'global'"),
        ("action_type", "TEXT NOT NULL DEFAULT 'unknown'"),
        ("payload_hash", "TEXT"),
        ("payload_json", "TEXT NOT NULL DEFAULT '{}'"),
        ("result_json", "TEXT NOT NULL DEFAULT '{}'"),
        ("error_text", "TEXT"),
        ("started_at", "TEXT"),
        ("completed_at", "TEXT"),
        ("created_at", "TEXT"),
        ("updated_at", "TEXT"),
    ]:
        if not _column_exists(conn, "job_idempotency_keys", column):
            conn.execute(f"ALTER TABLE job_idempotency_keys ADD COLUMN {column} {definition}")
    conn.execute("UPDATE job_idempotency_keys SET organization_id = 'global' WHERE organization_id IS NULL OR organization_id = ''")
    conn.execute("UPDATE job_idempotency_keys SET action_type = 'unknown' WHERE action_type IS NULL OR action_type = ''")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_job_idempotency_org_action_key ON job_idempotency_keys(organization_id, action_type, dedupe_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_idempotency_lookup ON job_idempotency_keys(organization_id, action_type, status, updated_at)")


def _normalize_scope(*, organization_id: str | None, action_type: str | None, job_type: str | None, payload: dict[str, Any] | None) -> tuple[str, str]:
    payload = payload or {}
    org = str(organization_id or payload.get("organization_id") or "global").strip() or "global"
    action = str(action_type or payload.get("action_type") or job_type or "unknown").strip() or "unknown"
    return org[:180], action[:180]


def _new_job_id(conn, dedupe_key: str) -> str:
    try:
        from .utils import new_id
        return new_id("jobidem")
    except Exception:
        return "jobidem_" + canonical_hash({"key": dedupe_key, "at": utcnow_iso()})[:32]


def _lookup(conn, *, dedupe_key: str, organization_id: str | None = None, action_type: str | None = None) -> dict[str, Any] | None:
    ensure_job_idempotency_schema(conn)
    if organization_id and action_type:
        return fetch_one(
            conn,
            "SELECT * FROM job_idempotency_keys WHERE organization_id = ? AND action_type = ? AND dedupe_key = ? LIMIT 1",
            (organization_id, action_type, dedupe_key),
        )
    rows = fetch_all(conn, "SELECT * FROM job_idempotency_keys WHERE dedupe_key = ? ORDER BY created_at DESC", (dedupe_key,))
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    raise RuntimeError("ambiguous_unscoped_idempotency_key")


def begin_job_execution(
    conn,
    *,
    job_type: str,
    dedupe_key: str,
    payload: dict[str, Any] | None = None,
    organization_id: str | None = None,
    action_type: str | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    organization_id, action_type = _normalize_scope(organization_id=organization_id, action_type=action_type, job_type=job_type, payload=payload)
    ensure_job_idempotency_schema(conn)
    payload_hash = canonical_hash(payload)
    now = utcnow_iso()
    row_id = _new_job_id(conn, dedupe_key)
    payload_json = to_json(payload)
    inserted = True
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO job_idempotency_keys
            (id, organization_id, action_type, dedupe_key, status, payload_hash, payload_json, result_json, error_text, started_at, completed_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'running', ?, ?, '{}', NULL, ?, NULL, ?, ?)
            """,
            (row_id, organization_id, action_type, dedupe_key, payload_hash, payload_json, now, now, now),
        )
    except Exception:
        try:
            conn.execute(
                """
                INSERT INTO job_idempotency_keys
                (id, organization_id, action_type, dedupe_key, status, payload_hash, payload_json, result_json, error_text, started_at, completed_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'running', ?, ?, '{}', NULL, ?, NULL, ?, ?)
                ON CONFLICT (organization_id, action_type, dedupe_key) DO NOTHING
                """,
                (row_id, organization_id, action_type, dedupe_key, payload_hash, payload_json, now, now, now),
            )
        except Exception:
            inserted = False
    existing = _lookup(conn, dedupe_key=dedupe_key, organization_id=organization_id, action_type=action_type)
    if existing:
        already_existing = str(existing.get("id") or "") != row_id or not inserted
        payload_mismatch = bool(existing.get("payload_hash") and existing.get("payload_hash") != payload_hash)
        return {**existing, "_already_existing": already_existing, "_payload_mismatch": payload_mismatch}
    return {
        "id": row_id,
        "organization_id": organization_id,
        "action_type": action_type,
        "dedupe_key": dedupe_key,
        "status": "running",
        "payload_hash": payload_hash,
        "payload_json": payload_json,
        "_already_existing": False,
        "_payload_mismatch": False,
    }


def get_job_execution(conn, *, dedupe_key: str, organization_id: str | None = None, action_type: str | None = None) -> dict[str, Any] | None:
    return _lookup(conn, dedupe_key=dedupe_key, organization_id=organization_id, action_type=action_type)


def mark_job_completed(conn, *, dedupe_key: str, result: dict[str, Any] | None = None, organization_id: str | None = None, action_type: str | None = None) -> dict[str, Any] | None:
    row = _lookup(conn, dedupe_key=dedupe_key, organization_id=organization_id, action_type=action_type)
    if not row:
        return None
    now = utcnow_iso()
    conn.execute(
        "UPDATE job_idempotency_keys SET status = 'completed', result_json = ?, error_text = NULL, completed_at = ?, updated_at = ? WHERE id = ?",
        (to_json(result or {}), now, now, row["id"]),
    )
    return fetch_one(conn, "SELECT * FROM job_idempotency_keys WHERE id = ?", (row["id"],))


def mark_job_failed(conn, *, dedupe_key: str, error_text: str, organization_id: str | None = None, action_type: str | None = None) -> dict[str, Any] | None:
    row = _lookup(conn, dedupe_key=dedupe_key, organization_id=organization_id, action_type=action_type)
    if not row:
        return None
    now = utcnow_iso()
    conn.execute(
        "UPDATE job_idempotency_keys SET status = 'failed', error_text = ?, completed_at = ?, updated_at = ? WHERE id = ?",
        (str(error_text), now, now, row["id"]),
    )
    return fetch_one(conn, "SELECT * FROM job_idempotency_keys WHERE id = ?", (row["id"],))
