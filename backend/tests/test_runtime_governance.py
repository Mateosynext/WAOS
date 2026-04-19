from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_SQLITE_FOR_TESTS", "true")

from backend.app.db import SCHEMA_PATH
from backend.app.migrations import apply_migrations, migration_status
from backend.app.policy_engine import evaluate_policy_action, resolve_intent_keywords


def _conn():
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.row_factory = sqlite3.Row
    conn.executescript(Path(SCHEMA_PATH).read_text())
    return conn, tmp.name


def test_runtime_migrations_create_reasoning_and_lock_tables() -> None:
    conn, name = _conn()
    try:
        apply_migrations(conn)
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "schema_migrations" in tables
        assert "message_operational_reasoning" in tables
        assert "inbound_message_locks" in tables
        assert "knowledge_documents" in tables
        assert "knowledge_document_versions" in tables
        assert "knowledge_refresh_events" in tables
        status = migration_status(conn)
        assert status["pending_count"] == 0
        assert status["current_version"]
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)


def test_policy_engine_supports_tenant_overrides() -> None:
    keywords = resolve_intent_keywords({"runtime_policy": {"intent_keywords": {"pricing": ["tarifa especial"]}}})
    assert "tarifa especial" in keywords["pricing"]
    decision = evaluate_policy_action(
        conversation={"status": "ai_active"},
        classification={"intent": "complaint", "requested_human": False, "urgency_score": 90},
        memory={"lead_score": 10, "memory_json": "{}"},
        bot_config={"runtime_policy": {"handoff_rules": [{"name": "complaint_fast_handoff", "when_intent_in": ["complaint"], "min_urgency_score": 80, "action": "handoff", "reason": "policy complaint"}]}},
    )
    assert decision == {"action": "handoff", "reason": "policy complaint", "policy": "complaint_fast_handoff"}
