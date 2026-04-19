from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_one, get_connection, init_db
from backend.app.main import app
from backend.app.utils import to_json, utcnow_iso
from backend.app.whatsapp_delivery_truth import record_whatsapp_delivery_status, seed_whatsapp_delivery_projection
from backend.tests.test_activation_foundations import _auth_headers
from backend.tests.test_whatsapp_channel_runtime import _ensure_whatsapp_number
from backend.worker import process_outbox


client = TestClient(app)


def _ensure_truth_conversation(*, bot_id: str, conversation_id: str, contact_id: str, phone_number_id: str, phone: str = "+521555001234") -> None:
    init_db()
    _auth_headers("org_activation")
    with get_connection() as conn:
        now = utcnow_iso()
        if not fetch_one(conn, "SELECT * FROM bots WHERE id = ?", (bot_id,)):
            execute(
                conn,
                "INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, published_version_id, config_draft_json, created_at, updated_at, deleted_at) VALUES (?, 'org_activation', ?, ?, 'fitness', 'es', 'America/Mexico_City', 'active', 0, 'published', NULL, '{}', ?, ?, NULL)",
                (bot_id, bot_id, bot_id, now, now),
            )
        if not fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", (contact_id,)):
            execute(
                conn,
                "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES (?, 'org_activation', ?, ?, ?, '[]', ?, ?)",
                (contact_id, phone, contact_id, f"{contact_id}@example.com", now, now),
            )
        if not fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (conversation_id,)):
            execute(
                conn,
                "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES (?, 'org_activation', ?, ?, 'open', 0, 1, NULL, NULL, ?, NULL, NULL, NULL, ?, ?)",
                (conversation_id, bot_id, contact_id, now, now, now),
            )
        if not fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (f"seed_inbound_{conversation_id}",)):
            execute(
                conn,
                "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES (?, 'org_activation', ?, ?, ?, 'inbound', 'text', 'whatsapp', 'hola', ?, 'received', '{}', ?)",
                (f"seed_inbound_{conversation_id}", conversation_id, contact_id, bot_id, f"wamid-seed-{conversation_id}", now),
            )
        execute(
            conn,
            "UPDATE conversations SET status = 'open', human_takeover = 0, ai_active = 1, automation_freeze_until = NULL, last_message_at = ?, updated_at = ? WHERE id = ?",
            (now, now, conversation_id),
        )
    _ensure_whatsapp_number(bot_id=bot_id, phone_number_id=phone_number_id)


def test_delivery_truth_projection_moves_from_accepted_to_read_end_to_end(monkeypatch) -> None:
    headers = _auth_headers()
    _ensure_truth_conversation(bot_id="bot_truth_projection", conversation_id="conv_truth_projection", contact_id="ct_truth_projection", phone_number_id="wa_truth_projection", phone="521555001234")

    def _fake_send(conn, *, organization_id: str, bot_id: str, phone: str, payload: dict):
        return {
            "provider": "meta_cloud_api",
            "status": "sent",
            "phone_number_id": "wa_truth_projection",
            "external_id": "wamid-truth-projection-1",
            "status_code": 200,
            "response": {"messages": [{"id": "wamid-truth-projection-1"}], "phone_number_id": "wa_truth_projection"},
        }

    monkeypatch.setattr("backend.worker.send_whatsapp_message", _fake_send)

    response = client.post(
        "/api/v1/conversations/conv_truth_projection/messages",
        headers=headers,
        json={"kind": "text", "body": "Hola, déjalo montado end to end."},
    )
    assert response.status_code == 200
    outbox_id = response.json()["outbox_id"]

    processed = process_outbox()
    assert any(item["id"] == outbox_id and item["delivery_truth_status"] == "accepted" for item in processed)

    with get_connection() as conn:
        projection = fetch_one(conn, "SELECT * FROM whatsapp_delivery_projection WHERE provider_message_id = ?", ("wamid-truth-projection-1",))
    assert projection is not None
    assert projection["current_status"] == "accepted"
    assert projection["accepted_at"] is not None
    assert projection["delivered_at"] is None
    assert projection["read_at"] is None

    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-truth-projection",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": "wa_truth_projection"},
                            "statuses": [
                                {"id": "wamid-truth-projection-1", "status": "delivered", "recipient_id": "521555001234", "timestamp": "1710003001"},
                                {"id": "wamid-truth-projection-1", "status": "read", "recipient_id": "521555001234", "timestamp": "1710003002"},
                            ],
                        },
                    }
                ],
            }
        ],
    }
    webhook_response = client.post("/webhooks/whatsapp/wa_truth_projection", json=webhook_payload)
    assert webhook_response.status_code == 200

    with get_connection() as conn:
        projection = fetch_one(conn, "SELECT * FROM whatsapp_delivery_projection WHERE provider_message_id = ?", ("wamid-truth-projection-1",))
    assert projection is not None
    assert projection["current_status"] == "read"
    assert projection["delivered_at"] is not None
    assert projection["read_at"] is not None


