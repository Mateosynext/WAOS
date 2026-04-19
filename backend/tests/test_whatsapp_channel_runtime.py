from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_all, fetch_one, get_connection, init_db
from backend.app.main import app
from backend.app.utils import to_json, utcnow_iso
from backend.app.whatsapp_channel_runtime import build_whatsapp_outbound_payload
from backend.worker import process_outbox
from backend.tests.test_activation_foundations import _auth_headers


client = TestClient(app)


def _ensure_whatsapp_number(*, organization_id: str = "org_activation", bot_id: str = "bot_activation", phone_number_id: str = "wa_test_number") -> None:
    init_db()
    _auth_headers(organization_id)
    with get_connection() as conn:
        execute(conn, "DELETE FROM whatsapp_policy_decisions WHERE bot_id = ?", (bot_id,))
        execute(conn, "DELETE FROM whatsapp_delivery_status_facts WHERE bot_id = ?", (bot_id,))
        execute(conn, "DELETE FROM whatsapp_delivery_projection WHERE bot_id = ?", (bot_id,))
        execute(conn, "DELETE FROM whatsapp_template_failovers WHERE bot_id = ?", (bot_id,))
        execute(conn, "DELETE FROM whatsapp_opt_outs WHERE bot_id = ?", (bot_id,))
        execute(conn, "DELETE FROM outbox_messages WHERE bot_id = ?", (bot_id,))
        row = fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE bot_id = ?", (bot_id,))
        if row:
            execute(
                conn,
                "UPDATE whatsapp_numbers SET phone_number = ?, phone_number_id = ?, waba_id = ?, connection_status = 'connected', webhook_verify_token = ?, metadata_json = '{}', quality_rating = 'unknown', quality_status = 'unknown', throughput_tier = 'standard', provider_degraded_until = NULL, last_health_check_at = NULL, last_provider_error_code = NULL, last_provider_error_at = NULL, updated_at = ? WHERE id = ?",
                ("+5215550009999", phone_number_id, "waba_test", "verify-token", utcnow_iso(), row["id"]),
            )
        else:
            execute(
                conn,
                "INSERT INTO whatsapp_numbers (id, organization_id, bot_id, provider, phone_number, phone_number_id, waba_id, connection_status, webhook_verify_token, access_token_masked, metadata_json, quality_rating, quality_status, throughput_tier, provider_degraded_until, last_health_check_at, last_provider_error_code, last_provider_error_at, created_at, updated_at) VALUES (?, ?, ?, 'meta_cloud_api', ?, ?, ?, 'connected', ?, ?, '{}', 'unknown', 'unknown', 'standard', NULL, NULL, NULL, NULL, ?, ?)",
                (f"wa_number_{bot_id}", organization_id, bot_id, "+5215550009999", phone_number_id, "waba_test", "verify-token", "masked", utcnow_iso(), utcnow_iso()),
            )


def test_whatsapp_webhook_ingests_rich_inbound_messages(monkeypatch) -> None:
    _ensure_whatsapp_number(phone_number_id="wa_rich_inbound")
    monkeypatch.setattr("backend.app.application.inbound_service.run_ai_pipeline", lambda *args, **kwargs: {"reply": None})

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-rich",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"display_phone_number": "+52 1 555 000 9999", "phone_number_id": "wa_rich_inbound"},
                            "contacts": [{"wa_id": "5215557778888", "profile": {"name": "Clau"}}],
                            "messages": [
                                {"id": "wamid-audio-1", "from": "5215557778888", "timestamp": "1710000001", "type": "audio", "audio": {"id": "aud-1", "mime_type": "audio/ogg", "voice": True}},
                                {"id": "wamid-location-1", "from": "5215557778888", "timestamp": "1710000002", "type": "location", "location": {"latitude": 19.4326, "longitude": -99.1332, "name": "Reforma", "address": "CDMX"}},
                                {"id": "wamid-list-1", "from": "5215557778888", "timestamp": "1710000003", "type": "interactive", "interactive": {"type": "list_reply", "list_reply": {"id": "plan-premium", "title": "Plan Premium", "description": "Con asesor"}}},
                                {"id": "wamid-image-1", "from": "5215557778888", "timestamp": "1710000004", "type": "image", "image": {"id": "img-1", "caption": "Te comparto mi comprobante"}},
                                {"id": "wamid-sticker-1", "from": "5215557778888", "timestamp": "1710000005", "type": "sticker", "sticker": {"id": "stk-1"}},
                            ],
                        },
                    }
                ],
            }
        ],
    }

    response = client.post("/webhooks/whatsapp/wa_rich_inbound", json=payload)
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["processed"] == 4
    assert len(body["ignored"]) == 1
    assert body["ignored"][0]["message_type"] == "sticker"

    with get_connection() as conn:
        rows = fetch_all(conn, "SELECT external_id, kind, source, body, metadata_json FROM messages WHERE external_id IN ('wamid-audio-1','wamid-location-1','wamid-list-1','wamid-image-1') ORDER BY external_id ASC")
    assert [row["kind"] for row in rows] == ["audio", "image", "list_reply", "location"]
    assert all(row["source"] == "whatsapp" for row in rows)
    bodies = {row["external_id"]: row["body"] for row in rows}
    assert "Nota de voz" in bodies["wamid-audio-1"]
    assert "Ubicación compartida" in bodies["wamid-location-1"]
    assert "Plan Premium" in bodies["wamid-list-1"]
    assert "comprobante" in bodies["wamid-image-1"]



