from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.tests.test_activation_foundations import _auth_headers


client = TestClient(app)


def test_tool_execution_runs_feed_outcomes_and_scorecards_automatically() -> None:
    headers = _auth_headers()

    booking = client.post(
        "/api/v1/tool-executions/execute",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "action": "book_appointment",
            "confirm": True,
            "payload": {
                "conversation_id": "conv_activation",
                "contact_id": "ct_activation",
                "scheduled_for": "2026-04-24T18:00:00Z",
                "duration_minutes": 30,
                "notes": "Flywheel booking",
            },
            "metadata": {"prompt_run_id": "prun_flywheel_1", "flow_id": "flow_flywheel_1"},
        },
    )
    assert booking.status_code == 200
    booking_data = booking.json()["data"]
    appointment_id = booking_data["result"]["appointment"]["id"]
    booking_run_id = booking_data["execution"]["id"]
    assert booking_data["result"]["closed_loop"]["event_name"] == "appointment_scheduled"

    attended = client.post(
        "/api/v1/outcomes/events",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": "conv_activation",
            "contact_id": "ct_activation",
            "appointment_id": appointment_id,
            "event_name": "appointment_attended",
            "event_category": "appointment",
            "event_timestamp": "2026-04-24T18:45:00Z",
            "source_system": "calendar",
            "vertical": "fitness",
            "funnel_stage": "appointment",
        },
    )
    assert attended.status_code == 200

    stage = client.post(
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
                "estimated_amount": 2300,
                "next_action": "Cobrar anticipo",
            },
        },
    )
    assert stage.status_code == 200
    assert stage.json()["data"]["result"]["closed_loop"]["event_name"] == "lead_stage_progressed"

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
                "title": "Flywheel pago",
                "amount": 1250,
                "currency": "MXN",
                "appointment_id": appointment_id,
            },
        },
    )
    assert payment_link.status_code == 200
    payment_data = payment_link.json()["data"]
    payment_id = payment_data["result"]["payment"]["id"]
    assert payment_data["result"]["closed_loop"]["event_name"] == "payment_started"

    paid = client.post(
        "/api/v1/outcomes/events",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": "conv_activation",
            "contact_id": "ct_activation",
            "appointment_id": appointment_id,
            "payment_id": payment_id,
            "event_name": "payment_completed",
            "event_category": "payment",
            "event_timestamp": "2026-04-24T19:00:00Z",
            "source_system": "payments",
            "value_number": 1250.0,
            "vertical": "fitness",
            "funnel_stage": "payment",
        },
    )
    assert paid.status_code == 200

    action_score = client.get(
        "/api/v1/outcomes/scorecards",
        headers=headers,
        params={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "entity_type": "tool_action",
            "entity_id": "create_payment_link",
            "scorecard_window": "28d",
        },
    )
    assert action_score.status_code == 200
    item = action_score.json()["data"]["items"][0]
    assert item["entity_id"] == "create_payment_link"
    assert item["metrics"]["revenue_sum"] >= 1250.0
    assert item["metrics"]["by_event"]["payment_completed"] >= 1

    book_score = client.get(
        "/api/v1/outcomes/scorecards",
        headers=headers,
        params={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "entity_type": "tool_action",
            "entity_id": "book_appointment",
            "scorecard_window": "28d",
        },
    )
    assert book_score.status_code == 200
    book_item = book_score.json()["data"]["items"][0]
    assert book_item["metrics"]["by_event"]["appointment_attended"] >= 1

    run_detail = client.get(f"/api/v1/tool-executions/runs/{booking_run_id}", headers=headers)
    assert run_detail.status_code == 200
    closed_loop = run_detail.json()["data"]["closed_loop"]
    assert closed_loop["exposure"]["tool_action"] == "book_appointment"
    assert any(item["event_name"] == "appointment_attended" for item in closed_loop["linked_attribution"])
    assert closed_loop["action_scorecard"]["entity_id"] == "book_appointment"