def test_whatsapp_delivery_truth_analytics_endpoint_returns_real_breakdowns() -> None:
    headers = _auth_headers()
    _ensure_truth_conversation(bot_id="bot_truth_metrics", conversation_id="conv_truth_metrics", contact_id="ct_truth_metrics", phone_number_id="wa_truth_metrics", phone="521555001235")

    seeds = [
        {
            "message_id": "msg_truth_metrics_1",
            "outbox_id": "out_truth_metrics_1",
            "provider_message_id": "wamid-truth-metrics-1",
            "template": "welcome_template",
            "status_events": [
                {"message_id": "wamid-truth-metrics-1", "status": "delivered", "timestamp": "1710004001", "recipient_id": "521555001235", "metadata": {"phone_number_id": "wa_truth_metrics"}},
                {"message_id": "wamid-truth-metrics-1", "status": "read", "timestamp": "1710004002", "recipient_id": "521555001235", "metadata": {"phone_number_id": "wa_truth_metrics"}},
            ],
        },
        {
            "message_id": "msg_truth_metrics_2",
            "outbox_id": "out_truth_metrics_2",
            "provider_message_id": "wamid-truth-metrics-2",
            "template": "welcome_template",
            "status_events": [
                {"message_id": "wamid-truth-metrics-2", "status": "failed", "timestamp": "1710004010", "recipient_id": "521555001235", "errors": [{"code": 131048, "message": "delivery failed"}], "metadata": {"phone_number_id": "wa_truth_metrics"}},
            ],
        },
        {
            "message_id": "msg_truth_metrics_3",
            "outbox_id": "out_truth_metrics_3",
            "provider_message_id": "wamid-truth-metrics-3",
            "template": "recovery_template",
            "status_events": [
                {"message_id": "wamid-truth-metrics-3", "status": "delivered", "timestamp": "1710004020", "recipient_id": "521555001235", "metadata": {"phone_number_id": "wa_truth_metrics"}},
            ],
        },
    ]

    with get_connection() as conn:
        execute(conn, "DELETE FROM whatsapp_delivery_status_facts WHERE provider_message_id LIKE 'wamid-truth-metrics-%'")
        execute(conn, "DELETE FROM whatsapp_delivery_projection WHERE provider_message_id LIKE 'wamid-truth-metrics-%'")
        execute(conn, "DELETE FROM outbox_messages WHERE id LIKE 'out_truth_metrics_%'")
        execute(conn, "DELETE FROM messages WHERE id LIKE 'msg_truth_metrics_%'")
        for item in seeds:
            execute(
                conn,
                "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES (?, 'org_activation', 'conv_truth_metrics', 'ct_truth_metrics', 'bot_truth_metrics', 'outbound', 'template', 'human', ?, ?, 'sent', '{}', ?)",
                (item["message_id"], f"Body {item['template']}", item["provider_message_id"], utcnow_iso()),
            )
            execute(
                conn,
                "INSERT INTO outbox_messages (id, organization_id, bot_id, execution_run_id, conversation_id, channel, payload_json, governance_json, status, attempts, last_error, provider_message_id, provider_status_code, provider_response_json, priority, next_attempt_at, locked_at, scheduled_for, sent_at, created_at) VALUES (?, 'org_activation', 'bot_truth_metrics', NULL, 'conv_truth_metrics', 'whatsapp', ?, ?, 'sent', 1, NULL, ?, 200, '{}', 70, NULL, NULL, ?, ?, ?)",
                (
                    item["outbox_id"],
                    to_json({"body": f"Body {item['template']}", "message_id": item["message_id"], "contact_id": "ct_truth_metrics", "message_type": "template", "template": {"name": item["template"]}}),
                    to_json({"selected_template": item["template"], "message_type": "template"}),
                    item["provider_message_id"],
                    utcnow_iso(),
                    utcnow_iso(),
                    utcnow_iso(),
                ),
            )
            outbox = fetch_one(conn, "SELECT * FROM outbox_messages WHERE id = ?", (item["outbox_id"],))
            message = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (item["message_id"],))
            seed_whatsapp_delivery_projection(conn, outbox=outbox, message=message)
            for status_event in item["status_events"]:
                record_whatsapp_delivery_status(conn, organization_id="org_activation", bot_id="bot_truth_metrics", event=status_event, outbox=outbox, message=message, source="test")

    response = client.get(
        "/api/v1/analytics/whatsapp/delivery-truth?organization_id=org_activation&bot_id=bot_truth_metrics&window_hours=168&limit=10",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["accepted_count"] == 3
    assert data["summary"]["delivered_count"] == 2
    assert data["summary"]["read_count"] == 1
    assert data["summary"]["failed_count"] == 1
    assert data["summary"]["delivery_rate"] == 66.67
    assert data["summary"]["fail_rate"] == 33.33
    assert len(data["recent_messages"]) == 3
    by_template = {item["label"]: item for item in data["breakdowns"]["by_template"]}
    assert by_template["welcome_template"]["accepted_count"] == 2
    assert by_template["welcome_template"]["fail_rate"] == 50.0
    assert by_template["recovery_template"]["delivery_rate"] == 100.0
