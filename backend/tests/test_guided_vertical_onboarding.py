from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_all, fetch_one, get_connection
from backend.app.main import app
from backend.tests.test_activation_foundations import _auth_headers
from backend.app.utils import from_json, utcnow_iso, to_json


client = TestClient(app)
ORG_ID = "org_guided_onboarding"
BOT_ID = "bot_guided_onboarding"
USER_ID = "usr_activation"


def _seed_guided_onboarding_scope() -> None:
    _auth_headers()
    now = utcnow_iso()
    with get_connection() as conn:
        if not fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (ORG_ID,)):
            execute(
                conn,
                "INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, tenant_mode, created_at, updated_at) VALUES (?, ?, ?, 'active', 'America/Mexico_City', NULL, '{}', 'sandbox', ?, ?)",
                (ORG_ID, "Clinica Wizard", "clinica-wizard", now, now),
            )
        if not fetch_one(conn, "SELECT * FROM organization_members WHERE organization_id = ? AND user_id = ?", (ORG_ID, USER_ID)):
            execute(
                conn,
                "INSERT INTO organization_members (id, organization_id, user_id, role, is_active, created_at) VALUES (?, ?, ?, 'org_admin', 1, ?)",
                ("mem_guided_onboarding", ORG_ID, USER_ID, now),
            )
        if not fetch_one(conn, "SELECT * FROM bots WHERE id = ?", (BOT_ID,)):
            execute(
                conn,
                "INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, published_version_id, config_draft_json, created_at, updated_at, deleted_at) VALUES (?, ?, ?, ?, NULL, 'es', 'America/Mexico_City', 'active', 0, 'draft', NULL, '{}', ?, ?, NULL)",
                (BOT_ID, ORG_ID, "Bot Wizard", "Clinica Wizard", now, now),
            )
        execute(conn, "DELETE FROM vertical_onboarding_step_runs WHERE organization_id = ?", (ORG_ID,))
        execute(conn, "DELETE FROM vertical_onboarding_wizards WHERE organization_id = ?", (ORG_ID,))
        execute(conn, "DELETE FROM bot_response_templates WHERE organization_id = ? AND bot_id = ? AND template_key LIKE 'guided-%'", (ORG_ID, BOT_ID))
        execute(conn, "DELETE FROM catalog_services WHERE organization_id = ? AND bot_id = ? AND name IN ('Valoracion guiada premium', 'Alineadores invisibles wizard')", (ORG_ID, BOT_ID))
        docs = fetch_all(conn, "SELECT id FROM knowledge_documents WHERE organization_id = ? AND bot_id = ? AND source_key LIKE 'guided-onboarding:%'", (ORG_ID, BOT_ID))
        for item in docs:
            execute(conn, "DELETE FROM knowledge_document_versions WHERE document_id = ?", (item["id"],))
            execute(conn, "DELETE FROM knowledge_documents WHERE id = ?", (item["id"],))
        execute(conn, "DELETE FROM integration_connections WHERE organization_id = ? AND bot_id = ? AND status = 'planned'", (ORG_ID, BOT_ID))
        conn.commit()