def test_whatsapp_webhook_processes_statuses_and_provider_errors() -> None:
    _ensure_whatsapp_number(phone_number_id="wa_status_events")
    with get_connection() as conn:
        for idx, provider_message_id in enumerate(["wamid-out-1", "wamid-out-2"], start=1):
            if not fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (f"msg_status_{idx}",)):
                execute(
                    conn,
                    "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, 'outbound', 'text', 'human', ?, ?, 'sent', '{}', ?)",
                    (f"msg_status_{idx}", "org_activation", "conv_activation", "ct_activation", "bot_activation", f"Mensaje {idx}", provider_message_id, utcnow_iso()),
                )
            if not fetch_one(conn, "SELECT * FROM outbox_messages WHERE id = ?", (f"out_status_{idx}",)):
                execute(
                    conn,
                    "INSERT INTO outbox_messages (id, organization_id, bot_id, execution_run_id, conversation_id, channel, payload_json, status, attempts, last_error, provider_message_id, provider_status_code, provider_response_json, priority, next_attempt_at, locked_at, scheduled_for, sent_at, created_at) VALUES (?, ?, ?, NULL, ?, 'whatsapp', ?, 'sent', 1, NULL, ?, 200, '{}', 50, NULL, NULL, ?, ?, ?)",
                    (f"out_status_{idx}", "org_activation", "bot_activation", "conv_activation", to_json({"body": f"Mensaje {idx}", "message_id": f"msg_status_{idx}", "contact_id": "ct_activation"}), provider_message_id, utcnow_iso(), utcnow_iso(), utcnow_iso()),
                )

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-status",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": "wa_status_events"},
                            "statuses": [
                                {"id": "wamid-out-1", "status": "read", "recipient_id": "5215550001111", "timestamp": "1710001001", "conversation": {"id": "conv-provider-1"}, "pricing": {"category": "service"}},
                                {"id": "wamid-out-2", "status": "failed", "recipient_id": "5215550001111", "timestamp": "1710001002", "errors": [{"code": 131048, "message": "delivery failed"}]},
                            ],
                            "errors": [{"code": 131048, "title": "Rate limit", "message": "Provider rate limited"}],
                        },
                    }
                ],
            }
        ],
    }

    response = client.post("/webhooks/whatsapp/wa_status_events", json=payload)
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status_events"] == 2
    assert body["provider_errors"] == 1

    with get_connection() as conn:
        read_message = fetch_one(conn, "SELECT status, metadata_json FROM messages WHERE external_id = ?", ("wamid-out-1",))
        failed_message = fetch_one(conn, "SELECT status FROM messages WHERE external_id = ?", ("wamid-out-2",))
        read_outbox = fetch_one(conn, "SELECT status FROM outbox_messages WHERE provider_message_id = ?", ("wamid-out-1",))
        failed_outbox = fetch_one(conn, "SELECT status FROM outbox_messages WHERE provider_message_id = ?", ("wamid-out-2",))
        callbacks = fetch_all(conn, "SELECT callback_type, status FROM runtime_callbacks WHERE callback_type LIKE 'whatsapp.%' ORDER BY created_at ASC")
        channel_events = fetch_all(conn, "SELECT event_type FROM channel_events WHERE channel = 'whatsapp' ORDER BY created_at ASC")
    assert read_message["status"] == "read"
    assert failed_message["status"] == "failed"
    assert read_outbox["status"] == "read"
    assert failed_outbox["status"] == "failed"
    assert any(item["callback_type"] == "whatsapp.status.read" for item in callbacks)
    assert any(item["callback_type"] == "whatsapp.status.failed" for item in callbacks)
    assert any(item["callback_type"] == "whatsapp.provider_error" for item in callbacks)
    assert any(item["event_type"] == "whatsapp_provider_error" for item in channel_events)



