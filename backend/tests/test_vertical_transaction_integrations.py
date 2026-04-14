from __future__ import annotations

import json
import os

os.environ.setdefault('WAOS_E2E_FAKE_PROVIDERS', 'true')

from backend.app.db import execute, fetch_one, get_connection, init_db
from backend.app.platform.secrets import store_secret
from backend.app.utils import new_id, to_json, utcnow_iso
from backend.app.vertical_transactions import vertical_transaction_service
from backend.app.payments_runtime import handle_stripe_webhook


def _seed_runtime() -> tuple[dict, str, str, str, str]:
    organization_id = new_id('org')
    user_id = new_id('user')
    bot_id = new_id('bot')
    contact_id = new_id('ctc')
    conversation_id = new_id('conv')
    now = utcnow_iso()
    with get_connection() as conn:
        execute(conn, "INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)", (user_id, f"{user_id}@example.com", "Runtime User", "not-used", "super_admin", now, now))
        execute(conn, "INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at) VALUES (?, ?, ?, 'active', 'America/Mexico_City', NULL, '{}', ?, ?)", (organization_id, 'Org Test', f'org-{organization_id[-8:]}', now, now))
        execute(conn, "INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, published_version_id, config_draft_json, created_at, updated_at, deleted_at) VALUES (?, ?, ?, ?, 'fitness', 'es', 'America/Mexico_City', 'active', 0, 'published', NULL, '{}', ?, ?, NULL)", (bot_id, organization_id, 'Bot Demo', 'Bot Demo', now, now))
        execute(conn, "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, '[]', ?, ?)", (contact_id, organization_id, '+525500000001', 'Contacto Demo', 'demo@example.com', now, now))
        execute(conn, "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, 'open', 0, 1, NULL, NULL, ?, NULL, NULL, NULL, ?, ?)", (conversation_id, organization_id, bot_id, contact_id, now, now, now))
        execute(conn, "INSERT INTO integration_connections (id, organization_id, bot_id, integration_type, provider, name, status, health_status, credential_status, last_error, config_json, last_test_at, last_sync_at, created_at, updated_at, auto_sync_enabled, sync_frequency_minutes, next_sync_at, retry_count, last_provider_event_at, last_provider_status_code) VALUES (?, ?, ?, 'payments', 'stripe', 'Stripe', 'active', 'healthy', 'configured', NULL, ?, NULL, NULL, ?, ?, 0, 30, NULL, 0, NULL, NULL)", (new_id('int'), organization_id, bot_id, to_json({'secret_key': 'sk_test_demo', 'webhook_secret': 'whsec_demo'}), now, now))
        execute(conn, "INSERT INTO integration_connections (id, organization_id, bot_id, integration_type, provider, name, status, health_status, credential_status, last_error, config_json, last_test_at, last_sync_at, created_at, updated_at, auto_sync_enabled, sync_frequency_minutes, next_sync_at, retry_count, last_provider_event_at, last_provider_status_code) VALUES (?, ?, ?, 'calendar', 'google_calendar', 'Google Calendar', 'active', 'healthy', 'connected', NULL, ?, NULL, NULL, ?, ?, 1, 30, ?, 0, NULL, NULL)", (new_id('int'), organization_id, bot_id, to_json({'calendar_id': 'primary', 'timezone': 'America/Mexico_City'}), now, now, now))
        store_secret(conn, organization_id=organization_id, bot_id=bot_id, scope='bot', key_name='GOOGLE_ACCESS_TOKEN', secret_value='tok_demo_12345')
    actor = {'id': user_id, 'global_role': 'super_admin', 'organization_ids': [organization_id]}
    return actor, organization_id, bot_id, contact_id, conversation_id


def test_transaction_runtime_connects_payments_calendar_and_webhook_roundtrip() -> None:
    init_db()
    actor, organization_id, bot_id, contact_id, conversation_id = _seed_runtime()
    with get_connection() as conn:
        account = vertical_transaction_service.create_account(
            conn,
            organization_id=organization_id,
            vertical_id='fitness',
            bot_id=bot_id,
            contact_id=contact_id,
            actor_user=actor,
            metadata={'conversation_id': conversation_id},
            external_reference='fitness-connected-demo',
        )
        quoted = vertical_transaction_service.dispatch_command(
            conn,
            organization_id=organization_id,
            account_id=account['id'],
            command_name='create_quote',
            payload={'idempotency_key': 'quote-1', 'amount': 1999, 'title': 'Plan mensual'},
            actor_user=actor,
        )
        quoted_account = quoted['account']
        payment_id = quoted_account['metadata']['last_payment_id']
        payment = fetch_one(conn, 'SELECT * FROM commerce_payments WHERE id = ?', (payment_id,))
        assert payment is not None
        assert payment['payment_link_url']
        assert payment['provider'] == 'stripe'

        booked = vertical_transaction_service.dispatch_command(
            conn,
            organization_id=organization_id,
            account_id=account['id'],
            command_name='confirm_booking',
            payload={'idempotency_key': 'booking-1', 'scheduled_for': '2026-04-20T10:00:00Z', 'duration_minutes': 50},
            actor_user=actor,
        )
        booked_account = booked['account']
        appointment_id = booked_account['metadata']['last_appointment_id']
        appointment = fetch_one(conn, 'SELECT * FROM appointments WHERE id = ?', (appointment_id,))
        assert appointment is not None
        assert appointment['provider'] == 'google_calendar'
        assert appointment['external_id']

        webhook_payload = {
            'type': 'checkout.session.completed',
            'data': {'object': {'id': 'cs_fake_paid', 'payment_intent': 'pi_fake_paid', 'metadata': {'payment_id': payment_id}}},
        }
        result = handle_stripe_webhook(conn, payload=json.dumps(webhook_payload).encode('utf-8'), signature=None)
        assert result['ok'] is True

        final_account = vertical_transaction_service.get_account(conn, organization_id=organization_id, account_id=account['id'])
        assert final_account['payment_status'] == 'paid'
        assert final_account['amount_collected'] >= 1999
        assert any(item['reference_id'] == payment_id for item in final_account['ledger'])
