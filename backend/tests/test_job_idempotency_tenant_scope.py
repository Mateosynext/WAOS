from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "backend/app/job_idempotency.py"


def _load_job_idempotency_module():
    package_name = "waos_job_idempotency_testpkg"
    package = types.ModuleType(package_name)
    package.__path__ = []
    db = types.ModuleType(f"{package_name}.db")
    utils = types.ModuleType(f"{package_name}.utils")

    def fetch_one(conn, sql, params=()):
        row = conn.execute(sql, tuple(params)).fetchone()
        return dict(row) if row is not None else None

    def fetch_all(conn, sql, params=()):
        return [dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]

    def table_exists(conn, table):
        row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
        return row is not None

    def has_column(conn, table, column):
        return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})").fetchall())

    def to_json(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def from_json(value, default=None):
        if not value:
            return default
        return json.loads(value)

    def canonical_hash(value):
        return hashlib.sha256(to_json(value).encode("utf-8")).hexdigest()

    db.fetch_one = fetch_one
    db.fetch_all = fetch_all
    db.table_exists = table_exists
    db.has_column = has_column
    utils.to_json = to_json
    utils.from_json = from_json
    utils.canonical_hash = canonical_hash
    utils.utcnow_iso = lambda: "2026-04-27T00:00:00Z"
    counter = {"value": 0}

    def new_id(prefix):
        counter["value"] += 1
        return f"{prefix}_{counter['value']}"

    utils.new_id = new_id

    sys.modules[package_name] = package
    sys.modules[f"{package_name}.db"] = db
    sys.modules[f"{package_name}.utils"] = utils
    spec = importlib.util.spec_from_file_location(f"{package_name}.job_idempotency", TARGET)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, fetch_all, fetch_one


job_idempotency, fetch_all, fetch_one = _load_job_idempotency_module()


def _conn():
    raw = sqlite3.connect(":memory:")
    raw.row_factory = sqlite3.Row
    return raw


class JobIdempotencyTenantScopeTest(unittest.TestCase):
    def test_idempotency_key_is_scoped_by_org_and_action(self) -> None:
        conn = _conn()
        try:
            job_idempotency.ensure_job_idempotency_schema(conn)
            a = job_idempotency.begin_job_execution(conn, job_type="send_whatsapp", dedupe_key="same-key", organization_id="org_a", action_type="send", payload={"organization_id": "org_a", "n": 1})
            b = job_idempotency.begin_job_execution(conn, job_type="send_whatsapp", dedupe_key="same-key", organization_id="org_b", action_type="send", payload={"organization_id": "org_b", "n": 1})
            c = job_idempotency.begin_job_execution(conn, job_type="send_whatsapp", dedupe_key="same-key", organization_id="org_a", action_type="sync", payload={"organization_id": "org_a", "n": 1})
            self.assertNotEqual(a["id"], b["id"])
            self.assertNotEqual(a["id"], c["id"])
            rows = fetch_all(conn, "SELECT organization_id, action_type, dedupe_key FROM job_idempotency_keys WHERE dedupe_key = ? ORDER BY organization_id, action_type", ("same-key",))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows, [
                {"organization_id": "org_a", "action_type": "send", "dedupe_key": "same-key"},
                {"organization_id": "org_a", "action_type": "sync", "dedupe_key": "same-key"},
                {"organization_id": "org_b", "action_type": "send", "dedupe_key": "same-key"},
            ])

            duplicate = job_idempotency.begin_job_execution(conn, job_type="send_whatsapp", dedupe_key="same-key", organization_id="org_a", action_type="send", payload={"organization_id": "org_a", "n": 1})
            self.assertTrue(duplicate["_already_existing"])
            self.assertFalse(duplicate["_payload_mismatch"])

            mismatch = job_idempotency.begin_job_execution(conn, job_type="send_whatsapp", dedupe_key="same-key", organization_id="org_a", action_type="send", payload={"organization_id": "org_a", "n": 2})
            self.assertTrue(mismatch["_already_existing"])
            self.assertTrue(mismatch["_payload_mismatch"])

            job_idempotency.mark_job_completed(conn, dedupe_key="same-key", organization_id="org_a", action_type="send", result={"ok": True})
            org_a_send = fetch_one(conn, "SELECT status FROM job_idempotency_keys WHERE organization_id = 'org_a' AND action_type = 'send' AND dedupe_key = 'same-key'")
            org_b_send = fetch_one(conn, "SELECT status FROM job_idempotency_keys WHERE organization_id = 'org_b' AND action_type = 'send' AND dedupe_key = 'same-key'")
            self.assertEqual(org_a_send["status"], "completed")
            self.assertEqual(org_b_send["status"], "running")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
