from __future__ import annotations

import importlib.util
import sqlite3
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "backend/app/tenant_guard.py"


class HTTPException(Exception):
    def __init__(self, status_code: int, detail=None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _load_tenant_guard_module():
    package_name = "waos_tenant_guard_testpkg"
    package = types.ModuleType(package_name)
    package.__path__ = []
    db = types.ModuleType(f"{package_name}.db")
    security = types.ModuleType(f"{package_name}.security")
    fastapi = types.ModuleType("fastapi")

    def fetch_one(conn, sql, params=()):
        row = conn.execute(sql, tuple(params)).fetchone()
        return dict(row) if row is not None else None

    def ensure_org_access(user, organization_id):
        org_id = str(organization_id or "")
        allowed = {str(item.get("organization_id")) for item in user.get("memberships", [])}
        allowed.update(str(item) for item in user.get("organization_ids", []))
        if org_id not in allowed and user.get("global_role") != "super_admin":
            raise HTTPException(status_code=403, detail="forbidden_cross_tenant")

    db.fetch_one = fetch_one
    security.ensure_org_access = ensure_org_access
    fastapi.HTTPException = HTTPException
    sys.modules[package_name] = package
    sys.modules[f"{package_name}.db"] = db
    sys.modules[f"{package_name}.security"] = security
    sys.modules["fastapi"] = fastapi

    spec = importlib.util.spec_from_file_location(f"{package_name}.tenant_guard", TARGET)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


tenant_guard = _load_tenant_guard_module()
MULTI_TENANT_RESOURCE_SPECS = tenant_guard.MULTI_TENANT_RESOURCE_SPECS
require_same_tenant_resource = tenant_guard.require_same_tenant_resource


CRITICAL_ENDPOINT_FUZZ_CASES = (
    {"method": "GET", "path": "/api/v1/bots/{bot_id}", "resource_type": "bot_id"},
    {"method": "GET", "path": "/api/v1/conversations/{conversation_id}", "resource_type": "conversation_id"},
    {"method": "GET", "path": "/api/v1/ai/workflow-runs/{run_id}", "resource_type": "run_id"},
    {"method": "POST", "path": "/api/v1/tool-executions/{tool_execution_id}/apply", "resource_type": "tool_execution_id"},
    {"method": "GET", "path": "/api/v1/knowledge/documents/{knowledge_document_id}", "resource_type": "knowledge_document_id"},
    {"method": "POST", "path": "/api/v1/integrations/{integration_id}/sync", "resource_type": "integration_id"},
    {"method": "GET", "path": "/api/v1/outcomes/{outcome_id}", "resource_type": "outcome_id"},
    {"method": "GET", "path": "/api/v1/payments/{payment_id}", "resource_type": "payment_id"},
)

ORG_A_USER = {
    "id": "user_a",
    "global_role": "org_admin",
    "memberships": [{"organization_id": "org_a", "role": "org_admin"}],
    "organization_ids": ["org_a"],
}


def _conn():
    raw = sqlite3.connect(":memory:")
    raw.row_factory = sqlite3.Row
    for spec in MULTI_TENANT_RESOURCE_SPECS:
        raw.execute(f"CREATE TABLE {spec.table} (id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, deleted_at TEXT)")
        raw.execute(f"INSERT INTO {spec.table} (id, organization_id) VALUES (?, ?)", (f"local_{spec.resource_type}", "org_a"))
        raw.execute(f"INSERT INTO {spec.table} (id, organization_id) VALUES (?, ?)", (f"foreign_{spec.resource_type}", "org_b"))
    raw.commit()
    return raw


class MultiTenantFuzzRealTest(unittest.TestCase):
    def test_every_critical_resource_id_has_real_cross_tenant_fuzz_guard(self) -> None:
        conn = _conn()
        try:
            covered = {spec.resource_type for spec in MULTI_TENANT_RESOURCE_SPECS}
            expected = {
                "bot_id",
                "conversation_id",
                "run_id",
                "tool_execution_id",
                "knowledge_document_id",
                "integration_id",
                "outcome_id",
                "payment_id",
            }
            self.assertTrue(expected.issubset(covered))
            self.assertEqual({case["resource_type"] for case in CRITICAL_ENDPOINT_FUZZ_CASES}, expected)

            for spec in MULTI_TENANT_RESOURCE_SPECS:
                local = require_same_tenant_resource(
                    conn,
                    user=ORG_A_USER,
                    resource_type=spec.resource_type,
                    resource_id=f"local_{spec.resource_type}",
                    organization_id="org_a",
                )
                self.assertIsNotNone(local)
                self.assertEqual(local["organization_id"], "org_a")

                with self.assertRaises(HTTPException) as cross_tenant:
                    require_same_tenant_resource(
                        conn,
                        user=ORG_A_USER,
                        resource_type=spec.resource_type,
                        resource_id=f"foreign_{spec.resource_type}",
                        organization_id="org_a",
                    )
                self.assertIn(cross_tenant.exception.status_code, {403, 404})
                self.assertNotIn("org_b", str(cross_tenant.exception.detail))

                with self.assertRaises(HTTPException) as implicit_cross_tenant:
                    require_same_tenant_resource(
                        conn,
                        user=ORG_A_USER,
                        resource_type=spec.resource_type,
                        resource_id=f"foreign_{spec.resource_type}",
                    )
                self.assertIn(implicit_cross_tenant.exception.status_code, {403, 404})
                self.assertNotIn("org_b", str(implicit_cross_tenant.exception.detail))
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