def test_conversation_api_and_worker_send_template_end_to_end(monkeypatch) -> None:
    headers = _auth_headers()
    _ensure_whatsapp_number(phone_number_id="wa_template_send")
    with get_connection() as conn:
        execute(conn, "DELETE FROM whatsapp_policy_decisions WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_status_facts WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_projection WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_template_failovers WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM outbox_messages WHERE organization_id = ? AND channel = 'whatsapp' AND status IN ('queued','retry','running')", ("org_activation",))
    captured: list[dict] = []

    def _fake_send(conn, *, organization_id: str, bot_id: str, phone: str, payload: dict):
        captured.append({"organization_id": organization_id, "bot_id": bot_id, "phone": phone, "payload": payload})
        return {
            "provider": "meta_cloud_api",
            "status": "sent",
            "phone_number_id": "wa_template_send",
            "external_id": "wamid-template-sent",
            "status_code": 200,
            "response": {"messages": [{"id": "wamid-template-sent"}]},
        }

    monkeypatch.setattr("backend.worker.send_whatsapp_message", _fake_send)

    response = client.post(
        "/api/v1/conversations/conv_activation/messages",
        headers=headers,
        json={
            "kind": "text",
            "whatsapp_payload": {
                "message_type": "template",
                "template": {
                    "name": "appointment_reminder",
                    "language": {"code": "es_MX"},
                    "components": [{"type": "body", "parameters": [{"type": "text", "text": "Mateo"}]}],
                },
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"]["kind"] == "template"
    assert payload["message"]["status"] == "queued"

    processed = process_outbox()
    assert processed
    assert captured
    assert captured[0]["payload"] == {
        "type": "template",
        "template": {
            "name": "appointment_reminder",
            "language": {"code": "es_MX"},
            "components": [{"type": "body", "parameters": [{"type": "text", "text": "Mateo"}]}],
            "category": "utility",
        },
    }

    with get_connection() as conn:
        queued = fetch_one(conn, "SELECT status, provider_message_id FROM outbox_messages WHERE provider_message_id = ?", ("wamid-template-sent",))
        message = fetch_one(conn, "SELECT status, external_id FROM messages WHERE external_id = ?", ("wamid-template-sent",))
    assert queued["status"] == "sent"
    assert message["status"] == "sent"



def test_build_whatsapp_outbound_payload_supports_flow_catalog_and_mark_read() -> None:
    flow_payload = build_whatsapp_outbound_payload(
        {
            "message_type": "flow_entrypoint",
            "flow": {
                "flow_id": "flow-123",
                "flow_token": "token-abc",
                "flow_cta": "Abrir flujo",
                "body": {"text": "Completa tu pre-registro"},
            },
            "body": "Completa tu pre-registro",
        }
    )
    assert flow_payload["type"] == "interactive"
    assert flow_payload["interactive"]["type"] == "flow"
    assert flow_payload["interactive"]["action"]["parameters"]["flow_id"] == "flow-123"

    catalog_payload = build_whatsapp_outbound_payload(
        {
            "message_type": "catalog",
            "catalog": {
                "catalog_id": "cat-1",
                "body": {"text": "Estos son los productos disponibles"},
                "sections": [{"title": "Destacados", "product_items": [{"product_retailer_id": "sku-1"}]}],
            },
            "body": "Estos son los productos disponibles",
        }
    )
    assert catalog_payload["interactive"]["type"] == "product_list"
    assert catalog_payload["interactive"]["action"]["catalog_id"] == "cat-1"

    read_payload = build_whatsapp_outbound_payload({"message_type": "mark_as_read", "read_target": "wamid-in-1"})
    assert read_payload == {"status": "read", "message_id": "wamid-in-1"}


def test_whatsapp_webhook_deduplicates_retries(monkeypatch) -> None:
    _ensure_whatsapp_number(phone_number_id="wa_dedupe")
    monkeypatch.setattr("backend.app.application.inbound_service.run_ai_pipeline", lambda *args, **kwargs: {"reply": None})

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-dedupe",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": "wa_dedupe"},
                            "contacts": [{"wa_id": "5215558889999", "profile": {"name": "Retry User"}}],
                            "messages": [
                                {"id": "wamid-dedupe-1", "from": "5215558889999", "timestamp": "1710002001", "type": "image", "image": {"id": "img-dedupe", "caption": "Comprobante duplicado"}},
                            ],
                        },
                    }
                ],
            }
        ],
    }

    first = client.post("/webhooks/whatsapp/wa_dedupe", json=payload)
    assert first.status_code == 200
    assert first.json()["data"]["processed"] == 1
    assert first.json()["data"]["deduplicated"] == []

    second = client.post("/webhooks/whatsapp/wa_dedupe", json=payload)
    assert second.status_code == 200
    data = second.json()["data"]
    assert data["processed"] == 0
    assert len(data["deduplicated"]) == 1
    assert data["deduplicated"][0]["message_id"] == "wamid-dedupe-1"

    with get_connection() as conn:
        messages = fetch_all(conn, "SELECT id FROM messages WHERE external_id = ?", ("wamid-dedupe-1",))
        receipts = fetch_all(conn, "SELECT id FROM webhook_event_receipts WHERE channel = 'whatsapp' AND external_event_id LIKE ?", ("wa:wa_dedupe:message:wamid-dedupe-1%",))
    assert len(messages) == 1
    assert len(receipts) == 1


