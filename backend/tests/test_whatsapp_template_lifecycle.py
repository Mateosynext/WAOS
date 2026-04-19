from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_all, fetch_one, get_connection, init_db
from backend.app.main import app
from backend.app.platform import store_secret
from backend.app.utils import to_json, utcnow_iso
from backend.app.whatsapp import enqueue_manual_whatsapp_message
from backend.tests.test_activation_foundations import _auth_headers
from backend.tests.test_whatsapp_channel_runtime import _ensure_whatsapp_number
from backend.worker import RetryableProviderError, process_outbox


client = TestClient(app)


def _seed_template_runtime(*, phone_number_id: str = "wa_template_lifecycle") -> None:
    init_db()
    _auth_headers()
    _ensure_whatsapp_number(phone_number_id=phone_number_id)
    with get_connection() as conn:
        store_secret(conn, organization_id="org_activation", bot_id="bot_activation", scope="bot", key_name="META_ACCESS_TOKEN", secret_value="meta-token-12345678")


APPROVED_TEMPLATE_VERSION = {
    "language_code": "es_MX",
    "category": "utility",
    "body_text": "Hola {{1}}, tu cita es el {{2}}.",
    "header_type": "TEXT",
    "header_text": "Agenda {{1}}",
    "sample_values": {"body": ["Mateo", "viernes 5:30 pm"], "header": ["confirmada"]},
    "variables": [
        {"component": "body", "index": 1, "name": "customer_name", "sample": "Mateo"},
        {"component": "body", "index": 2, "name": "appointment_slot", "sample": "viernes 5:30 pm"},
        {"component": "header", "index": 1, "name": "status", "sample": "confirmada"},
    ],
    "buttons": [{"type": "quick_reply", "text": "Confirmar"}],
    "approval_status": "approved",
}


SIMPLE_APPROVED_TEMPLATE_VERSION = {
    "language_code": "es_MX",
    "category": "utility",
    "body_text": "Hola {{1}}, tenemos seguimiento para ti.",
    "sample_values": {"body": ["Mateo"]},
    "variables": [{"component": "body", "index": 1, "name": "customer_name", "sample": "Mateo"}],
    "approval_status": "approved",
}


TEMPLATE_COMPONENTS_ONE_VAR = [
    {
        "type": "body",
        "parameters": [
            {"type": "text", "text": "Mateo"},
        ],
    }
]


TEMPLATE_COMPONENTS_TWO_BODY_AND_HEADER = [
    {
        "type": "header",
        "parameters": [
            {"type": "text", "text": "confirmada"},
        ],
    },
    {
        "type": "body",
        "parameters": [
            {"type": "text", "text": "Mateo"},
            {"type": "text", "text": "viernes 5:30 pm"},
        ],
    },
]


