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
        execute(conn, "DELETE FROM vertical_onboarding_wizard_events WHERE organization_id = ?", (ORG_ID,))
        execute(conn, "DELETE FROM vertical_onboarding_step_runs WHERE organization_id = ?", (ORG_ID,))
        execute(conn, "DELETE FROM vertical_onboarding_wizards WHERE organization_id = ?", (ORG_ID,))
        execute(conn, "DELETE FROM bot_response_templates WHERE organization_id = ? AND bot_id = ? AND template_key LIKE 'guided-%'", (ORG_ID, BOT_ID))
        execute(conn, "DELETE FROM catalog_services WHERE organization_id = ? AND bot_id = ? AND name IN ('Valoracion guiada premium', 'Alineadores invisibles wizard')", (ORG_ID, BOT_ID))
        docs = fetch_all(conn, "SELECT id FROM knowledge_documents WHERE organization_id = ? AND bot_id = ? AND source_key LIKE 'guided-onboarding:%'", (ORG_ID, BOT_ID))
        for item in docs:
            execute(conn, "DELETE FROM knowledge_document_versions WHERE document_id = ?", (item["id"],))
            execute(conn, "DELETE FROM knowledge_documents WHERE id = ?", (item["id"],))
        execute(conn, "DELETE FROM bot_simulation_runs WHERE organization_id = ? AND bot_id = ?", (ORG_ID, BOT_ID))
        execute(conn, "DELETE FROM release_requests WHERE organization_id = ? AND bot_id = ?", (ORG_ID, BOT_ID))
        execute(conn, "DELETE FROM bot_versions WHERE organization_id = ? AND bot_id = ?", (ORG_ID, BOT_ID))
        execute(conn, "DELETE FROM integration_connections WHERE organization_id = ? AND bot_id = ?", (ORG_ID, BOT_ID))
        execute(conn, "UPDATE bots SET published_version_id = NULL, current_state = 'draft', status = 'active', config_draft_json = '{}' WHERE id = ?", (BOT_ID,))
        conn.commit()


def _complete_business_basics(headers: dict[str, str], wizard_id: str, *, business_name: str, bot_name: str, tone: str = "amable") -> None:
    saved = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/business_basics",
        headers=headers,
        json={
            "payload": {
                "business_name": business_name,
                "bot_name": bot_name,
                "tone": tone,
                "language": "es",
                "timezone": "America/Mexico_City",
            }
        },
    )
    assert saved.status_code == 200



def _complete_catalog_offer(headers: dict[str, str], wizard_id: str) -> None:
    saved = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/catalog_offer",
        headers=headers,
        json={
            "payload": {
                "services": ["Valoracion guiada premium", "Alineadores invisibles wizard"],
                "primary_ctas": [{"key": "assessment", "label": "Agendar valoracion", "goal": "assessment"}],
            }
        },
    )
    assert saved.status_code == 200



def _complete_knowledge_seed(headers: dict[str, str], wizard_id: str) -> None:
    saved = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/knowledge_seed",
        headers=headers,
        json={
            "payload": {
                "faqs": [{"q": "¿Abren sabado?", "a": "Si"}],
                "policies": ["No prometer diagnostico sin valoracion."],
                "knowledge_sources": [{"connector_key": "drive", "required": True, "label": "Drive operativa", "publish_policy": "auto_publish"}],
            }
        },
    )
    assert saved.status_code == 200



def _complete_until_integrations(headers: dict[str, str], wizard_id: str, *, business_name: str, bot_name: str, tone: str = "amable") -> None:
    _complete_business_basics(headers, wizard_id, business_name=business_name, bot_name=bot_name, tone=tone)
    _complete_catalog_offer(headers, wizard_id)
    _complete_knowledge_seed(headers, wizard_id)


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
    assert any(item["event_type"] == "wizard.started" for item in wizard.get("event_log") or [])

    _complete_business_basics(headers, wizard_id, business_name="Clinica Sonrisa Pro", bot_name="Bot Sonrisa Pro")

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
    assert any(item["event_type"] == "wizard.dry_run_completed" for item in dry_run_data["wizard"].get("event_log") or [])

    applied = client.post(f"/api/v1/onboarding/wizard/{wizard_id}/apply", headers=headers)
    assert applied.status_code == 200
    applied_data = applied.json()["data"]
    assert applied_data["summary"]["template_count"] >= 1
    assert "Valoracion guiada premium" in applied_data["summary"]["created_services"]
    assert applied_data["pack_result"]["subvertical"] == "ortodoncia"
    assert any(item["event_type"] == "wizard.applied" for item in applied_data["wizard"].get("event_log") or [])

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

    _complete_until_integrations(headers, wizard_id, business_name="Clinica Sonrisa Pro", bot_name="Bot Sonrisa Pro")

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

    _complete_until_integrations(headers, wizard_id, business_name="Clinica Sonrisa Pro", bot_name="Bot Sonrisa Pro")

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
        execute(conn, "INSERT INTO bot_versions (id, organization_id, bot_id, version_number, status, config_json, created_by, notes, created_at) VALUES (?, ?, ?, ?, 'published', '{}', ?, '', ?)", ("ver_live", ORG_ID, BOT_ID, 1, USER_ID, now))
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


