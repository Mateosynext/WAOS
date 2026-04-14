from __future__ import annotations

from .db import execute, fetch_one
from .utils import hash_value, new_id, to_json, utcnow_iso


def _payload_hash(payload: dict | None) -> str:
    return hash_value(to_json(payload or {}))


def get_job_execution(conn, *, dedupe_key: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM job_idempotency_keys WHERE dedupe_key = ?", (dedupe_key,))


def begin_job_execution(conn, *, job_type: str, dedupe_key: str, payload: dict | None = None) -> dict:
    existing = get_job_execution(conn, dedupe_key=dedupe_key)
    now = utcnow_iso()
    if existing:
        return existing
    row = {
        "id": new_id("idem"),
        "job_type": job_type,
        "dedupe_key": dedupe_key,
        "status": "running",
        "payload_hash": _payload_hash(payload),
        "result_json": "{}",
        "error_text": None,
        "last_run_at": now,
        "created_at": now,
        "updated_at": now,
    }
    execute(
        conn,
        "INSERT INTO job_idempotency_keys (id, job_type, dedupe_key, status, payload_hash, result_json, error_text, last_run_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row["id"], row["job_type"], row["dedupe_key"], row["status"], row["payload_hash"], row["result_json"], row["error_text"], row["last_run_at"], row["created_at"], row["updated_at"]),
    )
    return row


def mark_job_completed(conn, *, dedupe_key: str, result: dict | None = None) -> None:
    execute(
        conn,
        "UPDATE job_idempotency_keys SET status = 'completed', result_json = ?, error_text = NULL, last_run_at = ?, updated_at = ? WHERE dedupe_key = ?",
        (to_json(result or {}), utcnow_iso(), utcnow_iso(), dedupe_key),
    )


def mark_job_failed(conn, *, dedupe_key: str, error_text: str) -> None:
    execute(
        conn,
        "UPDATE job_idempotency_keys SET status = 'failed', error_text = ?, last_run_at = ?, updated_at = ? WHERE dedupe_key = ?",
        (error_text, utcnow_iso(), utcnow_iso(), dedupe_key),
    )
