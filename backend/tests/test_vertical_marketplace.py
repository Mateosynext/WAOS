from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_all, fetch_one, get_connection
from backend.app.main import app
from backend.app.utils import from_json, utcnow_iso
from backend.tests.test_activation_foundations import _auth_headers

client = TestClient(app)
ORG_ID = "org_vertical_marketplace"
BOT_ID = "bot_vertical_marketplace"
USER_ID = "usr_activation"


def _seed_marketplace_scope() -> None:
    _auth_headers(ORG_ID)
    now = utcnow_iso()
    with get_connection() as conn:
        if not fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (ORG_ID,)):
            execute(conn, "INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, tenant_mode, created_at, updated_at) VALUES (?, ?, ?, 'active', 'America/Mexico_City', 'esthetic', '{}', 'sandbox', ?, ?)", (ORG_ID, 'Aesthetic Org', 'aesthetic-org', now, now))
        if not fetch_one(conn, "SELECT * FROM organization_members WHERE organization_id = ? AND user_id = ?", (ORG_ID, USER_ID)):
            execute(conn, "INSERT INTO organization_members (id, organization_id, user_id, role, is_active, created_at) VALUES (?, ?, ?, 'org_admin', 1, ?)", ('mem_vertical_marketplace', ORG_ID, USER_ID, now))
        if not fetch_one(conn, "SELECT * FROM bots WHERE id = ?", (BOT_ID,)):
            execute(conn, "INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, published_version_id, config_draft_json, created_at, updated_at, deleted_at) VALUES (?, ?, ?, ?, 'esthetic', 'es', 'America/Mexico_City', 'active', 0, 'draft', NULL, '{}', ?, ?, NULL)", (BOT_ID, ORG_ID, 'Bot Marketplace', 'Aesthetic Org', now, now))
        execute(conn, "DELETE FROM vertical_marketplace_install_items WHERE organization_id = ?", (ORG_ID,))
        execute(conn, "DELETE FROM vertical_marketplace_upgrade_runs WHERE organization_id = ?", (ORG_ID,))
        execute(conn, "DELETE FROM vertical_marketplace_installs WHERE organization_id = ?", (ORG_ID,))
        execute(conn, "DELETE FROM vertical_marketplace_package_versions WHERE package_id IN (SELECT id FROM vertical_marketplace_packages WHERE package_slug = 'esthetic-premium-pack')")
        execute(conn, "DELETE FROM vertical_marketplace_packages WHERE package_slug = 'esthetic-premium-pack'")
        execute(conn, "DELETE FROM bot_response_templates WHERE organization_id = ? AND bot_id = ? AND template_key LIKE 'marketplace-%'", (ORG_ID, BOT_ID))
        docs = fetch_all(conn, "SELECT id FROM knowledge_documents WHERE organization_id = ? AND bot_id = ? AND source_key LIKE 'marketplace:esthetic-premium-pack:%'", (ORG_ID, BOT_ID))
        for item in docs:
            execute(conn, "DELETE FROM knowledge_document_versions WHERE document_id = ?", (item['id'],))
            execute(conn, "DELETE FROM knowledge_documents WHERE id = ?", (item['id'],))
        execute(conn, "DELETE FROM catalog_services WHERE organization_id = ? AND bot_id = ? AND name IN ('Evaluacion glow premium', 'Membresia post-tratamiento')", (ORG_ID, BOT_ID))
        execute(conn, "DELETE FROM automation_rules WHERE organization_id = ? AND bot_id = ? AND name LIKE 'Marketplace %'", (ORG_ID, BOT_ID))
        execute(conn, "DELETE FROM industry_playbooks WHERE organization_id = ? AND name LIKE 'Marketplace %'", (ORG_ID,))
        execute(conn, "DELETE FROM integration_connections WHERE organization_id = ? AND bot_id = ? AND provider IN ('google_drive','stripe')", (ORG_ID, BOT_ID))
        conn.commit()