def test_conversation_api_rejects_invalid_interactive_payload() -> None:
    headers = _auth_headers()
    _ensure_whatsapp_number(phone_number_id="wa_invalid_payload")

    with get_connection() as conn:
        before_count = fetch_one(conn, "SELECT COUNT(*) AS value FROM outbox_messages WHERE organization_id = ? AND channel = 'whatsapp'", ("org_activation",))["value"]

    response = client.post(
        "/api/v1/conversations/conv_activation/messages",
        headers=headers,
        json={
            "kind": "text",
            "whatsapp_payload": {
                "message_type": "interactive_button",
                "interactive": {
                    "body": {"text": "Elige una opción"},
                    "buttons": [{"id": "", "title": "Confirmar"}],
                },
            },
        },
    )

    assert response.status_code == 422
    assert "whatsapp_interactive_button_id_required" in response.text

    with get_connection() as conn:
        after_count = fetch_one(conn, "SELECT COUNT(*) AS value FROM outbox_messages WHERE organization_id = ? AND channel = 'whatsapp'", ("org_activation",))["value"]
    assert after_count == before_count


def test_whatsapp_governance_rewrites_freeform_to_template_outside_24h(monkeypatch) -> None:
    headers = _auth_headers()
    _ensure_whatsapp_number(phone_number_id="wa_governance_template")
    with get_connection() as conn:
        execute(conn, "DELETE FROM whatsapp_policy_decisions WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_status_facts WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_projection WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_template_failovers WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM outbox_messages WHERE organization_id = ? AND channel = 'whatsapp' AND status IN ('queued','retry','running')", ("org_activation",))
        execute(conn, "UPDATE messages SET created_at = '2026-01-02T00:00:00Z' WHERE conversation_id = ? AND direction = 'inbound' AND source = 'whatsapp'", ("conv_activation",))
    captured: list[dict] = []

    def _fake_send(conn, *, organization_id: str, bot_id: str, phone: str, payload: dict):
        captured.append({"organization_id": organization_id, "bot_id": bot_id, "phone": phone, "payload": payload})
        return {
            "provider": "meta_cloud_api",
            "status": "sent",
            "phone_number_id": "wa_governance_template",
            "external_id": "wamid-governance-template",
            "status_code": 200,
            "response": {"messages": [{"id": "wamid-governance-template"}]},
        }

    monkeypatch.setattr("backend.worker.send_whatsapp_message", _fake_send)

    response = client.post(
        "/api/v1/conversations/conv_activation/messages",
        headers=headers,
        json={
            "kind": "text",
            "body": "Hola, te escribo para continuar tu proceso.",
            "whatsapp_payload": {
                "template_fallback": {
                    "name": "followup_utility",
                    "language": {"code": "es_MX"},
                    "components": [{"type": "body", "parameters": [{"type": "text", "text": "Mateo"}]}],
                },
                "message_category": "utility",
            },
        },
    )
    assert response.status_code == 200
    outbox_id = response.json()["outbox_id"]

    processed = process_outbox()
    assert any(item["id"] == outbox_id and item["status"] == "sent" for item in processed)
    assert captured
    assert captured[0]["payload"]["type"] == "template"
    assert captured[0]["payload"]["template"]["name"] == "followup_utility"

    with get_connection() as conn:
        outbox = fetch_one(conn, "SELECT status, governance_json FROM outbox_messages WHERE id = ?", (outbox_id,))
    governance = __import__("json").loads(outbox["governance_json"])
    assert outbox["status"] == "sent"
    assert governance["decision"] == "rewrite_to_template"
    assert governance["reason_code"] == "outside_customer_care_window_template_required"
    assert governance["message_type"] == "template"



