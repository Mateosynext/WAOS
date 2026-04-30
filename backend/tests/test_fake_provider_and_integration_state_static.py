from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class FakeProviderAndIntegrationStateStaticTest(unittest.TestCase):
    def test_fake_providers_are_blocked_in_production_startup_and_release_gate(self) -> None:
        config = _read("backend/app/config.py")
        main = _read("backend/app/main.py")
        integrations = _read("backend/app/integrations_runtime.py")
        payments = _read("backend/app/payments_runtime/implementation.py")
        release = _read("backend/app/platform/release.py")

        for content in [config, main, integrations, payments]:
            self.assertIn("WAOS_E2E_FAKE_PROVIDERS cannot be enabled in production", content)
        self.assertIn("self.is_production and self.waos_e2e_fake_providers", config)
        for content in [main, integrations, payments]:
            self.assertIn("settings.is_production and settings.waos_e2e_fake_providers", content)

        self.assertIn("fake_providers_disabled", release)
        self.assertIn("WAOS_E2E_FAKE_PROVIDERS", release)
        self.assertIn("not settings.waos_e2e_fake_providers", release)

    def test_sync_success_no_longer_means_credentials_are_connected(self) -> None:
        worker = _read("backend/worker.py")
        commands = _read("backend/app/application/integration_handlers/commands.py")
        repo = _read("backend/app/repositories/integrations_runtime.py")
        runtime = _read("backend/app/integrations_runtime.py")
        schema = _read("backend/app/runtime_schema_migration.py") + _read("backend/app/migrations.py")

        self.assertNotIn("credential_status = CASE WHEN provider = 'google_calendar' THEN 'connected'", worker)
        self.assertNotIn("credential_status = 'connected'", commands)
        self.assertIn("last_sync_status = 'completed'", worker)
        self.assertIn("last_sync_status = 'failed'", worker)
        self.assertIn("last_sync_status = 'completed'", commands)
        self.assertIn("last_sync_status = 'failed'", commands)

        for column in ["credential_status", "last_sync_status", "provider_verified_at", "last_provider_error"]:
            self.assertIn(column, repo)
            self.assertIn(column, schema)
        self.assertIn("provider_verified_at=utcnow_iso()", runtime)
        self.assertIn("last_provider_error=None", runtime)


if __name__ == "__main__":
    unittest.main()
