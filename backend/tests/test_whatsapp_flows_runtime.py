from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import fetch_all, get_connection, init_db
from backend.app.main import app
from backend.app.platform import store_secret
from backend.tests.test_activation_foundations import _auth_headers
from backend.tests.test_whatsapp_channel_runtime import _ensure_whatsapp_number


client = TestClient(app)


FLOW_JSON_V1 = {
    "version": "7.1",
    "data_api_version": "3.0",
    "routing_model": {"SCREEN_ONE": ["SCREEN_TWO"], "SCREEN_TWO": []},
    "screens": [
        {"id": "SCREEN_ONE", "title": "Inicio", "layout": {"type": "SingleColumnLayout", "children": [{"type": "TextHeading", "text": "Inicio"}]}},
        {"id": "SCREEN_TWO", "title": "Confirmación", "terminal": True, "layout": {"type": "SingleColumnLayout", "children": [{"type": "TextHeading", "text": "Confirmación"}]}} ,
    ],
}

FLOW_JSON_V2 = {
    "version": "7.1",
    "data_api_version": "3.0",
    "routing_model": {"SCREEN_A": ["SCREEN_B"], "SCREEN_B": []},
    "screens": [
        {"id": "SCREEN_A", "title": "Perfilado", "layout": {"type": "SingleColumnLayout", "children": [{"type": "TextHeading", "text": "Perfilado"}]}},
        {"id": "SCREEN_B", "title": "Resumen", "terminal": True, "layout": {"type": "SingleColumnLayout", "children": [{"type": "TextHeading", "text": "Resumen"}]}} ,
    ],
}


def _seed_meta_connectivity() -> None:
    init_db()
    _auth_headers()
    _ensure_whatsapp_number(phone_number_id="wa_flow_runtime")
    with get_connection() as conn:
        store_secret(conn, organization_id="org_activation", bot_id="bot_activation", scope="bot", key_name="META_ACCESS_TOKEN", secret_value="meta-token-12345678")


def test_whatsapp_flow_builder_execution_runtime_and_analytics() -> None:
    _seed_meta_connectivity()
    headers = _auth_headers()

    create_response = client.post(
        "/api/v1/whatsapp/flows",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "name": "Flow de citas",
            "flow_type": "appointment_booking",
            "flow_json": FLOW_JSON_V1,
            "categories": ["APPOINTMENT_BOOKING"],
            "fallback": {"mode": "human_handoff", "message": "Te paso con una persona."},
            "compatibility": {"min_flow_message_version": 4},
        },
    )
    assert create_response.status_code == 200
    flow = create_response.json()
    flow_id = flow["id"]
    version_1 = flow["versions"][0]["id"]

    version_response = client.post(
        f"/api/v1/whatsapp/flows/{flow_id}/versions",
        headers=headers,
        json={"flow_json": FLOW_JSON_V2, "compatibility": {"min_flow_message_version": 3}},
    )
    assert version_response.status_code == 200
    version_2 = version_response.json()["id"]

    experiment_response = client.post(
        f"/api/v1/whatsapp/flows/{flow_id}/experiments",
        headers=headers,
        json={"version_a_id": version_1, "version_b_id": version_2, "rollout_percentage": 100, "status": "active"},
    )
    assert experiment_response.status_code == 200

    fallback_execution = client.post(
        f"/api/v1/whatsapp/flows/{flow_id}/execute",
        headers=headers,
        json={
            "conversation_id": "conv_activation",
            "contact_id": "ct_activation",
            "flow_token": "tok-unsupported",
            "client_capabilities": {"supports_flows": False, "flow_message_version": 2},
        },
    )
    assert fallback_execution.status_code == 200
    fallback_payload = fallback_execution.json()
    assert fallback_payload["status"] == "fallback"
    assert fallback_payload["fallback"]["mode"] == "human_handoff"

    execute_response = client.post(
        f"/api/v1/whatsapp/flows/{flow_id}/execute",
        headers=headers,
        json={
            "conversation_id": "conv_activation",
            "contact_id": "ct_activation",
            "flow_token": "tok-supported",
            "version_id": version_2,
            "client_capabilities": {"supports_flows": True, "flow_message_version": 5},
        },
    )
    assert execute_response.status_code == 200
    execution = execute_response.json()
    assert execution["status"] == "started"
    assert execution["provider_payload"]["flow"]["flow_action_payload"]["screen"] == "SCREEN_A"

    runtime_next = client.post(
        f"/api/v1/whatsapp/flows/{flow_id}/runtime",
        json={"execution_id": execution["execution_id"], "action": "next", "screen_id": "SCREEN_A"},
    )
    assert runtime_next.status_code == 200
    assert runtime_next.json()["status"] == "running"
    assert runtime_next.json()["next_screen_id"] == "SCREEN_B"

    runtime_complete = client.post(
        f"/api/v1/whatsapp/flows/{flow_id}/runtime",
        json={"execution_id": execution["execution_id"], "action": "submit", "screen_id": "SCREEN_B", "submitted_data": {"confirmed": True}},
    )
    assert runtime_complete.status_code == 200
    assert runtime_complete.json()["completed"] is True

    event_response = client.post(
        f"/api/v1/whatsapp/flows/{flow_id}/events",
        headers=headers,
        json={"execution_id": execution["execution_id"], "event_type": "flow_completed_from_webhook", "screen_id": "SCREEN_B", "step_index": 3, "payload": {"provider": "meta"}},
    )
    assert event_response.status_code == 200

    analytics_response = client.get(
        f"/api/v1/whatsapp/flows/{flow_id}/analytics",
        headers=headers,
        params={"since": "2026-01-01", "until": "2026-12-31"},
    )
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert analytics["flow"]["id"] == flow_id
    assert any(item["status"] == "completed" for item in analytics["executions"])
    assert any(item["event_type"] in {"screen_view", "step_completed", "flow_completed_from_webhook"} for item in analytics["events"])