def test_whatsapp_governance_allows_freeform_within_24h(monkeypatch) -> None:
    headers = _auth_headers()
    _ensure_whatsapp_number(phone_number_id="wa_governance_open_window")
    with get_connection() as conn:
        execute(conn, "DELETE FROM whatsapp_policy_decisions WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_status_facts WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_projection WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_template_failovers WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM outbox_messages WHERE organization_id = ? AND channel = 'whatsapp' AND status IN ('queued','retry','running')", ("org_activation",))
        if not fetch_one(conn, "SELECT id FROM messages WHERE id = ?", ("msg_recent_window",)):
            execute(
                conn,
                "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, 'inbound', 'text', 'whatsapp', ?, ?, 'received', '{}', ?)",
                ("msg_recent_window", "org_activation", "conv_activation", "ct_activation", "bot_activation", "¿Siguen abiertos?", "wamid-recent-window", utcnow_iso()),
            )
    captured: list[dict] = []

    def _fake_send(conn, *, organization_id: str, bot_id: str, phone: str, payload: dict):
        captured.append(payload)
        return {
            "provider": "meta_cloud_api",
            "status": "sent",
            "phone_number_id": "wa_governance_open_window",
            "external_id": "wamid-governance-freeform",
            "status_code": 200,
            "response": {"messages": [{"id": "wamid-governance-freeform"}]},
        }

    monkeypatch.setattr("backend.worker.send_whatsapp_message", _fake_send)
    response = client.post(
        "/api/v1/conversations/conv_activation/messages",
        headers=headers,
        json={"kind": "text", "body": "Sí, seguimos abiertos hasta las 8 pm."},
    )
    assert response.status_code == 200
    outbox_id = response.json()["outbox_id"]

    processed = process_outbox()
    assert any(item["id"] == outbox_id and item["status"] == "sent" for item in processed)
    assert captured[0]["type"] == "text"
    assert captured[0]["text"]["body"] == "Sí, seguimos abiertos hasta las 8 pm."

    with get_connection() as conn:
        outbox = fetch_one(conn, "SELECT governance_json FROM outbox_messages WHERE id = ?", (outbox_id,))
    governance = __import__("json").loads(outbox["governance_json"])
    assert governance["reason_code"] == "care_window_open"
    assert governance["message_type"] == "text"
    assert governance["care_window"]["is_open"] is True



def test_whatsapp_governance_blocks_freeform_without_template_outside_24h() -> None:
    headers = _auth_headers()
    _ensure_whatsapp_number(phone_number_id="wa_governance_block")
    with get_connection() as conn:
        execute(conn, "DELETE FROM whatsapp_policy_decisions WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_status_facts WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_projection WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_template_failovers WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM outbox_messages WHERE organization_id = ? AND channel = 'whatsapp' AND status IN ('queued','retry','running')", ("org_activation",))
        execute(conn, "UPDATE messages SET created_at = '2026-01-02T00:00:00Z' WHERE conversation_id = ? AND direction = 'inbound' AND source = 'whatsapp'", ("conv_activation",))

    response = client.post(
        "/api/v1/conversations/conv_activation/messages",
        headers=headers,
        json={"kind": "text", "body": "Solo paso a darte seguimiento."},
    )
    assert response.status_code == 200
    outbox_id = response.json()["outbox_id"]

    processed = process_outbox()
    assert any(item["id"] == outbox_id and item["status"] == "dead_letter" for item in processed)

    with get_connection() as conn:
        outbox = fetch_one(conn, "SELECT status, governance_json, provider_response_json FROM outbox_messages WHERE id = ?", (outbox_id,))
    governance = __import__("json").loads(outbox["governance_json"])
    provider_response = __import__("json").loads(outbox["provider_response_json"])
    assert outbox["status"] == "dead_letter"
    assert governance["reason_code"] == "outside_customer_care_window_template_required"
    assert provider_response["governance"]["status"] == "dead_letter"