def test_vertical_marketplace_publish_install_and_upgrade() -> None:
    _seed_marketplace_scope()
    headers = {**_auth_headers(ORG_ID), 'x-organization-id': ORG_ID}

    publish = client.post(
        '/api/v1/vertical-marketplace/packages',
        headers=headers,
        json={
            'package_type': 'vertical',
            'package_slug': 'esthetic-premium-pack',
            'title': 'Esthetic Premium Pack',
            'summary': 'Pack instalable para clinicas esteticas con onboarding, prompts y automatizaciones.',
            'version': '1.0.0',
            'vertical_key': 'esthetic',
            'subvertical': 'facial',
            'compatibility': {'min_runtime': 'v13', 'channels': ['whatsapp', 'voice'], 'requires_bot': True},
            'checklist': ['conectar agenda', 'subir protocolos', 'definir CTA principal'],
            'metrics_expected': {'ttfv_hours': 6, 'show_rate_target': 0.72},
            'monetization_model': 'paid_install',
            'price_amount': 399,
            'currency': 'USD',
            'release_notes': 'Version inicial del pack estético.',
            'manifest': {
                'behavior': {'tone': 'premium_calido', 'response_length': 'media', 'sales_intensity': 'media_alta', 'escalate_when': ['urgencia', 'queja'], 'required_phrases': ['te explico el siguiente paso claro']},
                'templates': [
                    {'template_key': 'marketplace-welcome', 'title': 'Bienvenida premium', 'content': 'Hola, te acompaño a elegir el mejor siguiente paso para tu tratamiento.', 'variables': ['first_name']}
                ],
                'knowledge_documents': [
                    {'title': 'FAQ tratamientos faciales', 'source_key': 'marketplace:esthetic-premium-pack:faq-facial', 'source_kind': 'import', 'domain': 'support', 'content_text': 'Incluye respuestas sobre sesiones, recuperacion, contraindicaciones y tiempos.', 'supports': ['faq', 'support']}
                ],
                'catalog_services': [
                    {'name': 'Evaluacion glow premium', 'duration_minutes': 45, 'price': 1200, 'currency': 'MXN'}
                ],
                'integrations': [
                    {'integration_type': 'knowledge', 'provider': 'google_drive', 'name': 'Google Drive', 'status': 'planned', 'config': {'folder': 'esthetic-premium'}},
                    {'integration_type': 'payments', 'provider': 'stripe', 'name': 'Stripe', 'status': 'planned', 'config': {'mode': 'payment_links'}}
                ],
                'playbooks': [
                    {'name': 'Marketplace reactivacion estetica', 'status': 'active', 'config': {'goal': 'recover_leads', 'window_days': 14}}
                ],
                'automations': [
                    {'name': 'Marketplace post evaluacion', 'rule_type': 'followup', 'status': 'active', 'config': {'delay_minutes': 30, 'objective': 'close_assessment'}}
                ],
            },
        },
    )
    assert publish.status_code == 200
    package = publish.json()['data']
    assert package['package_slug'] == 'esthetic-premium-pack'
    assert package['latest_version']['version'] == '1.0.0'

    listed = client.get('/api/v1/vertical-marketplace/packages', headers=headers, params={'vertical_key': 'esthetic'})
    assert listed.status_code == 200
    assert any(item['package_slug'] == 'esthetic-premium-pack' for item in listed.json()['data']['items'])

    install = client.post(
        '/api/v1/vertical-marketplace/install',
        headers=headers,
        json={'organization_id': ORG_ID, 'bot_id': BOT_ID, 'package_slug': 'esthetic-premium-pack', 'install_scope': 'bot'},
    )
    assert install.status_code == 200
    install_data = install.json()['data']
    install_id = install_data['id']
    assert install_data['current_version'] == '1.0.0'
    assert install_data['install_summary']['templates'] >= 1
    assert install_data['install_summary']['knowledge_documents'] >= 1

    installs = client.get('/api/v1/vertical-marketplace/installs', headers=headers, params={'organization_id': ORG_ID, 'bot_id': BOT_ID})
    assert installs.status_code == 200
    assert installs.json()['data']['count'] == 1

    with get_connection() as conn:
        tmpl = fetch_one(conn, "SELECT * FROM bot_response_templates WHERE organization_id = ? AND bot_id = ? AND template_key = 'marketplace-welcome'", (ORG_ID, BOT_ID))
        assert tmpl is not None
        doc = fetch_one(conn, "SELECT * FROM knowledge_documents WHERE organization_id = ? AND bot_id = ? AND source_key = 'marketplace:esthetic-premium-pack:faq-facial'", (ORG_ID, BOT_ID))
        assert doc is not None
        svc = fetch_one(conn, "SELECT * FROM catalog_services WHERE organization_id = ? AND bot_id = ? AND name = 'Evaluacion glow premium'", (ORG_ID, BOT_ID))
        assert svc is not None
        auto = fetch_one(conn, "SELECT * FROM automation_rules WHERE organization_id = ? AND bot_id = ? AND name = 'Marketplace post evaluacion'", (ORG_ID, BOT_ID))
        assert auto is not None
        playbook = fetch_one(conn, "SELECT * FROM industry_playbooks WHERE organization_id = ? AND name = 'Marketplace reactivacion estetica'", (ORG_ID,))
        assert playbook is not None
        settings = from_json(fetch_one(conn, 'SELECT settings_json FROM organizations WHERE id = ?', (ORG_ID,))['settings_json'], {})
        assert settings['vertical_marketplace']['last_install']['package_slug'] == 'esthetic-premium-pack'
        bot_config = from_json(fetch_one(conn, 'SELECT config_draft_json FROM bots WHERE id = ?', (BOT_ID,))['config_draft_json'], {})
        assert bot_config['vertical_marketplace']['last_install']['current_version'] == '1.0.0'
        items = fetch_all(conn, 'SELECT * FROM vertical_marketplace_install_items WHERE install_id = ?', (install_id,))
        assert len(items) >= 5

    publish_v2 = client.post(
        '/api/v1/vertical-marketplace/packages',
        headers=headers,
        json={
            'package_type': 'vertical',
            'package_slug': 'esthetic-premium-pack',
            'title': 'Esthetic Premium Pack',
            'summary': 'Pack instalable para clinicas esteticas con onboarding, prompts y automatizaciones.',
            'version': '1.1.0',
            'vertical_key': 'esthetic',
            'subvertical': 'facial',
            'release_notes': 'Agrega membresia y nuevo CTA.',
            'manifest': {
                'templates': [
                    {'template_key': 'marketplace-welcome', 'title': 'Bienvenida premium', 'content': 'Hola, te acompaño a elegir el mejor siguiente paso para tu tratamiento.', 'variables': ['first_name']},
                    {'template_key': 'marketplace-membership', 'title': 'Membresia', 'content': 'Tambien te puedo explicar la membresia post-tratamiento.', 'variables': []}
                ],
                'catalog_services': [
                    {'name': 'Evaluacion glow premium', 'duration_minutes': 45, 'price': 1200, 'currency': 'MXN'},
                    {'name': 'Membresia post-tratamiento', 'duration_minutes': 20, 'price': 799, 'currency': 'MXN'}
                ],
            },
        },
    )
    assert publish_v2.status_code == 200
    assert publish_v2.json()['data']['latest_version']['version'] == '1.1.0'

    upgrade = client.post(
        f'/api/v1/vertical-marketplace/installs/{install_id}/upgrade',
        headers=headers,
        json={'organization_id': ORG_ID},
    )
    assert upgrade.status_code == 200
    upgraded = upgrade.json()['data']
    assert upgraded['current_version'] == '1.1.0'
    assert upgraded['upgrade_run']['status'] == 'completed'

    with get_connection() as conn:
        install_row = fetch_one(conn, 'SELECT * FROM vertical_marketplace_installs WHERE id = ?', (install_id,))
        assert install_row['current_version'] == '1.1.0'
        assert int(install_row['upgrade_available']) == 0
        svc2 = fetch_one(conn, "SELECT * FROM catalog_services WHERE organization_id = ? AND bot_id = ? AND name = 'Membresia post-tratamiento'", (ORG_ID, BOT_ID))
        assert svc2 is not None
        tmpl2 = fetch_one(conn, "SELECT * FROM bot_response_templates WHERE organization_id = ? AND bot_id = ? AND template_key = 'marketplace-membership'", (ORG_ID, BOT_ID))
        assert tmpl2 is not None
        upgrades = fetch_all(conn, 'SELECT * FROM vertical_marketplace_upgrade_runs WHERE install_id = ? ORDER BY created_at DESC', (install_id,))
        assert len(upgrades) >= 1
