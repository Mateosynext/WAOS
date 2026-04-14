from __future__ import annotations
import hashlib, hmac, json, os, tempfile, sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient

def _seed(conn, *, hash_password, store_secret, to_json):
    now = '2026-04-12T12:00:00Z'
    conn.execute("INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)", ('usr_admin', 'owner@waos.test', 'Owner User', hash_password('Passw0rd!'), 'org_admin', now, now))
    for org_id, name, slug in [('org_1','Org One','org-one'),('org_2','Org Two','org-two'),('org_3','Org Three','org-three')]:
        conn.execute("INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at) VALUES (?, ?, ?, 'active', 'America/Mexico_City', 'services', '{}', ?, ?)", (org_id, name, slug, now, now))
    for org_id in ['org_1','org_2']:
        conn.execute("INSERT INTO organization_members (id, organization_id, user_id, role, is_active, created_at) VALUES (?, ?, 'usr_admin', 'org_admin', 1, ?)", (f'omem_{org_id}', org_id, now))
    conn.execute("INSERT INTO organization_security_policies (id, organization_id, require_mfa, require_sso, session_ttl_minutes, session_idle_timeout_minutes, step_up_window_minutes, max_sessions_per_user, require_dual_approval_releases, webhook_signature_required, strict_idempotency, ip_allowlist_json, allowed_origins_json, updated_by, created_at, updated_at) VALUES (?, 'org_1', 1, 0, 720, 120, 15, 5, 1, 0, 1, '[]', '[]', 'usr_admin', ?, ?)", ('pol_org1', now, now))
    conn.execute("INSERT INTO organization_security_policies (id, organization_id, require_mfa, require_sso, session_ttl_minutes, session_idle_timeout_minutes, step_up_window_minutes, max_sessions_per_user, require_dual_approval_releases, webhook_signature_required, strict_idempotency, ip_allowlist_json, allowed_origins_json, updated_by, created_at, updated_at) VALUES (?, 'org_2', 0, 0, 720, 120, 15, 5, 1, 0, 1, '[]', '[]', 'usr_admin', ?, ?)", ('pol_org2', now, now))
    conn.execute("INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, config_draft_json, created_at, updated_at) VALUES (?, 'org_1', 'Sales Bot', 'Org One', 'services', 'es', 'America/Mexico_City', 'active', 0, 'published', '{}', ?, ?)", ('bot_1', now, now))
    conn.execute("INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, config_draft_json, created_at, updated_at) VALUES (?, 'org_2', 'Ops Bot', 'Org Two', 'services', 'es', 'America/Mexico_City', 'active', 0, 'published', '{}', ?, ?)", ('bot_2', now, now))
    conn.execute("INSERT INTO whatsapp_numbers (id, organization_id, bot_id, provider, phone_number, phone_number_id, waba_id, connection_status, webhook_verify_token, access_token_masked, metadata_json, created_at, updated_at) VALUES (?, 'org_1', 'bot_1', 'meta', '+525511111111', '123', 'waba_1', 'connected', 'verify-me', 'mask', '{}', ?, ?)", ('wn_1', now, now))
    conn.execute("INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES (?, 'org_1', '+525500000001', 'María Test', 'maria@example.com', '[]', ?, ?)", ('ct_1', now, now))
    conn.execute("INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES (?, 'org_2', '+525500000002', 'Sofía Test', 'sofia@example.com', '[]', ?, ?)", ('ct_2', now, now))
    conn.execute("INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES (?, 'org_1', 'bot_1', 'ct_1', 'ai_active', 0, 1, NULL, NULL, ?, NULL, ?, NULL, ?, ?)", ('conv_1', now, now, now, now))
    conn.execute("INSERT INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, provider_payload_json, reminder_scheduled_at, created_at, updated_at) VALUES (?, 'org_1', 'bot_1', 'conv_1', 'ct_1', '2026-04-15T16:00:00Z', 'pending', 30, 'America/Mexico_City', '{}', ?, ?, ?)", ('apt_org1', now, now, now))
    conn.execute("INSERT INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, provider_payload_json, reminder_scheduled_at, created_at, updated_at) VALUES (?, 'org_2', 'bot_2', NULL, 'ct_2', '2026-04-16T18:00:00Z', 'confirmed', 30, 'America/Mexico_City', '{}', ?, ?, ?)", ('apt_org2', now, now, now))
    conn.execute("INSERT INTO integration_connections (id, organization_id, bot_id, integration_type, provider, name, status, health_status, credential_status, config_json, created_at, updated_at) VALUES (?, 'org_1', 'bot_1', 'payments', 'stripe', 'Stripe', 'active', 'ok', 'healthy', '{}', ?, ?)", ('int_stripe', now, now))
    store_secret(conn, organization_id='org_1', bot_id='bot_1', scope='bot', key_name='STRIPE_WEBHOOK_SECRET', secret_value='whsec_123456789')
    conn.execute("INSERT INTO commerce_payments (id, organization_id, bot_id, conversation_id, contact_id, crm_lead_id, title, amount, currency, status, payment_link_url, payment_link_status, reminder_scheduled_at, confirmed_at, receipt_sent_at, cart_recovery_status, send_receipt_on_confirm, metadata_json, created_at, updated_at) VALUES (?, 'org_1', 'bot_1', 'conv_1', 'ct_1', NULL, 'Pago demo', 999.0, 'MXN', 'pending', NULL, 'generated', NULL, NULL, NULL, 'inactive', 1, ?, ?, ?)", ('pay_1', to_json({'appointment_id': 'apt_org1'}), now, now))

