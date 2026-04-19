from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import fetch_one, get_connection
from backend.app.main import app
from backend.tests.test_activation_foundations import _auth_headers


client = TestClient(app)


def test_tool_execution_native_preview_execute_idempotency_and_logs() -> None:
    headers = _auth_headers()

    preview = client.post(
        "/api/v1/tool-executions/preview",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "action": "book_appointment",
            "payload": {
                "conversation_id": "conv_activation",
                "contact_id": "ct_activation",
                "scheduled_for": "2026-04-21T18:00:00Z",
                "duration_minutes": 45,
                "notes": "Tool execution native booking",
            },
            "metadata": {"prompt_run_id": "prun_exec_1", "flow_id": "flow_exec_1"},
        },
    )
    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    preview_run_id = preview_data["execution"]["id"]
    confirmation_token = preview_data["confirmation_token"]
    assert preview_data["execution"]["status"] == "preview_ready"
    assert preview_data["preview"]["adapter_key"] == "waos_calendar"

    execute_booking = client.post(
        "/api/v1/tool-executions/execute",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "action": "book_appointment",
            "preview_execution_id": preview_run_id,
            "confirmation_token": confirmation_token,
            "idempotency_key": "tool-book-activation-1",
            "payload": {
                "conversation_id": "conv_activation",
                "contact_id": "ct_activation",
                "scheduled_for": "2026-04-21T18:00:00Z",
                "duration_minutes": 45,
                "notes": "Tool execution native booking",
            },
        },
    )
    assert execute_booking.status_code == 200
    booking_payload = execute_booking.json()["data"]
    appointment_id = booking_payload["result"]["appointment"]["id"]
    assert booking_payload["execution"]["status"] == "completed"
    assert booking_payload["result"]["appointment"]["scheduled_for"] == "2026-04-21T18:00:00Z"

    duplicate_booking = client.post(
        "/api/v1/tool-executions/execute",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "action": "book_appointment",
            "confirm": True,
            "idempotency_key": "tool-book-activation-1",
            "payload": {
                "conversation_id": "conv_activation",
                "contact_id": "ct_activation",
                "scheduled_for": "2026-04-21T18:00:00Z",
                "duration_minutes": 45,
                "notes": "Tool execution native booking",
            },
        },
    )
    assert duplicate_booking.status_code == 200
    duplicate_payload = duplicate_booking.json()["data"]
    assert duplicate_payload["idempotent"] is True

    stage_update = client.post(
        "/api/v1/tool-executions/execute",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "action": "update_contact_stage",
            "confirm": True,
            "payload": {
                "contact_id": "ct_activation",
                "conversation_id": "conv_activation",
                "stage": "propuesta",
                "estimated_amount": 1500,
                "next_action": "Enviar link de pago",
                "notes": "Lead listo para cobrar",
            },
        },
    )
    assert stage_update.status_code == 200
    assert stage_update.json()["data"]["result"]["lead"]["stage"] == "propuesta"

    payment_link = client.post(
        "/api/v1/tool-executions/execute",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "action": "create_payment_link",
            "confirm": True,
            "payload": {
                "conversation_id": "conv_activation",
                "contact_id": "ct_activation",
                "title": "Anticipo cirugía",
                "amount": 900,
                "currency": "MXN",
                "appointment_id": appointment_id,
            },
        },
    )
    assert payment_link.status_code == 200
    payment_payload = payment_link.json()["data"]
    payment_id = payment_payload["result"]["payment"]["id"]
    assert payment_payload["result"]["payment"]["checkout_status"] if "checkout_status" in payment_payload["result"]["payment"] else True

    with get_connection() as conn:
        conn.execute("UPDATE commerce_payments SET status = 'paid', payment_link_status = 'paid', confirmed_at = '2026-04-21T18:30:00Z', paid_at = '2026-04-21T18:30:00Z' WHERE id = ?", (payment_id,))
        conn.commit()

    receipt = client.post(
        "/api/v1/tool-executions/execute",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "action": "send_receipt",
            "confirm": True,
            "payload": {
                "payment_id": payment_id,
            },
        },
    )
    assert receipt.status_code == 200
    receipt_payload = receipt.json()["data"]
    assert receipt_payload["result"]["receipt_message"]["id"]

    runs = client.get(
        "/api/v1/tool-executions/runs",
        headers=headers,
        params={"organization_id": "org_activation", "limit": 20},
    )
    assert runs.status_code == 200
    items = runs.json()["data"]["items"]
    assert any(item["action"] == "create_payment_link" for item in items)
    assert any(item["action"] == "send_receipt" for item in items)

    execution_id = payment_payload["execution"]["id"]
    detail = client.get(f"/api/v1/tool-executions/runs/{execution_id}", headers=headers)
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    assert detail_data["action"] == "create_payment_link"
    assert any(step["step_name"] == "adapter.executed" for step in detail_data["steps"])

    with get_connection() as conn:
        appointment = fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))
        run = fetch_one(conn, "SELECT * FROM tool_execution_runs WHERE id = ?", (execution_id,))
        assert appointment is not None
        assert payment is not None
        assert run is not None
        assert run["idempotency_key"] is None or isinstance(run["idempotency_key"], str)