def test_guided_vertical_onboarding_wizard_builds_and_applies_vertical_pack() -> None:
    _seed_guided_onboarding_scope()
    headers = {**_auth_headers(), "x-organization-id": ORG_ID}

    verticals = client.get("/api/v1/onboarding/wizard/verticals", headers=headers)
    assert verticals.status_code == 200
    assert any(item["id"] == "dental" for item in verticals.json()["data"]["items"])

    blueprint = client.get(
        "/api/v1/onboarding/wizard/blueprint",
        headers=headers,
        params={
            "organization_id": ORG_ID,
            "bot_id": BOT_ID,
            "vertical_id": "dental",
            "subvertical": "ortodoncia",
            "primary_objective": "cerrar_tratamiento",
        },
    )
    assert blueprint.status_code == 200
    blueprint_data = blueprint.json()["data"]
    assert blueprint_data["profile"]["id"] == "dental"
    assert blueprint_data["selected_subvertical"]["name"] == "ortodoncia"
    assert any(item["provider"] == "google_calendar" for item in blueprint_data["setup"]["wizard"]["recommended_integrations"])

    started = client.post(
        "/api/v1/onboarding/wizard/start",
        headers=headers,
        json={
            "organization_id": ORG_ID,
            "bot_id": BOT_ID,
            "vertical_id": "dental",
            "subvertical": "ortodoncia",
            "business_name": "Clinica Sonrisa Pro",
            "bot_name": "Bot Sonrisa Pro",
            "primary_objective": "cerrar_tratamiento",
            "hours": "Lun-Vie 10:00-19:00",
            "whatsapp_number": "+5215551230000",
        },
    )
    assert started.status_code == 200
    wizard = started.json()["data"]
    wizard_id = wizard["id"]
    assert wizard["vertical_id"] == "dental"

    catalog = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/catalog_offer",
        headers=headers,
        json={
            "payload": {
                "services": ["Valoracion guiada premium", "Alineadores invisibles wizard"],
                "featured_offers": ["Diagnostico digital incluido"],
                "primary_ctas": [{"key": "assessment", "label": "Agendar valoracion", "goal": "assessment"}],
                "pricing_notes": ["anticipo desde 1500 MXN"],
            }
        },
    )
    assert catalog.status_code == 200

    knowledge = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/knowledge_seed",
        headers=headers,
        json={
            "payload": {
                "faqs": [
                    {"q": "¿Aceptan pagos en fases?", "a": "Si, podemos explicarte fases, anticipo y siguientes pagos."},
                    {"q": "¿Cuanto dura la valoracion?", "a": "La valoracion dura aprox 45 minutos con diagnostico inicial."},
                ],
                "policies": ["No prometer diagnostico sin valoracion.", "Escalar dolor intenso o urgencia a humano."],
                "knowledge_sources": [
                    {"connector_key": "drive", "required": True, "label": "Drive operativa", "publish_policy": "auto_publish"},
                    {"connector_key": "url", "required": True, "label": "Sitio dental", "publish_policy": "auto_publish"},
                    {"connector_key": "pdf", "required": False, "label": "Consentimientos PDF", "publish_policy": "manual_review"},
                ],
            }
        },
    )
    assert knowledge.status_code == 200

    integrations = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/integrations_rules",
        headers=headers,
        json={
            "payload": {
                "selected_integrations": [
                    {"integration_key": "whatsapp", "integration_type": "whatsapp", "provider": "meta_cloud_api", "name": "WhatsApp Cloud API", "status": "planned", "required": True},
                    {"integration_key": "google_calendar", "integration_type": "calendar", "provider": "google_calendar", "name": "Google Calendar", "status": "planned", "required": True},
                    {"integration_key": "payments", "integration_type": "payments", "provider": "stripe", "name": "Stripe", "status": "planned", "required": True},
                    {"integration_key": "crm", "integration_type": "crm", "provider": "waos_crm", "name": "WAOS CRM", "status": "planned", "required": True},
                    {"integration_key": "drive", "integration_type": "knowledge", "provider": "google_drive", "name": "Google Drive", "status": "planned", "required": True},
                ],
                "escalate_when": ["urgencia", "dolor intenso", "reclamo"],
                "handoff_keywords": ["urgencia", "doctor", "asesor"],
                "rule_overrides": {"can_say": ["planes", "fases", "anticipo"], "cannot_say": ["diagnostico definitivo"]},
            }
        },
    )
    assert integrations.status_code == 200

    dry_run = client.post(f"/api/v1/onboarding/wizard/{wizard_id}/dry-run", headers=headers)
    assert dry_run.status_code == 200
    dry_run_data = dry_run.json()["data"]
    assert dry_run_data["summary"]["apply_ready"] is True
    assert dry_run_data["summary"]["snapshot_required"] is True
    assert dry_run_data["exit_score"]["value"] >= 60
    assert any(item["label"] == "Vertical" for item in dry_run_data["diff_summary"])

    applied = client.post(f"/api/v1/onboarding/wizard/{wizard_id}/apply", headers=headers)
    assert applied.status_code == 200
    applied_data = applied.json()["data"]
    assert applied_data["summary"]["template_count"] >= 1
    assert "Valoracion guiada premium" in applied_data["summary"]["created_services"]
    assert applied_data["pack_result"]["subvertical"] == "ortodoncia"

    summary = client.get(
        "/api/v1/onboarding/summary",
        headers=headers,
        params={"organization_id": ORG_ID, "bot_id": BOT_ID},
    )
    assert summary.status_code == 200
    assert summary.json()["data"]["guided_wizard"]["id"] == wizard_id
    assert summary.json()["data"]["guided_wizard"]["status"] == "applied"

    with get_connection() as conn:
        wizard_row = fetch_one(conn, "SELECT * FROM vertical_onboarding_wizards WHERE id = ?", (wizard_id,))
        assert wizard_row["status"] == "applied"

        bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ?", (BOT_ID,))
        assert bot["vertical"] == "dental"
        config = from_json(bot["config_draft_json"], {})
        assert config["guided_onboarding"]["wizard_id"] == wizard_id
        assert config["selected_subvertical"] == "ortodoncia"

        org = fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (ORG_ID,))
        settings = from_json(org["settings_json"], {})
        assert settings["guided_onboarding"]["wizard_id"] == wizard_id
        assert settings["active_subvertical"] == "ortodoncia"

        behavior = fetch_one(conn, "SELECT * FROM bot_behavior_settings WHERE organization_id = ? AND bot_id = ?", (ORG_ID, BOT_ID))
        assert behavior is not None

        templates = fetch_all(conn, "SELECT * FROM bot_response_templates WHERE organization_id = ? AND bot_id = ? AND template_key LIKE 'guided-%'", (ORG_ID, BOT_ID))
        assert len(templates) >= 1

        services = fetch_all(conn, "SELECT * FROM catalog_services WHERE organization_id = ? AND bot_id = ?", (ORG_ID, BOT_ID))
        assert any(item["name"] == "Valoracion guiada premium" for item in services)

        knowledge_docs = fetch_all(conn, "SELECT * FROM knowledge_documents WHERE organization_id = ? AND bot_id = ? AND source_key LIKE 'guided-onboarding:%'", (ORG_ID, BOT_ID))
        assert len(knowledge_docs) >= 2

        planned_integrations = fetch_all(conn, "SELECT * FROM integration_connections WHERE organization_id = ? AND bot_id = ? AND status = 'planned'", (ORG_ID, BOT_ID))
        assert any(item["provider"] == "google_calendar" for item in planned_integrations)
        assert any(item["provider"] == "google_drive" for item in planned_integrations)