def test_whatsapp_governance_endpoint_exposes_health_limits_and_provider_degradation() -> None:
    headers = _auth_headers()
    _ensure_whatsapp_number(phone_number_id="wa_governance_panel")
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-provider-error",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": "wa_governance_panel"},
                            "errors": [{"code": 130429, "title": "Rate limit", "message": "Throughput limit reached"}],
                        },
                    }
                ],
            }
        ],
    }
    response = client.post("/webhooks/whatsapp/wa_governance_panel", json=payload)
    assert response.status_code == 200

    panel = client.get("/api/v1/system/whatsapp-governance", headers=headers)
    assert panel.status_code == 200
    data = panel.json()
    assert data["status"] in {"degraded", "error"}
    assert data["policy"]["customer_care_window_hours"] == 24
    assert data["numbers"]
    number = next(item for item in data["numbers"] if item["bot_id"] == "bot_activation")
    assert number["channel_health"]["throughput"]["limit_per_minute"] >= 1
    assert number["last_provider_error_code"] == "130429"
    assert number["channel_health"]["status"] in {"degraded", "blocked"}


def test_whatsapp_inbound_stop_registers_opt_out_and_skips_ai(monkeypatch) -> None:
    _ensure_whatsapp_number(phone_number_id="wa_opt_out")
    calls: list[dict] = []

    def _run_ai(*args, **kwargs):
        calls.append({"called": True})
        return {"reply": None}

    monkeypatch.setattr("backend.app.application.inbound_service.run_ai_pipeline", _run_ai)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-opt-out",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"display_phone_number": "+52 1 555 000 9999", "phone_number_id": "wa_opt_out"},
                            "contacts": [{"wa_id": "5215551112222", "profile": {"name": "Mateo"}}],
                            "messages": [
                                {"id": "wamid-stop-1", "from": "5215551112222", "timestamp": "1710000100", "type": "text", "text": {"body": "STOP"}},
                            ],
                        },
                    }
                ],
            }
        ],
    }

    response = client.post("/webhooks/whatsapp/wa_opt_out", json=payload)
    assert response.status_code == 200
    with get_connection() as conn:
        opt_out = fetch_one(conn, "SELECT * FROM whatsapp_opt_outs WHERE bot_id = ? AND active = 1 ORDER BY created_at DESC LIMIT 1", ("bot_activation",))
        conv = fetch_one(conn, "SELECT * FROM conversations WHERE bot_id = ? AND contact_id = ?", ("bot_activation", opt_out["contact_id"]))
        queued = fetch_one(conn, "SELECT * FROM outbox_messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1", (conv["id"],))
    assert opt_out["keyword"] == "STOP"
    assert int(conv["ai_active"] or 0) == 0
    assert queued is not None
    assert not calls