def test_guided_vertical_onboarding_rejects_stale_revision_on_step_save() -> None:
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
    wizard = started.json()["data"]
    wizard_id = wizard["id"]
    revision = wizard["wizard_revision"]

    _complete_business_basics(headers, wizard_id, business_name="Clinica Sonrisa Pro", bot_name="Bot Sonrisa Pro")
    _complete_catalog_offer(headers, wizard_id)
    wizard = client.get(f"/api/v1/onboarding/wizard/{wizard_id}", headers=headers).json()["data"]
    revision = wizard["wizard_revision"]

    ok_save = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/knowledge_seed",
        headers=headers,
        json={"payload": {"faqs": [{"q": "Uno", "a": "Dos"}]}, "expected_revision": revision},
    )
    assert ok_save.status_code == 200

    stale_save = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/knowledge_seed",
        headers=headers,
        json={"payload": {"faqs": [{"q": "Tres", "a": "Cuatro"}]}, "expected_revision": revision},
    )
    assert stale_save.status_code == 409
    assert stale_save.json()["detail"] == "wizard_revision_conflict"



def test_guided_onboarding_step_rejects_stale_consecutive_revision_updates() -> None:
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
            "business_name": "Clinica Revision",
            "bot_name": "Bot Revision",
            "primary_objective": "cerrar_tratamiento",
        },
    )
    assert started.status_code == 200
    wizard = started.json()["data"]
    revision = int(wizard["wizard_revision"])

    first = client.post(
        f"/api/v1/onboarding/wizard/{wizard['id']}/steps/business_basics",
        headers=headers,
        json={"payload": {"business_name": "Clinica Revision 1"}, "expected_revision": revision},
    )
    assert first.status_code == 200
    assert int(first.json()["data"]["wizard_revision"]) == revision + 1

    stale = client.post(
        f"/api/v1/onboarding/wizard/{wizard['id']}/steps/business_basics",
        headers=headers,
        json={"payload": {"business_name": "Clinica Revision 2"}, "expected_revision": revision},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"] == "wizard_revision_conflict"



def test_apply_guided_onboarding_wizard_without_existing_bot_creates_one() -> None:
    _seed_guided_onboarding_scope()
    headers = {**_auth_headers(), "x-organization-id": ORG_ID}
    started = client.post(
        "/api/v1/onboarding/wizard/start",
        headers=headers,
        json={
            "organization_id": ORG_ID,
            "vertical_id": "dental",
            "subvertical": "ortodoncia",
            "business_name": "Clinica Sin Bot",
            "bot_name": "Bot Nuevo",
            "primary_objective": "agendar",
            "hours": "Lun-Vie 09:00-18:00",
        },
    )
    assert started.status_code == 200
    wizard_id = started.json()["data"]["id"]

    applied = client.post(f"/api/v1/onboarding/wizard/{wizard_id}/apply", headers=headers)
    assert applied.status_code == 200
    payload = applied.json()["data"]
    assert payload["wizard"]["bot_id"]
    assert payload["summary"]["template_count"] >= 0



def test_guided_onboarding_import_graph_smoke() -> None:
    import backend.app.main as main_mod
    import backend.app.api.routers.onboarding as onboarding_router
    import backend.app.vertical_onboarding_runtime as runtime_mod

    assert main_mod.app is not None
    assert onboarding_router.router is not None
    assert callable(runtime_mod.update_guided_onboarding_step)
    assert callable(runtime_mod.apply_guided_onboarding_wizard)



def test_guided_onboarding_start_and_update_stay_under_local_budget() -> None:
    import time

    _seed_guided_onboarding_scope()
    headers = {**_auth_headers(), "x-organization-id": ORG_ID}

    started_at = time.perf_counter()
    started = client.post(
        "/api/v1/onboarding/wizard/start",
        headers=headers,
        json={
            "organization_id": ORG_ID,
            "bot_id": BOT_ID,
            "vertical_id": "dental",
            "subvertical": "ortodoncia",
            "business_name": "Clinica Budget",
            "bot_name": "Bot Budget",
            "primary_objective": "agendar",
        },
    )
    start_ms = (time.perf_counter() - started_at) * 1000
    assert started.status_code == 200
    assert start_ms < 5000

    wizard_id = started.json()["data"]["id"]
    revision = int(started.json()["data"]["wizard_revision"])
    updated_at = time.perf_counter()
    updated = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/business_basics",
        headers=headers,
        json={"payload": {"business_name": "Clinica Budget 2"}, "expected_revision": revision},
    )
    update_ms = (time.perf_counter() - updated_at) * 1000
    assert updated.status_code == 200
    assert update_ms < 5000