def test_guided_vertical_onboarding_requires_fresh_dry_run_before_reconfigure_apply() -> None:
    _seed_guided_onboarding_scope()
    headers = {**_auth_headers(), "x-organization-id": ORG_ID}

    started = client.post(
        "/api/v1/onboarding/wizard/start",
        headers=headers,
        json={
            "organization_id": ORG_ID,
            "bot_id": BOT_ID,
            "vertical_id": "dental",
            "subvertical": "ortodoncia",
            "business_name": "Clinica Sonrisa Pro",
            "bot_name": "Bot Sonrisa Pro",
            "primary_objective": "cerrar_tratamiento",
        },
    )
    assert started.status_code == 200
    wizard_id = started.json()["data"]["id"]

    integrations = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/integrations_rules",
        headers=headers,
        json={
            "payload": {
                "selected_integrations": [
                    {"integration_key": "whatsapp", "integration_type": "whatsapp", "provider": "meta_cloud_api", "name": "WhatsApp Cloud API", "status": "planned", "required": True},
                ],
                "escalate_when": ["urgencia"],
                "handoff_keywords": ["doctor"],
                "expected_handoff_sla": "20 minutos",
                "human_destination_channel": "Equipo humano",
            }
        },
    )
    assert integrations.status_code == 200

    dry_run = client.post(f"/api/v1/onboarding/wizard/{wizard_id}/dry-run", headers=headers)
    assert dry_run.status_code == 200
    assert dry_run.json()["data"]["summary"]["apply_ready"] is True

    mutate = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/knowledge_seed",
        headers=headers,
        json={"payload": {"faqs": [{"q": "¿Abren sabado?", "a": "Si"}] }},
    )
    assert mutate.status_code == 200

    applied = client.post(f"/api/v1/onboarding/wizard/{wizard_id}/apply", headers=headers)
    assert applied.status_code == 400
    assert applied.json()["detail"] == "dry_run_required"


