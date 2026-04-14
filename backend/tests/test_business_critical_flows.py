import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_SQLITE_FOR_TESTS", "true")

from backend.app.db import SCHEMA_PATH
from backend.app.backend_runtime import ensure_backend_runtime_schema
from backend.app.domains.schema_setup import ensure_v9_schema
from backend.app.platform.release import create_release_request
from backend.app.payments_runtime import _verify_stripe_signature
from backend.app.domains.appointments import appointment_dashboard

class BusinessCriticalFlowsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.conn = sqlite3.connect(self.tmp.name)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(Path(SCHEMA_PATH).read_text())
        ensure_v9_schema(self.conn)
        ensure_backend_runtime_schema(self.conn)
        self.conn.execute("INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES ('usr_1', 'qa@example.com', 'QA', 'hash', 'super_admin', 1, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')")
        self.conn.execute("INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at) VALUES ('org_1', 'Org', 'org', 'active', 'America/Mexico_City', 'services', '{}', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')")
        self.conn.execute("INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, config_draft_json, created_at, updated_at) VALUES ('bot_1', 'org_1', 'Bot', 'Org', 'services', 'es', 'America/Mexico_City', 'draft', 0, 'draft', '{}', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')")
        self.conn.execute("INSERT INTO bot_versions (id, organization_id, bot_id, version_number, status, config_json, created_by, notes, created_at) VALUES ('ver_1', 'org_1', 'bot_1', 1, 'draft', '{}', 'usr_1', '', '2026-01-01T00:00:00Z')")
        self.conn.execute("INSERT INTO bot_versions (id, organization_id, bot_id, version_number, status, config_json, created_by, notes, created_at) VALUES ('ver_2', 'org_1', 'bot_1', 2, 'published', '{}', 'usr_1', '', '2026-01-02T00:00:00Z')")
        self.conn.execute("INSERT INTO secret_entries (id, organization_id, bot_id, scope, key_name, value_masked, value_encrypted, encryption_version, metadata_json, expires_at, last_rotated_at, created_at, updated_at) VALUES ('sec_1', 'org_1', NULL, 'organization', 'STRIPE_WEBHOOK_SECRET', '****', 'enc', 'v2', '{}', NULL, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')")
        self.conn.execute("INSERT INTO organization_security_policies (id, organization_id, require_mfa, require_sso, session_ttl_minutes, session_idle_timeout_minutes, step_up_window_minutes, max_sessions_per_user, require_dual_approval_releases, webhook_signature_required, strict_idempotency, ip_allowlist_json, allowed_origins_json, updated_by, created_at, updated_at) VALUES ('pol_1', 'org_1', 0, 0, 720, 120, 15, 5, 1, 1, 1, '[]', '[]', 'usr_1', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')")
        self.conn.execute("INSERT INTO audit_logs (id, organization_id, actor_user_id, actor_type, entity_type, entity_id, action, severity, metadata_json, created_at) VALUES ('aud_1', 'org_1', 'usr_1', 'user', 'release', 'rel_x', 'release.requested', 'info', '{}', '2026-01-01T00:00:00Z')")
        self.conn.execute("INSERT INTO whatsapp_numbers (id, organization_id, bot_id, provider, phone_number, phone_number_id, waba_id, connection_status, webhook_verify_token, access_token_masked, metadata_json, created_at, updated_at) VALUES ('wn_1', 'org_1', 'bot_1', 'meta', '+525511111111', '123', 'waba_1', 'connected', 'verify', 'mask', '{}', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')")
        self.conn.execute("INSERT INTO integration_connections (id, organization_id, bot_id, integration_type, provider, name, status, health_status, credential_status, config_json, created_at, updated_at) VALUES ('int_1', 'org_1', 'bot_1', 'payments', 'stripe', 'Stripe', 'active', 'ok', 'healthy', '{}', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')")
        self.conn.execute("INSERT INTO appointments (id, organization_id, bot_id, contact_id, conversation_id, scheduled_for, status, duration_minutes, timezone, provider_payload_json, reminder_scheduled_at, created_at, updated_at) VALUES ('apt_1', 'org_1', 'bot_1', NULL, NULL, '2026-01-05T10:00:00Z', 'pending', 30, 'America/Mexico_City', '{}', '2026-01-05T08:00:00Z', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')")
        self.conn.commit()
    def tearDown(self):
        self.conn.close(); Path(self.tmp.name).unlink(missing_ok=True)
    def test_stripe_signature_is_fail_closed_without_secret(self):
        self.assertFalse(_verify_stripe_signature(b'{}', None, None))
    def test_appointment_dashboard_includes_pending(self):
        data = appointment_dashboard(self.conn, 'org_1', 'bot_1')
        self.assertIn('pending', data['summary'])
        self.assertEqual(data['summary']['pending'], 1)
    def test_release_checklist_uses_real_evidence(self):
        row = create_release_request(self.conn, organization_id='org_1', bot_id='bot_1', requested_by='usr_1', title='Release', notes='Notes', validation={'ok': True, 'warnings': []}, diff_summary={'total_changes': 3, 'fingerprints': {'left': 'a', 'right': 'b'}})
        stored = self.conn.execute("SELECT checklist_json FROM release_requests WHERE id = ?", (row['id'],)).fetchone()
        self.assertIn('channel_ready', stored['checklist_json'])
        self.assertIn('payments_ready', stored['checklist_json'])

if __name__ == '__main__':
    unittest.main()