def test_guided_onboarding_required_fields_match_wizard_ui_contract() -> None:
    from backend.app.vertical_onboarding_runtime import _GUIDED_STEPS

    required_by_key = {item["key"]: item["fields"] for item in _GUIDED_STEPS}
    assert required_by_key["business_basics"] == ["business_name", "bot_name", "tone", "language", "timezone"]
    assert required_by_key["catalog_offer"] == ["services", "primary_ctas"]
    assert required_by_key["knowledge_seed"] == ["faqs", "policies", "knowledge_sources"]
    assert required_by_key["integrations_rules"] == ["selected_integrations", "escalate_when"]



def test_guided_onboarding_top_level_basics_prefill_do_not_auto_complete_business_basics() -> None:
    from backend.app.vertical_onboarding_runtime import build_guided_onboarding_blueprint

    blueprint = build_guided_onboarding_blueprint(
        vertical_id="dental",
        subvertical="Ortodoncia",
        business_name="Clínica Norte",
        bot_name="Asistente Norte",
        tone="amable",
        language="es",
        timezone="America/Mexico_City",
    )

    basics = next(step for step in blueprint["steps"] if step["key"] == "business_basics")
    assert basics["completed"] is False
    assert basics["status"] in {"pending", "in_progress"}
    assert basics["payload"] == {
        "business_name": "",
        "bot_name": "",
        "tone": "",
        "language": "",
        "timezone": "",
        "hours": "",
        "whatsapp_number": "",
    }
    assert blueprint["current_step"] == "business_basics"
    assert blueprint["prefill_answers"]["business_basics"]["business_name"] == "Clínica Norte"
    assert blueprint["prefill_answers"]["business_basics"]["bot_name"] == "Asistente Norte"


def test_guided_onboarding_whitespace_required_fields_do_not_complete_step() -> None:
    from backend.app.vertical_onboarding_runtime import build_guided_onboarding_blueprint

    blueprint = build_guided_onboarding_blueprint(
        vertical_id="dental",
        subvertical="Ortodoncia",
        business_name="Clínica Norte",
        bot_name="Asistente Norte",
        answers={
            "business_basics": {
                "business_name": "   ",
                "bot_name": "Asistente Norte",
                "tone": "amable",
                "language": "es",
                "timezone": "America/Mexico_City",
            }
        },
    )

    basics = next(step for step in blueprint["steps"] if step["key"] == "business_basics")
    assert basics["completed"] is False
    assert blueprint["current_step"] == "business_basics"



def test_guided_onboarding_event_log_tracks_start_and_step_save() -> None:
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
            "business_name": "Clinica Bitacora",
            "bot_name": "Bot Bitacora",
            "primary_objective": "agendar",
        },
    )
    assert started.status_code == 200
    wizard = started.json()["data"]
    wizard_id = wizard["id"]
    assert [item["event_type"] for item in wizard.get("event_log") or []] == ["wizard.started"]

    saved = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/business_basics",
        headers=headers,
        json={
            "payload": {
                "business_name": "Clinica Bitacora",
                "bot_name": "Bot Bitacora",
                "tone": "amable",
                "language": "es",
                "timezone": "America/Mexico_City",
            }
        },
    )
    assert saved.status_code == 200
    updated = saved.json()["data"]
    event_types = [item["event_type"] for item in updated.get("event_log") or []]
    assert "wizard.step_saved" in event_types
    saved_event = next(item for item in updated.get("event_log") or [] if item["event_type"] == "wizard.step_saved")
    assert saved_event["step_key"] == "business_basics"
    assert saved_event["payload"]["wizard_revision"] >= 2


