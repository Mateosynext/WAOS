from __future__ import annotations
import json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
API_PORT = int(os.environ.get('PLAYWRIGHT_API_PORT', '4100'))
FRONTEND_PORT = int(os.environ.get('PLAYWRIGHT_FRONTEND_PORT', '3000'))
DB_PATH = ROOT / 'backend' / '.tmp' / 'playwright-browser-e2e.sqlite3'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('APP_ENV', 'test')
os.environ.setdefault('ALLOW_SQLITE_FOR_TESTS', 'true')
os.environ.setdefault('STRICT_SECURITY_STARTUP', 'false')
os.environ.setdefault('DATABASE_URL', f'sqlite:///{DB_PATH}')
os.environ.setdefault('APP_SECRET', 'waos-browser-e2e-secret-1234567890-abcdef')
os.environ.setdefault('SECRET_ENCRYPTION_KEY', 'waos-browser-e2e-encryption-key-1234567890-ab')
os.environ.setdefault('PUBLIC_APP_URL', f'http://127.0.0.1:{FRONTEND_PORT}')
os.environ.setdefault('API_BASE_URL', f'http://127.0.0.1:{API_PORT}')
os.environ.setdefault('API_INTERNAL_URL', f'http://127.0.0.1:{API_PORT}')
os.environ.setdefault('WAOS_E2E_FAKE_PROVIDERS', 'true')
from backend.app.db import init_db, get_connection, execute
from backend.app.platform import store_secret, enroll_mfa_factor, activate_mfa_factor
from backend.app.utils import current_mfa_code, hash_password, to_json, utcnow_iso
from backend.app.main import app  # noqa: F401

def reset_db() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()

def ensure_user(conn, *, user_id: str, email: str, full_name: str, password: str, global_role: str) -> None:
    now = utcnow_iso()
    execute(conn, "INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)", (user_id, email, full_name, hash_password(password), global_role, now, now))