def test_validation_snapshot_promotes_inbox_when_bot_is_already_live_and_ready() -> None:
    _seed_guided_onboarding_scope()
    headers = {**_auth_headers(), "x-organization-id": ORG_ID}

    started = client.post(
        "/api/v1/onboarding/wizard/start",
        headers=headers,
        json={
            "organization_id": ORG_ID,
            "bot_id": BOT_ID,
            "vertical_id": "dental",
            "subvertical": "ortodoncia",
            "business_name": "Clinica Sonrisa Pro",
            "bot_name": "Bot Sonrisa Pro",
            "primary_objective": "cerrar_tratamiento",
        },
    )
    assert started.status_code == 200
    wizard_id = started.json()["data"]["id"]

    client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/integrations_rules",
        headers=headers,
        json={
            "payload": {
                "selected_integrations": [
                    {"integration_key": "whatsapp", "integration_type": "whatsapp", "provider": "meta_cloud_api", "name": "WhatsApp Cloud API", "status": "planned", "required": True},
                ],
                "escalate_when": ["urgencia", "reclamo"],
                "handoff_keywords": ["doctor", "asesor"],
                "expected_handoff_sla": "20 minutos",
                "human_destination_channel": "Equipo humano / operaciones",
            }
        },
    )
    dry_run = client.post(f"/api/v1/onboarding/wizard/{wizard_id}/dry-run", headers=headers)
    assert dry_run.status_code == 200

    now = utcnow_iso()
    with get_connection() as conn:
        execute(conn, "UPDATE bots SET status = 'published', current_state = 'published', published_version_id = 'ver_live', config_draft_json = json_set(COALESCE(config_draft_json, '{}'), '$.primary_channel', 'whatsapp') WHERE id = ?", (BOT_ID,))
        execute(
            conn,
            "INSERT INTO integration_connections (id, organization_id, bot_id, integration_type, provider, name, status, health_status, credential_status, config_json, created_at, updated_at) VALUES (?, ?, ?, 'whatsapp', 'meta_cloud_api', 'WhatsApp Cloud API', 'active', 'healthy', 'connected', '{}', ?, ?)",
            ("int_guided_live", ORG_ID, BOT_ID, now, now),
        )
        execute(
            conn,
            "INSERT INTO bot_simulation_runs (id, organization_id, bot_id, compare_target, left_version_id, right_version_id, status, summary_json, cases_total, passed_count, failed_count, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("sim_guided_live", ORG_ID, BOT_ID, 'published', 'ver_live', 'ver_live', 'completed', to_json({"pass_rate": 92, "cases_total": 5}), 5, 5, 0, USER_ID, now),
        )
        conn.commit()

    refreshed = client.get(f"/api/v1/onboarding/wizard/{wizard_id}", headers=headers)
    assert refreshed.status_code == 200
    snapshot = refreshed.json()["data"]["validation_snapshot"]
    assert snapshot["next_cta"]["key"] == "open_inbox"
    assert snapshot["next_cta"]["cta_label"] == "Abrir inbox"
    assert snapshot["simulation_result"]["approved"] is True