def test_whatsapp_template_lifecycle_sync_and_analytics(monkeypatch) -> None:
    _seed_template_runtime(phone_number_id="wa_template_lifecycle_sync")
    headers = _auth_headers()

    lint_response = client.post(
        "/api/v1/whatsapp/templates/lint",
        headers=headers,
        json={
            "name": "appointment_media_invalid",
            "version": {
                "language_code": "es_MX",
                "category": "utility",
                "body_text": "Hola {{1}}",
                "header_type": "IMAGE",
                "sample_values": {"body": ["Mateo"]},
                "variables": [{"component": "body", "index": 1, "name": "customer_name", "sample": "Mateo"}],
            },
        },
    )
    assert lint_response.status_code == 200
    lint_payload = lint_response.json()
    assert lint_payload["ok"] is False
    assert any(item["code"] == "header_asset_required" for item in lint_payload["errors"])

    create_response = client.post(
        "/api/v1/whatsapp/templates",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "name": "appointment_reminder_core",
            "category": "utility",
            "default_language": "es_MX",
            "version": APPROVED_TEMPLATE_VERSION,
        },
    )
    assert create_response.status_code == 200
    template = create_response.json()
    template_id = template["id"]
    approved_version_id = template["approved_version_id"]

    version_response = client.post(
        f"/api/v1/whatsapp/templates/{template_id}/versions",
        headers=headers,
        json={
            "language_code": "es_MX",
            "category": "marketing",
            "body_text": "Hola {{1}}, vuelve hoy y recibe {{2}}.",
            "sample_values": {"body": ["Mateo", "10%" ]},
            "variables": [
                {"component": "body", "index": 1, "name": "customer_name", "sample": "Mateo"},
                {"component": "body", "index": 2, "name": "discount", "sample": "10%"},
            ],
        },
    )
    assert version_response.status_code == 200
    rejected_version_id = version_response.json()["id"]

    from backend.app.domains import whatsapp_templates as wt

    monkeypatch.setattr(wt.MetaTemplateClient, "create_template_from_version", lambda self, **kwargs: {"id": "meta-template-001", "status": "PENDING"})
    monkeypatch.setattr(wt.MetaTemplateClient, "get_template_status", lambda self, **kwargs: {"id": "meta-template-001", "status": "APPROVED", "quality_rating": "GREEN"})

    sync_response = client.post(
        f"/api/v1/whatsapp/templates/{template_id}/sync",
        headers=headers,
        json={"version_id": approved_version_id, "action": "publish"},
    )
    assert sync_response.status_code == 200
    assert sync_response.json()["last_sync_status"] == "PENDING"

    status_response = client.post(
        f"/api/v1/whatsapp/templates/{template_id}/sync-status",
        headers=headers,
        params={"version_id": approved_version_id},
    )
    assert status_response.status_code == 200
    assert status_response.json()["approved_version_id"] == approved_version_id

    approval_response = client.post(
        f"/api/v1/whatsapp/templates/{template_id}/approval",
        headers=headers,
        json={"version_id": rejected_version_id, "approval_status": "rejected", "rejection_reason": "Copy demasiado promocional para utility"},
    )
    assert approval_response.status_code == 200
    versions = {item["id"]: item for item in approval_response.json()["versions"]}
    assert versions[approved_version_id]["approval_status"] == "approved"
    assert versions[rejected_version_id]["approval_status"] == "rejected"

    with get_connection() as conn:
        execute(
            conn,
            "INSERT INTO whatsapp_delivery_projection (id, organization_id, bot_id, conversation_id, contact_id, outbox_id, message_id, provider_message_id, phone_number_id, recipient_id, template_name, message_kind, vertical, accepted_at, sent_at, delivered_at, read_at, failed_at, current_status, first_event_at, last_event_at, pricing_json, metadata_json, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', 'conv_activation', 'ct_activation', NULL, NULL, 'wamid-template-1', 'wa_template_lifecycle_sync', '5215550001111', 'appointment_reminder_core', 'template', 'fitness', ?, ?, ?, ?, NULL, 'read', ?, ?, '{}', ?, ?, ?)",
            (
                'wdp_template_1',
                utcnow_iso(),
                utcnow_iso(),
                utcnow_iso(),
                utcnow_iso(),
                utcnow_iso(),
                utcnow_iso(),
                to_json({"governance": {"selected_template_version_id": approved_version_id, "selected_template_language": "es_MX", "message_category": "utility"}}),
                utcnow_iso(),
                utcnow_iso(),
            ),
        )
        execute(
            conn,
            "INSERT INTO whatsapp_delivery_projection (id, organization_id, bot_id, conversation_id, contact_id, outbox_id, message_id, provider_message_id, phone_number_id, recipient_id, template_name, message_kind, vertical, accepted_at, sent_at, delivered_at, read_at, failed_at, current_status, first_event_at, last_event_at, pricing_json, metadata_json, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', 'conv_activation', 'ct_activation', NULL, NULL, 'wamid-template-2', 'wa_template_lifecycle_sync', '5215550001111', 'appointment_reminder_core', 'template', 'fitness', ?, ?, NULL, NULL, ?, 'failed', ?, ?, '{}', ?, ?, ?)",
            (
                'wdp_template_2',
                utcnow_iso(),
                utcnow_iso(),
                utcnow_iso(),
                utcnow_iso(),
                utcnow_iso(),
                to_json({"governance": {"selected_template_version_id": approved_version_id, "selected_template_language": "es_MX", "message_category": "utility"}}),
                utcnow_iso(),
                utcnow_iso(),
            ),
        )

    analytics_response = client.get(
        f"/api/v1/whatsapp/templates/{template_id}/analytics",
        headers=headers,
        params={"since": "2026-01-01", "until": "2026-12-31"},
    )
    assert analytics_response.status_code == 200
    summary = analytics_response.json()["summary"]
    assert summary["accepted_count"] == 2
    assert summary["failed_count"] == 1
    assert summary["delivery_rate"] == 50.0
    assert summary["fail_rate"] == 50.0