def seed() -> None:
    now = '2026-04-13T12:00:00Z'
    valid_config = {
        'identity': {'bot_name': 'WAOS Sales Concierge', 'business_name': 'Acme North'},
        'objective': {'primary': 'Convertir conversaciones a cita y pago'},
        'business_knowledge': {'services': [{'name': 'Demo comercial', 'price': 999}], 'hours': {'monday': ['09:00-18:00']}, 'faqs': [{'q': 'Costo', 'a': 'Desde 999 MXN'}]},
        'rules': {'cannot_say': ['inventar disponibilidad']},
        'agenda': {'availability': {'timezone': 'America/Mexico_City'}},
        'followups': {'rules': [{'trigger': 'no_show', 'action': 'recovery'}]},
        'integrations': {'whatsapp': {'provider': 'meta_cloud_api'}, 'calendar': {'mode': 'connected', 'calendar_id': 'calendar_1'}},
    }
    with get_connection() as conn:
        ensure_user(conn, user_id='usr_owner', email='owner@waos.test', full_name='Owner User', password='Passw0rd!', global_role='super_admin')
        ensure_user(conn, user_id='usr_client', email='client@waos.test', full_name='Client User', password='Passw0rd!', global_role='client')
        ensure_user(conn, user_id='usr_mfa', email='mfa@waos.test', full_name='MFA User', password='Passw0rd!', global_role='super_admin')
        ensure_user(conn, user_id='usr_sso', email='sso@enterprise.test', full_name='SSO User', password='Passw0rd!', global_role='super_admin')
        for org_id, name, slug, vertical in [('org_1', 'Acme North', 'acme-north', 'services'), ('org_2', 'Acme South', 'acme-south', 'services'), ('org_3', 'Restricted Org', 'restricted-org', 'services')]:
            execute(conn, "INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at) VALUES (?, ?, ?, 'active', 'America/Mexico_City', ?, '{}', ?, ?)", (org_id, name, slug, vertical, now, now))
        for row_id, org_id, user_id, role in [('omem_owner_1', 'org_1', 'usr_owner', 'org_admin'), ('omem_owner_2', 'org_2', 'usr_owner', 'org_admin'), ('omem_client_1', 'org_1', 'usr_client', 'client'), ('omem_mfa_1', 'org_1', 'usr_mfa', 'org_admin'), ('omem_sso_1', 'org_1', 'usr_sso', 'org_admin')]:
            execute(conn, "INSERT INTO organization_members (id, organization_id, user_id, role, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)", (row_id, org_id, user_id, role, now))
        for row_id, org_id, require_mfa, require_sso, dual_approval, webhook_required in [('pol_org1', 'org_1', 1, 0, 0, 1), ('pol_org2', 'org_2', 0, 0, 0, 1)]:
            execute(conn, "INSERT INTO organization_security_policies (id, organization_id, require_mfa, require_sso, session_ttl_minutes, session_idle_timeout_minutes, step_up_window_minutes, max_sessions_per_user, require_dual_approval_releases, webhook_signature_required, strict_idempotency, ip_allowlist_json, allowed_origins_json, updated_by, created_at, updated_at) VALUES (?, ?, ?, ?, 720, 120, 15, 5, ?, ?, 1, '[]', '[]', 'usr_owner', ?, ?)", (row_id, org_id, require_mfa, require_sso, dual_approval, webhook_required, now, now))
        for bot_id, org_id, name in [('bot_1', 'org_1', 'Acme Concierge'), ('bot_2', 'org_2', 'South Sales Bot')]:
            execute(conn, "INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, config_draft_json, created_at, updated_at) VALUES (?, ?, ?, ?, 'services', 'es', 'America/Mexico_City', 'active', 0, 'published', ?, ?, ?)", (bot_id, org_id, name, 'Acme', to_json(valid_config), now, now))
        execute(conn, "INSERT INTO bot_versions (id, organization_id, bot_id, version_number, status, config_json, created_by, notes, created_at) VALUES ('ver_1', 'org_1', 'bot_1', 1, 'published', ?, 'usr_owner', 'Initial publish', ?)", (to_json(valid_config), now))
        execute(conn, "UPDATE bots SET published_version_id = 'ver_1' WHERE id = 'bot_1'")
        execute(conn, "INSERT INTO bot_versions (id, organization_id, bot_id, version_number, status, config_json, created_by, notes, created_at) VALUES ('ver_2', 'org_2', 'bot_2', 1, 'published', ?, 'usr_owner', 'Initial publish', ?)", (to_json(valid_config), now))
        execute(conn, "UPDATE bots SET published_version_id = 'ver_2' WHERE id = 'bot_2'")
        execute(conn, "INSERT INTO bot_behavior_settings (id, organization_id, bot_id, tone, response_length, use_emojis, sales_intensity, offer_promotions_when, escalate_when_json, insistence_policy, can_share_price_directly, can_negotiate, can_mention_stock, auto_send_images, bot_mode, active_hours_json, active_channels_json, forbidden_topics_json, required_phrases_json, fallback_message, created_at, updated_at) VALUES ('beh_1', 'org_1', 'bot_1', 'claro', 'media', 0, 'media', 'always', '[]', 'soft', 1, 0, 1, 1, 'ventas', '{}', '[\"whatsapp\"]', '[]', '[]', 'Te apoyo con eso.', ?, ?)", (now, now))
        execute(conn, "INSERT INTO bot_behavior_settings (id, organization_id, bot_id, tone, response_length, use_emojis, sales_intensity, offer_promotions_when, escalate_when_json, insistence_policy, can_share_price_directly, can_negotiate, can_mention_stock, auto_send_images, bot_mode, active_hours_json, active_channels_json, forbidden_topics_json, required_phrases_json, fallback_message, created_at, updated_at) VALUES ('beh_2', 'org_2', 'bot_2', 'formal', 'corta', 0, 'baja', 'never', '[]', 'soft', 1, 0, 1, 0, 'soporte', '{}', '[\"whatsapp\"]', '[]', '[]', 'Te apoyo con eso.', ?, ?)", (now, now))
        execute(conn, "INSERT INTO bot_response_templates (id, organization_id, bot_id, template_key, channel, title, content, variables_json, is_active, created_at, updated_at) VALUES ('tpl_1', 'org_1', 'bot_1', 'welcome', 'whatsapp', 'Welcome', 'Hola, te ayudo a reservar.', '[]', 1, ?, ?)", (now, now))
        execute(conn, "INSERT INTO bot_response_templates (id, organization_id, bot_id, template_key, channel, title, content, variables_json, is_active, created_at, updated_at) VALUES ('tpl_2', 'org_2', 'bot_2', 'welcome', 'whatsapp', 'Welcome', 'Hola, te ayudo a dar seguimiento.', '[]', 1, ?, ?)", (now, now))
        execute(conn, "INSERT INTO catalog_services (id, organization_id, bot_id, category_id, name, duration_minutes, price, currency, preparation, restrictions, availability_json, photos_json, associated_staff, branch, status, created_at, updated_at) VALUES ('srv_1', 'org_1', 'bot_1', NULL, 'Demo comercial', 30, 999, 'MXN', '', '', '{}', '[]', 'Sales Team', 'North', 'active', ?, ?)", (now, now))
        execute(conn, "INSERT INTO catalog_promotions (id, organization_id, bot_id, name, promo_type, message_short, message_long, banner_asset_id, applies_to_json, channels_json, starts_at, ends_at, stock_limit, branch, priority, cta_label, cta_url, legal_terms, promo_code, status, auto_offer_enabled, created_at, updated_at) VALUES ('pro_1', 'org_1', 'bot_1', 'Promo abril', 'discount', '10% off en onboarding', '10% off en onboarding', NULL, '[]', '[\"whatsapp\"]', '2026-04-01', '2026-04-30', NULL, 'North', 1, 'Ver promo', '/promotions', '', 'ABRIL10', 'active', 1, ?, ?)", (now, now))
        execute(conn, "INSERT INTO whatsapp_numbers (id, organization_id, bot_id, provider, phone_number, phone_number_id, waba_id, connection_status, webhook_verify_token, access_token_masked, metadata_json, created_at, updated_at) VALUES ('wn_1', 'org_1', 'bot_1', 'meta', '+525511111111', '123', 'waba_1', 'connected', 'verify-me', 'mask', '{}', ?, ?)", (now, now))
        store_secret(conn, organization_id='org_1', bot_id='bot_1', scope='bot', key_name='META_ACCESS_TOKEN', secret_value='meta-token-test')
        store_secret(conn, organization_id='org_1', bot_id='bot_1', scope='bot', key_name='STRIPE_SECRET_KEY', secret_value='sk_test_fake')
        store_secret(conn, organization_id='org_1', bot_id='bot_1', scope='bot', key_name='STRIPE_WEBHOOK_SECRET', secret_value='whsec_123456789')
        execute(conn, "INSERT INTO integration_connections (id, organization_id, bot_id, integration_type, provider, name, status, health_status, credential_status, config_json, created_at, updated_at, auto_sync_enabled, sync_frequency_minutes, next_sync_at, retry_count) VALUES ('int_stripe', 'org_1', 'bot_1', 'payments', 'stripe', 'Stripe', 'active', 'ok', 'connected', ?, ?, ?, 1, 10, ?, 0)", (to_json({'success_url': f'http://127.0.0.1:{FRONTEND_PORT}/revenue?payment_success=1', 'cancel_url': f'http://127.0.0.1:{FRONTEND_PORT}/revenue?payment_cancelled=1'}), now, now, now))
        execute(conn, "INSERT INTO integration_connections (id, organization_id, bot_id, integration_type, provider, name, status, health_status, credential_status, config_json, created_at, updated_at, auto_sync_enabled, sync_frequency_minutes, next_sync_at, retry_count) VALUES ('int_calendar', 'org_1', 'bot_1', 'calendar', 'google_calendar', 'Google Calendar', 'active', 'ok', 'connected', ?, ?, ?, 1, 30, ?, 0)", (to_json({'calendar_id': 'calendar_1', 'timezone': 'America/Mexico_City'}), now, now, now))
        execute(conn, "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES ('ct_1', 'org_1', '+525500000001', 'María Test', 'maria@example.com', '[]', ?, ?)", (now, now))
        execute(conn, "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES ('ct_2', 'org_2', '+525500000002', 'Sofía Test', 'sofia@example.com', '[]', ?, ?)", (now, now))
        execute(conn, "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES ('ct_3', 'org_1', '+525500000003', 'Luis Test', 'luis@example.com', '[]', ?, ?)", (now, now))
        execute(conn, "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES ('conv_1', 'org_1', 'bot_1', 'ct_1', 'ai_active', 0, 1, NULL, NULL, ?, NULL, ?, NULL, ?, ?)", (now, now, now, now))
        execute(conn, "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES ('conv_2', 'org_2', 'bot_2', 'ct_2', 'ai_active', 0, 1, NULL, NULL, ?, NULL, ?, NULL, ?, ?)", (now, now, now, now))
        execute(conn, "INSERT INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, provider_payload_json, reminder_scheduled_at, created_at, updated_at, payment_status, reconciliation_status) VALUES ('apt_org1', 'org_1', 'bot_1', 'conv_1', 'ct_1', '2026-04-15T16:00:00Z', 'pending', 30, 'America/Mexico_City', 'Demo comercial', '{}', ?, ?, ?, 'pending', 'pending')", (now, now, now))
        execute(conn, "INSERT INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, provider_payload_json, reminder_scheduled_at, created_at, updated_at, payment_status, reconciliation_status) VALUES ('apt_org2', 'org_2', 'bot_2', 'conv_2', 'ct_2', '2026-04-16T18:00:00Z', 'confirmed', 30, 'America/Mexico_City', 'Seguimiento premium', '{}', ?, ?, ?, 'paid', 'paid')", (now, now, now))
        execute(conn, "INSERT INTO crm_leads (id, organization_id, bot_id, contact_id, conversation_id, stage, estimated_amount, owner_user_id, next_action, followup_at, tags_json, notes, lost_reason, language, source_channel, source_campaign, pipeline_json, detected_objections_json, created_at, updated_at) VALUES ('lead_1', 'org_1', 'bot_1', 'ct_1', 'conv_1', 'nuevo', 999, 'usr_owner', 'Llamar hoy', NULL, '[]', '', NULL, 'es', 'whatsapp', 'organico', '{}', '[]', ?, ?)", (now, now))
        execute(conn, "INSERT INTO reactivation_recommendations (id, organization_id, bot_id, contact_id, crm_lead_id, segment, priority, suggested_channel, suggested_message, suggested_incentive, suggested_send_at, rationale, status, created_at, updated_at) VALUES ('rea_1', 'org_1', 'bot_1', 'ct_1', 'lead_1', 'warm', 90, 'whatsapp', 'Retoma seguimiento', '10% off', ?, 'Lead tibio', 'open', ?, ?)", (now, now, now))
        execute(conn, "INSERT INTO customer_feedback (id, organization_id, bot_id, conversation_id, contact_id, score_type, score_value, reason, detractor_alert, recovery_status, agent_user_id, created_at) VALUES ('fb_1', 'org_1', 'bot_1', 'conv_1', 'ct_1', 'nps', 9, 'Todo claro en portal', 0, 'not_needed', 'usr_owner', ?)", (now,))
        execute(conn, "INSERT INTO service_requests (id, organization_id, bot_id, contact_id, request_type, status, payload_json, response_json, created_at, updated_at) VALUES ('req_1', 'org_1', 'bot_1', 'ct_1', 'support_case', 'open', ?, '{}', ?, ?)", (to_json({'detail': 'Actualizar copy de bienvenida', 'message': 'Actualizar copy de bienvenida'}), now, now))
        execute(conn, "INSERT INTO executive_reports (id, organization_id, bot_id, period_start, period_end, report_type, summary_json, delivery_channels_json, pdf_path, pdf_filename, pdf_generated_at, updated_at, generated_at, created_at) VALUES ('rep_existing', 'org_1', 'bot_1', '2026-04-01', '2026-04-07', 'executive', '{}', '[\"pdf\"]', NULL, NULL, NULL, ?, ?, ?)", (now, now, now))
        execute(conn, "INSERT INTO sso_providers (id, organization_id, provider, issuer, client_id, status, scopes_json, metadata_json, last_test_at, created_at, updated_at) VALUES ('sso_1', 'org_1', 'okta', 'https://sso.enterprise.test', 'client_123', 'active', '[\"openid\",\"profile\",\"email\"]', ?, NULL, ?, ?)", (to_json({'allowed_domains': ['enterprise.test'], 'domain_hint': 'enterprise.test', 'display_name': 'SSO Enterprise'}), now, now))
        enrolled = enroll_mfa_factor(conn, user_id='usr_mfa')
        secret = enrolled.get('provisioning_uri', '').split('secret=', 1)[1].split('&', 1)[0]
        code = current_mfa_code(secret)
        activate_mfa_factor(conn, user_id='usr_mfa', code=code)
        execute(conn, "INSERT INTO audit_logs (id, organization_id, actor_user_id, actor_type, entity_type, entity_id, action, metadata_json, severity, created_at, request_id, session_id, ip_address, user_agent, trace_id) VALUES ('aud_1', 'org_1', 'usr_owner', 'user', 'bot', 'bot_1', 'seed.ready', '{}', 'info', ?, NULL, NULL, NULL, NULL, NULL)", (now,))
        conn.commit()
        (ROOT / 'frontend' / 'tests' / 'e2e' / '.real-secrets.json').write_text(json.dumps({'mfa_user_email': 'mfa@waos.test', 'mfa_user_password': 'Passw0rd!', 'mfa_user_secret': secret, 'owner_email': 'owner@waos.test', 'owner_password': 'Passw0rd!', 'client_email': 'client@waos.test', 'client_password': 'Passw0rd!'}, indent=2), encoding='utf-8')

def main() -> None:
    reset_db(); seed(); import uvicorn; uvicorn.run('backend.app.main:app', host='127.0.0.1', port=API_PORT, reload=False, log_level='warning')
if __name__ == '__main__':
    main()