def test_whatsapp_flow_publish_sync_and_rollback(monkeypatch) -> None:
    _seed_meta_connectivity()
    headers = _auth_headers()

    create_response = client.post(
        "/api/v1/whatsapp/flows",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "name": "Flow remoto",
            "flow_type": "guided_quote",
            "flow_json": FLOW_JSON_V1,
            "categories": ["OTHER"],
        },
    )
    assert create_response.status_code == 200
    flow = create_response.json()
    flow_id = flow["id"]
    version_id = flow["versions"][0]["id"]

    from backend.app.domains import whatsapp_flows as wf

    monkeypatch.setattr(wf.MetaFlowClient, "create_flow", lambda self, **kwargs: {"id": "meta-flow-001"})
    monkeypatch.setattr(wf.MetaFlowClient, "upload_flow_json", lambda self, remote_flow_id, **kwargs: {"success": True, "validation_errors": []})
    monkeypatch.setattr(wf.MetaFlowClient, "publish_flow", lambda self, remote_flow_id: {"success": True})
    monkeypatch.setattr(wf.MetaFlowClient, "get_flow", lambda self, remote_flow_id: {"id": remote_flow_id, "status": "PUBLISHED", "preview": {"url": "https://preview.example"}, "data_api_version": "3.0"})
    monkeypatch.setattr(wf.MetaFlowClient, "get_preview", lambda self, remote_flow_id: {"preview": {"url": "https://preview.example"}})
    monkeypatch.setattr(wf.MetaFlowClient, "get_endpoint_metric", lambda self, remote_flow_id, **kwargs: {"metric": [{"name": "ENDPOINT_AVAILABILITY", "value": 99.9}]})

    publish_response = client.post(
        f"/api/v1/whatsapp/flows/{flow_id}/publish",
        headers=headers,
        json={"version_id": version_id},
    )
    assert publish_response.status_code == 200
    published = publish_response.json()
    assert published["remote_flow_id"] == "meta-flow-001"
    assert published["published_version_id"] == version_id

    sync_response = client.post(f"/api/v1/whatsapp/flows/{flow_id}/sync", headers=headers)
    assert sync_response.status_code == 200
    assert sync_response.json()["remote_status"] == "PUBLISHED"

    version_response = client.post(
        f"/api/v1/whatsapp/flows/{flow_id}/versions",
        headers=headers,
        json={"flow_json": FLOW_JSON_V2},
    )
    assert version_response.status_code == 200

    rollback_response = client.post(
        f"/api/v1/whatsapp/flows/{flow_id}/rollback",
        headers=headers,
        json={"target_version_id": version_id},
    )
    assert rollback_response.status_code == 200
    rolled_back = rollback_response.json()
    assert rolled_back["published_version_id"] != version_id
    assert len(rolled_back["versions"]) >= 3

    with get_connection() as conn:
        publications = fetch_all(conn, "SELECT action, status FROM whatsapp_flow_publications WHERE flow_id = ? ORDER BY started_at ASC", (flow_id,))
    assert any(row["action"] == "publish" and row["status"] == "published" for row in publications)
    assert any(row["action"] == "sync" and row["status"] == "synced" for row in publications)