def test_whatsapp_template_governance_auto_fallback_when_requested_template_not_approved(monkeypatch) -> None:
    _seed_template_runtime(phone_number_id="wa_template_governance_fallback")
    headers = _auth_headers()

    fallback_response = client.post(
        "/api/v1/whatsapp/templates",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "name": "appointment_recovery_template",
            "category": "utility",
            "default_language": "es_MX",
            "version": SIMPLE_APPROVED_TEMPLATE_VERSION,
        },
    )
    assert fallback_response.status_code == 200

    pending_response = client.post(
        "/api/v1/whatsapp/templates",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "name": "appointment_primary_pending",
            "category": "utility",
            "default_language": "es_MX",
            "fallback_template_id": fallback_response.json()["id"],
            "version": {**SIMPLE_APPROVED_TEMPLATE_VERSION, "approval_status": "pending"},
        },
    )
    assert pending_response.status_code == 200

    with get_connection() as conn:
        execute(conn, "DELETE FROM outbox_messages WHERE organization_id = ? AND channel = 'whatsapp' AND status IN ('queued','retry','running')", ("org_activation",))
        enqueue_manual_whatsapp_message(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            contact_id="ct_activation",
            body="Seguimiento",
            author_user_id="usr_activation",
            whatsapp_payload={
                "message_type": "template",
                "template": {
                    "name": "appointment_primary_pending",
                    "language": {"code": "es_MX"},
                    "components": TEMPLATE_COMPONENTS_ONE_VAR,
                },
            },
        )

    captured: list[dict] = []

    def _fake_send(conn, *, organization_id: str, bot_id: str, phone: str, payload: dict):
        captured.append(payload)
        return {
            "provider": "meta_cloud_api",
            "status": "sent",
            "phone_number_id": "wa_template_governance_fallback",
            "external_id": "wamid-auto-fallback-1",
            "status_code": 200,
            "response": {"messages": [{"id": "wamid-auto-fallback-1"}]},
        }

    monkeypatch.setattr("backend.worker.send_whatsapp_message", _fake_send)

    processed = process_outbox()
    assert processed[0]["status"] == "sent"
    assert captured[0]["template"]["name"] == "appointment_recovery_template"


def test_whatsapp_template_provider_error_retries_with_configured_fallback(monkeypatch) -> None:
    _seed_template_runtime(phone_number_id="wa_template_provider_fallback")
    headers = _auth_headers()

    fallback_response = client.post(
        "/api/v1/whatsapp/templates",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "name": "provider_safe_recovery",
            "category": "utility",
            "default_language": "es_MX",
            "version": SIMPLE_APPROVED_TEMPLATE_VERSION,
        },
    )
    assert fallback_response.status_code == 200
    fallback_id = fallback_response.json()["id"]

    primary_response = client.post(
        "/api/v1/whatsapp/templates",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "name": "provider_risky_primary",
            "category": "utility",
            "default_language": "es_MX",
            "fallback_template_id": fallback_id,
            "version": SIMPLE_APPROVED_TEMPLATE_VERSION,
        },
    )
    assert primary_response.status_code == 200

    with get_connection() as conn:
        execute(conn, "DELETE FROM outbox_messages WHERE organization_id = ? AND channel = 'whatsapp' AND status IN ('queued','retry','running')", ("org_activation",))
        enqueue_manual_whatsapp_message(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            contact_id="ct_activation",
            body="Seguimiento",
            author_user_id="usr_activation",
            whatsapp_payload={
                "message_type": "template",
                "template": {
                    "name": "provider_risky_primary",
                    "language": {"code": "es_MX"},
                    "components": TEMPLATE_COMPONENTS_ONE_VAR,
                },
            },
        )

    captured_names: list[str] = []

    def _fake_send(conn, *, organization_id: str, bot_id: str, phone: str, payload: dict):
        template_name = ((payload.get("template") or {}).get("name"))
        captured_names.append(template_name)
        if template_name == "provider_risky_primary":
            raise RetryableProviderError(
                "template invalid",
                retryable=False,
                status_code=400,
                details={"error_class": "template_invalid", "provider_code": 131008, "retry_after_seconds": None},
            )
        return {
            "provider": "meta_cloud_api",
            "status": "sent",
            "phone_number_id": "wa_template_provider_fallback",
            "external_id": "wamid-template-fallback-success",
            "status_code": 200,
            "response": {"messages": [{"id": "wamid-template-fallback-success"}]},
        }

    monkeypatch.setattr("backend.worker.send_whatsapp_message", _fake_send)

    first_pass = process_outbox()
    failover_entry = next((item for item in first_pass if item.get("template_failover")), None)
    assert failover_entry is not None
    assert failover_entry["status"] == "retry"
    assert failover_entry["template_failover"]["selected_template"] == "provider_safe_recovery"

    with get_connection() as conn:
        outbox = fetch_one(conn, "SELECT payload_json, status FROM outbox_messages WHERE provider_message_id IS NULL ORDER BY created_at DESC LIMIT 1", ())
        updated_payload = (fetch_one(conn, "SELECT payload_json, status FROM outbox_messages ORDER BY created_at DESC LIMIT 1", ()) or outbox)
        payload_json = fetch_one(conn, "SELECT payload_json FROM outbox_messages WHERE status = 'retry' ORDER BY created_at DESC LIMIT 1", ())
        failovers = fetch_all(conn, "SELECT * FROM whatsapp_template_failovers ORDER BY created_at DESC", ())
    assert failovers
    assert 'provider_safe_recovery' in (payload_json or {}).get('payload_json', '')

    second_pass = process_outbox()
    assert second_pass[0]["status"] == "sent"
    assert captured_names == ["provider_risky_primary", "provider_safe_recovery"]