def test_guided_onboarding_blueprint_normalizes_step_payload_shapes() -> None:
    from backend.app.vertical_onboarding_runtime import build_guided_onboarding_blueprint

    blueprint = build_guided_onboarding_blueprint(
        vertical_id="dental",
        subvertical="Ortodoncia",
        business_name="Clínica Norte",
        bot_name="Asistente Norte",
        answers={
            "catalog_offer": {
                "services": ["Valoración", " ", "Valoración"],
                "primary_ctas": ["Agendar valoración", {"label": "Hablar con asesor", "goal": "handoff"}],
            },
            "knowledge_seed": {
                "faqs": ["¿Precio? | Desde 500", {"q": "¿Horario?", "a": "Lunes a viernes"}],
                "policies": ["No spam", "", "No spam"],
                "knowledge_sources": ["Drive operativo", {"connector_key": "url", "label": "Sitio web"}],
            },
            "integrations_rules": {
                "selected_integrations": ["whatsapp", {"provider": "google_calendar", "name": "Google Calendar", "integration_key": "calendar"}],
                "escalate_when": ["urgencia", "", "urgencia"],
                "rule_overrides": "texto inválido",
            },
        },
    )

    answers = blueprint["answers"]
    assert answers["catalog_offer"]["services"] == ["Valoración"]
    assert len(answers["catalog_offer"]["primary_ctas"]) == 2
    assert answers["knowledge_seed"]["faqs"][0] == {"q": "¿Precio?", "a": "Desde 500"}
    assert answers["knowledge_seed"]["policies"] == ["No spam"]
    assert len(answers["knowledge_seed"]["knowledge_sources"]) == 2
    assert len(answers["integrations_rules"]["selected_integrations"]) == 2
    assert answers["integrations_rules"]["escalate_when"] == ["urgencia"]
    assert answers["integrations_rules"]["rule_overrides"] == {}


def test_guided_onboarding_rejects_out_of_sequence_step_updates() -> None:
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
            "business_name": "Clinica Secuencia",
            "bot_name": "Bot Secuencia",
            "primary_objective": "cerrar_tratamiento",
        },
    )
    assert started.status_code == 200
    wizard_id = started.json()["data"]["id"]

    with get_connection() as conn:
        execute(
            conn,
            "UPDATE vertical_onboarding_wizards SET answers_json = ?, current_step = ?, progress_percent = ? WHERE id = ?",
            (
                to_json({
                    "vertical_fit": {
                        "vertical_id": "dental",
                        "subvertical": "ortodoncia",
                        "primary_objective": "cerrar_tratamiento",
                    },
                    "business_basics": {
                        "business_name": "Clinica Secuencia",
                        "bot_name": "Bot Secuencia",
                        "tone": "cercano",
                        "language": "es",
                        "timezone": "America/Mexico_City",
                        "hours": "",
                        "whatsapp_number": "",
                    },
                    "catalog_offer": {},
                    "knowledge_seed": {},
                    "integrations_rules": {},
                    "launch_review": {},
                }),
                "catalog_offer",
                33,
                wizard_id,
            ),
        )
        conn.commit()

    blocked = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/launch_review",
        headers=headers,
        json={
            "payload": {
                "recommended_playbooks": [{"key": "launch", "label": "Launch", "priority": 1}],
                "launch_notes": ["No debería pasar todavía"],
                "autopublish_knowledge": True,
            }
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "wizard_step_out_of_sequence"



def test_guided_onboarding_duplicate_step_save_does_not_increment_revision() -> None:
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
            "business_name": "Clinica Dedupe",
            "bot_name": "Bot Dedupe",
            "primary_objective": "cerrar_tratamiento",
        },
    )
    assert started.status_code == 200
    wizard_id = started.json()["data"]["id"]

    _complete_business_basics(headers, wizard_id, business_name="Clinica Dedupe", bot_name="Bot Dedupe")

    payload = {
        "services": ["Valoracion guiada premium"],
        "primary_ctas": [{"key": "assessment", "label": "Agendar valoración", "goal": "assessment"}],
    }
    first = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/catalog_offer",
        headers=headers,
        json={"payload": payload},
    )
    assert first.status_code == 200
    first_data = first.json()["data"]
    first_revision = first_data["wizard_revision"]

    second = client.post(
        f"/api/v1/onboarding/wizard/{wizard_id}/steps/catalog_offer",
        headers=headers,
        json={"payload": payload, "expected_revision": first_revision},
    )
    assert second.status_code == 200
    second_data = second.json()["data"]
    assert second_data["wizard_revision"] == first_revision