def main() -> None:
    tmpdir = tempfile.TemporaryDirectory(prefix='waos-api-e2e-')
    db_path = Path(tmpdir.name) / 'waos.sqlite3'
    os.environ['APP_ENV'] = 'test'
    os.environ['ALLOW_SQLITE_FOR_TESTS'] = 'true'
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    os.environ['APP_SECRET'] = 'waos-test-secret-1234567890-abcdef'
    os.environ['SECRET_ENCRYPTION_KEY'] = 'waos-test-encryption-key-1234567890'
    os.environ['STRICT_SECURITY_STARTUP'] = 'false'
    from backend.app.db import init_db, get_connection
    from backend.app.main import app
    from backend.app.platform import store_secret
    from backend.app.utils import current_mfa_code, hash_password, to_json
    init_db()
    with get_connection() as conn:
        _seed(conn, hash_password=hash_password, store_secret=store_secret, to_json=to_json)
    with TestClient(app) as client:
        first = client.post('/api/v1/auth/login', json={'email': 'owner@waos.test', 'password': 'Passw0rd!'})
        assert first.status_code == 200 and first.json().get('mfa_setup_required') is True
        secret = parse_qs(urlparse(first.json()['mfa_setup']['provisioning_uri']).query)['secret'][0]
        second = client.post('/api/v1/auth/login', json={'email': 'owner@waos.test', 'password': 'Passw0rd!', 'mfa_setup_code': current_mfa_code(secret)})
        assert second.status_code == 200 and second.json().get('mfa_required') is True
        third = client.post('/api/v1/auth/login', json={'email': 'owner@waos.test', 'password': 'Passw0rd!', 'challenge_id': second.json()['challenge_id'], 'otp_code': current_mfa_code(secret)}, headers={'user-agent': 'qa-e2e'})
        assert third.status_code == 200, third.text
        auth = third.json(); headers = {'Authorization': f"Bearer {auth['access_token']}"}
        assert client.get('/api/v1/auth/me', headers=headers).status_code == 200
        refreshed = client.post('/api/v1/auth/refresh', json={'refresh_token': auth['refresh_token']}); assert refreshed.status_code == 200
        assert client.get('/api/v1/appointments?organization_id=org_2', headers=headers).status_code == 200
        assert client.get('/api/v1/appointments?organization_id=org_3', headers=headers).status_code == 403
        inbound_payload = {'entry': [{'changes': [{'value': {'metadata': {'phone_number_id': '123'}, 'contacts': [{'wa_id': '525500000001', 'profile': {'name': 'Maria'}}], 'messages': [{'id': 'wamid-1', 'from': '525500000001', 'timestamp': '1710000000', 'type': 'text', 'text': {'body': 'Hola, quiero reagendar'}}]}}]}]}
        assert client.post('/webhooks/whatsapp/123', json=inbound_payload).status_code == 200
        assert client.post('/webhooks/whatsapp/123', json=inbound_payload).status_code == 200
        event = {'type': 'checkout.session.completed', 'data': {'object': {'id': 'cs_test_1', 'payment_intent': 'pi_test_1', 'client_reference_id': 'pay_1', 'metadata': {'payment_id': 'pay_1', 'appointment_id': 'apt_org1'}}}}
        payload = json.dumps(event, separators=(',', ':')).encode('utf-8'); ts = '1710000000'; sig = hmac.new(b'whsec_123456789', f'{ts}.{payload.decode("utf-8")}'.encode('utf-8'), hashlib.sha256).hexdigest()
        assert client.post('/webhooks/stripe', content=payload, headers={'stripe-signature': f't={ts},v1={sig}', 'content-type': 'application/json'}).status_code == 200
        with get_connection() as conn:
            payment = conn.execute("SELECT status, provider_status FROM commerce_payments WHERE id = ?", ('pay_1',)).fetchone(); assert payment['status'] == 'paid' and payment['provider_status'] == 'paid'
        assert client.post('/api/v1/sales/payments/pay_1/confirm', headers=headers, json={'provider_reference': 'pi_test_1'}).status_code == 409
        report = client.post('/api/v1/reports/executive/generate', headers=headers, json={'organization_id': 'org_1', 'period_start': '2026-04-01', 'period_end': '2026-04-07', 'bot_id': 'bot_1', 'delivery_channels': ['pdf']})
        assert report.status_code == 200, report.text
        assert client.get(f"/api/v1/reports/executive/{report.json()['id']}/pdf", headers=headers).status_code == 200
        assert client.post('/api/v1/auth/logout', headers=headers, json={'refresh_token': refreshed.json()['refresh_token']}).status_code == 200
        assert client.get('/api/v1/auth/me', headers=headers).status_code == 401
    print('API E2E flows passed: auth+MFA, webhook, payments, reports, multi-org.')
if __name__ == '__main__':
    main()