def test_whatsapp_governance_blocks_prohibited_content_even_inside_window(monkeypatch) -> None:
    headers = _auth_headers()
    _ensure_whatsapp_number(phone_number_id="wa_content_guard")
    with get_connection() as conn:
        execute(conn, "DELETE FROM whatsapp_policy_decisions WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_status_facts WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_projection WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_template_failovers WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM outbox_messages WHERE organization_id = ? AND channel = 'whatsapp'", ("org_activation",))
        if not fetch_one(conn, "SELECT id FROM messages WHERE id = ?", ("msg_recent_guard",)):
            execute(
                conn,
                "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, 'inbound', 'text', 'whatsapp', ?, ?, 'received', '{}', ?)",
                ("msg_recent_guard", "org_activation", "conv_activation", "ct_activation", "bot_activation", "Hola", "wamid-guard-open", utcnow_iso()),
            )

    monkeypatch.setattr("backend.worker.send_whatsapp_message", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not send")))
    response = client.post(
        "/api/v1/conversations/conv_activation/messages",
        headers=headers,
        json={"kind": "text", "body": "Oferta GRATIS 🚨 haz click aquí bit.ly/demo"},
    )
    assert response.status_code == 200
    outbox_id = response.json()["outbox_id"]
    processed = process_outbox()
    assert any(item["id"] == outbox_id and item["status"] == "dead_letter" for item in processed)
    with get_connection() as conn:
        outbox = fetch_one(conn, "SELECT status, governance_json FROM outbox_messages WHERE id = ?", (outbox_id,))
    governance = __import__("json").loads(outbox["governance_json"])
    assert outbox["status"] == "dead_letter"
    assert governance["reason_code"] == "content_policy_blocked"



def test_whatsapp_governance_enforces_unverified_rate_limit(monkeypatch) -> None:
    headers = _auth_headers()
    _ensure_whatsapp_number(phone_number_id="wa_unverified_limit")
    with get_connection() as conn:
        execute(conn, "DELETE FROM whatsapp_policy_decisions WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_status_facts WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_delivery_projection WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM whatsapp_template_failovers WHERE organization_id = ? AND bot_id = ?", ("org_activation", "bot_activation"))
        execute(conn, "DELETE FROM outbox_messages WHERE organization_id = ? AND channel = 'whatsapp'", ("org_activation",))
        execute(conn, "UPDATE whatsapp_numbers SET metadata_json = ? WHERE bot_id = ?", (to_json({"business_profile": {"verified": False}}), "bot_activation"))
        if not fetch_one(conn, "SELECT id FROM messages WHERE id = ?", ("msg_recent_limit",)):
            execute(
                conn,
                "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, 'inbound', 'text', 'whatsapp', ?, ?, 'received', '{}', ?)",
                ("msg_recent_limit", "org_activation", "conv_activation", "ct_activation", "bot_activation", "Hola", "wamid-limit-open", utcnow_iso()),
            )
        execute(
            conn,
            "INSERT INTO outbox_messages (id, organization_id, bot_id, execution_run_id, conversation_id, channel, payload_json, status, attempts, last_error, provider_message_id, provider_status_code, provider_response_json, priority, next_attempt_at, locked_at, scheduled_for, sent_at, created_at) VALUES (?, ?, ?, NULL, ?, 'whatsapp', ?, 'sent', 1, NULL, ?, 200, '{}', 50, NULL, NULL, ?, ?, ?)",
            ("out_recent_limit", "org_activation", "bot_activation", "conv_activation", to_json({"body": "prev", "message_id": "msg_recent_limit", "contact_id": "ct_activation"}), "wamid-prev-limit", utcnow_iso(), utcnow_iso(), utcnow_iso()),
        )

    monkeypatch.setattr("backend.worker.send_whatsapp_message", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should be throttled")))
    response = client.post(
        "/api/v1/conversations/conv_activation/messages",
        headers=headers,
        json={"kind": "text", "body": "Segundo mensaje demasiado rápido."},
    )
    assert response.status_code == 200
    outbox_id = response.json()["outbox_id"]
    processed = process_outbox()
    assert any(item["id"] == outbox_id and item["status"] == "retry" for item in processed)
    with get_connection() as conn:
        outbox = fetch_one(conn, "SELECT status, governance_json FROM outbox_messages WHERE id = ?", (outbox_id,))
    governance = __import__("json").loads(outbox["governance_json"])
    assert outbox["status"] == "retry"
    assert governance["reason_code"] == "rate_limit_per_second_exceeded"
    assert governance["business_profile"]["verification_status"] == "unverified"



def test_whatsapp_quality_webhook_pauses_bot_on_red() -> None:
    _ensure_whatsapp_number(phone_number_id="wa_quality_red")
    response = client.post("/webhooks/whatsapp/wa_quality_red/quality", json={"quality_rating": "RED"})
    assert response.status_code == 200
    with get_connection() as conn:
        number = fetch_one(conn, "SELECT quality_rating, quality_status FROM whatsapp_numbers WHERE bot_id = ?", ("bot_activation",))
        bot = fetch_one(conn, "SELECT ai_paused FROM bots WHERE id = ?", ("bot_activation",))
    assert number["quality_rating"] == "RED"
    assert number["quality_status"] == "blocked"
    assert int(bot["ai_paused"] or 0) == 1