def test_guided_onboarding_blueprint_progress_uses_only_captured_answers() -> None:
    from backend.app.vertical_onboarding_runtime import build_guided_onboarding_blueprint

    blueprint = build_guided_onboarding_blueprint(
        vertical_id="dental",
        subvertical="Ortodoncia",
        primary_objective="agendar",
        answers={
            "vertical_fit": {
                "vertical_id": "dental",
                "subvertical": "Ortodoncia",
                "primary_objective": "agendar",
            }
        },
    )

    assert blueprint["current_step"] == "business_basics"
    assert blueprint["progress_percent"] < 100
    assert blueprint["answers"]["catalog_offer"] == {
        "services": [],
        "featured_offers": [],
        "primary_ctas": [],
        "pricing_notes": [],
    }
    assert len(blueprint["setup"]["wizard"]["recommended_ctas"]) >= 1
    assert len(blueprint["setup"]["services"]) >= 1



def test_guided_onboarding_start_persists_captured_answers_without_future_defaults() -> None:
    _seed_guided_onboarding_scope()
    headers = {**_auth_headers(), "x-organization-id": ORG_ID}

    started = client.post(
        "/api/v1/onboarding/wizard/start",
        headers=headers,
        json={
            "organization_id": ORG_ID,
            "vertical_id": "dental",
            "subvertical": "ortodoncia",
            "primary_objective": "agendar",
        },
    )
    assert started.status_code == 200
    wizard = started.json()["data"]

    assert wizard["current_step"] == "business_basics"
    assert wizard["progress_percent"] < 100
    assert wizard["answers"]["vertical_fit"]["vertical_id"] == "dental"
    assert wizard["answers"]["catalog_offer"] == {
        "services": [],
        "featured_offers": [],
        "primary_ctas": [],
        "pricing_notes": [],
    }
    assert wizard["answers"]["knowledge_seed"] == {
        "faqs": [],
        "policies": [],
        "knowledge_sources": [],
        "owner_user_id": None,
    }
    assert len(wizard["setup"]["wizard"]["recommended_integrations"]) >= 1
    assert len(wizard["setup"]["services"]) >= 1


def test_guided_onboarding_get_repairs_integrity_drift_before_returning() -> None:
    _seed_guided_onboarding_scope()
    headers = {**_auth_headers(), "x-organization-id": ORG_ID}

    started = client.post(
        "/api/v1/onboarding/wizard/start",
        headers=headers,
        json={
            "organization_id": ORG_ID,
            "vertical_id": "dental",
            "subvertical": "ortodoncia",
            "primary_objective": "agendar",
        },
    )
    assert started.status_code == 200
    wizard_id = started.json()["data"]["id"]

    with get_connection() as conn:
        execute(
            conn,
            "UPDATE vertical_onboarding_wizards SET current_step = ?, progress_percent = ?, subvertical = ?, setup_json = ?, checklist_json = ? WHERE id = ?",
            (
                "launch_review",
                100,
                "subvertical-invalida",
                to_json({}),
                to_json([]),
                wizard_id,
            ),
        )
        execute(
            conn,
            "UPDATE vertical_onboarding_step_runs SET step_status = ?, payload_json = ?, completed_at = ? WHERE wizard_id = ? AND step_key = ?",
            (
                "completed",
                to_json({"business_name": "estado corrupto"}),
                utcnow_iso(),
                wizard_id,
                "business_basics",
            ),
        )
        conn.commit()

    repaired = client.get(f"/api/v1/onboarding/wizard/{wizard_id}", headers=headers)
    assert repaired.status_code == 200
    wizard = repaired.json()["data"]

    assert wizard["current_step"] == "business_basics"
    assert wizard["progress_percent"] < 100
    assert wizard["subvertical"] == "ortodoncia"
    assert wizard["setup"]
    assert wizard["checklist"]
    assert wizard["diagnostics"]["integrity_mismatch"] is False
    business_step = next(item for item in wizard.get("step_runs") or [] if item["step_key"] == "business_basics")
    assert business_step["step_status"] in {"pending", "in_progress"}
    assert business_step["payload"].get("business_name", "") != "estado corrupto"
    assert business_step["payload"].get("bot_name", "") == ""
    assert any(item["event_type"] == "wizard.integrity_reconciled" for item in wizard.get("event_log") or [])
