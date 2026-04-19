from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.agent_runtime import orchestrate_runtime_turn
from backend.app.db import execute, fetch_one, get_connection
from backend.app.main import app
from backend.tests.test_activation_foundations import _auth_headers


client = TestClient(app)


ROUTE_CONTACT_ID = "ct_multi_agent"
ROUTE_CONVERSATION_ID = "conv_multi_agent"
ROUTE_PAYMENT_ID = "pay_multi_agent"


def _seed_route_entities() -> None:
    _auth_headers()
    with get_connection() as conn:
        if not fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", (ROUTE_CONTACT_ID,)):
            execute(
                conn,
                "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES (?, 'org_activation', ?, ?, ?, '[]', ?, ?)",
                (ROUTE_CONTACT_ID, "+5215551234444", "Cliente Multi Agent", "multi-agent@example.com", "2026-04-17T19:40:00Z", "2026-04-17T19:40:00Z"),
            )
        if not fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (ROUTE_CONVERSATION_ID,)):
            execute(
                conn,
                "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, 'open', 0, 1, NULL, NULL, ?, NULL, NULL, NULL, ?, ?)",
                (ROUTE_CONVERSATION_ID, ROUTE_CONTACT_ID, "2026-04-17T19:40:00Z", "2026-04-17T19:40:00Z", "2026-04-17T19:40:00Z"),
            )
        if not fetch_one(conn, "SELECT * FROM messages WHERE id = ?", ("msg_multi_agent",)):
            execute(
                conn,
                "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES ('msg_multi_agent', 'org_activation', ?, ?, 'bot_activation', 'inbound', 'text', 'whatsapp', ?, NULL, 'received', '{}', ?)",
                (ROUTE_CONVERSATION_ID, ROUTE_CONTACT_ID, "Quiero pagar el anticipo hoy, mándame el link de cobro", "2026-04-17T19:40:00Z"),
            )
        if not fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (ROUTE_PAYMENT_ID,)):
            execute(
                conn,
                "INSERT INTO commerce_payments (id, organization_id, bot_id, conversation_id, contact_id, crm_lead_id, title, amount, currency, status, payment_link_url, payment_link_status, reminder_scheduled_at, confirmed_at, receipt_sent_at, cart_recovery_status, send_receipt_on_confirm, metadata_json, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, ?, NULL, 'Anticipo', 500, 'MXN', 'pending', NULL, 'generated', NULL, NULL, NULL, 'inactive', 1, '{}', ?, ?)",
                (ROUTE_PAYMENT_ID, ROUTE_CONVERSATION_ID, ROUTE_CONTACT_ID, "2026-04-17T19:40:00Z", "2026-04-17T19:40:00Z"),
            )
        conn.commit()


def _bot_config() -> dict:
    return {
        "identity": {"business_name": "WAOS Clinic", "language": "es"},
        "business_knowledge": {
            "services": ["Consulta", "Seguimiento"],
            "prices": [{"name": "Consulta", "price": "$799 MXN"}],
            "hours": "Lunes a viernes de 9:00 a 18:00",
        },
        "objective": {"primary": "close_more"},
        "personality": {"tone": "clear"},
        "rules": {},
        "handoff": {"sensitive_keywords": ["humano", "asesor"]},
    }


def test_orchestrate_runtime_turn_routes_to_specialist_agent_and_supervisor() -> None:
    result = orchestrate_runtime_turn(
        text="Necesito reagendar mi cita para mañana en la tarde",
        conversation={"id": "conv_1", "status": "open", "human_takeover": 0, "ai_active": 1},
        bot={"id": "bot_1", "status": "active", "ai_paused": 0},
        memory={"lead_stage": "contacted", "lead_score": 30},
        bot_config=_bot_config(),
        recent_messages=[],
        conn=None,
        organization_id=None,
        bot_id="bot_1",
        contact_id="ct_1",
        conversation_id="conv_1",
        recent_voice_notes=[],
        language_config={"default_language": "es", "supported_languages": ["es", "en"]},
    )
    assert result["specialist_route"]["specialist_agent_key"] == "booking"
    assert result["plan"]["specialist"]["agent_key"] == "booking"
    assert "reschedule" in result["plan"]["specialist"]["allowed_tools"]
    assert result["supervisor"]["approved_specialist_agent"] == "booking"
    assert result["decision"]["specialist_agent"] == "booking"
    assert result["shared_memory"]["memory_version"] == "shared_memory_v1"


def test_agent_orchestration_route_persists_history_records_exposure_and_feeds_scorecards() -> None:
    headers = _auth_headers()
    _seed_route_entities()

    route = client.post(
        "/api/v1/agent-orchestration/route",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": ROUTE_CONVERSATION_ID,
            "contact_id": ROUTE_CONTACT_ID,
            "text": "Quiero pagar el anticipo hoy, mándame el link de cobro",
            "persist": True,
            "record_exposure": True,
        },
    )
    assert route.status_code == 200
    route_data = route.json()["data"]
    assert route_data["route"]["specialist_agent_key"] == "collections"
    assert route_data["route_run"]["specialist_agent_key"] == "collections"
    assert route_data["exposure"]["specialist_agent_key"] == "collections"

    paid = client.post(
        "/api/v1/outcomes/events",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": ROUTE_CONVERSATION_ID,
            "contact_id": ROUTE_CONTACT_ID,
            "payment_id": ROUTE_PAYMENT_ID,
            "event_name": "payment_completed",
            "event_category": "payment",
            "event_timestamp": "2026-04-17T20:00:00Z",
            "source_system": "payments",
            "value_number": 500.0,
            "vertical": "fitness",
            "funnel_stage": "payment",
        },
    )
    assert paid.status_code == 200

    recompute = client.post(
        "/api/v1/outcomes/recompute",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "windows": ["28d"],
            "attribution_window_hours": 168,
        },
    )
    assert recompute.status_code == 200

    scorecards = client.get(
        "/api/v1/outcomes/scorecards",
        headers=headers,
        params={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "entity_type": "specialist_agent",
            "entity_id": "collections",
            "scorecard_window": "28d",
        },
    )
    assert scorecards.status_code == 200
    item = scorecards.json()["data"]["items"][0]
    assert item["entity_id"] == "collections"
    assert item["metrics"]["revenue_sum"] >= 500.0

    overview = client.get(f"/api/v1/agent-orchestration/conversations/{ROUTE_CONVERSATION_ID}", headers=headers)
    assert overview.status_code == 200
    payload = overview.json()["data"]
    assert payload["latest_route"]["specialist_agent_key"] == "collections"
    assert payload["latest_scorecard"]["entity_id"] == "collections"
