from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_one, get_connection
from backend.app.main import app
from backend.app.utils import utcnow_iso
from backend.tests.test_activation_foundations import _auth_headers
from backend.tests.test_proactive_reasoning_engine import _seed_proactive_entities

client = TestClient(app)

GROWTH_CONTACT_ID = "ct_growth_os"
GROWTH_CONVERSATION_ID = "conv_growth_os"
GROWTH_PAYMENT_ID = "pay_growth_os"
GROWTH_LEAD_ID = "lead_growth_os"


def _seed_growth_target() -> None:
    _auth_headers()
    with get_connection() as conn:
        if not fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", (GROWTH_CONTACT_ID,)):
            execute(
                conn,
                "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES (?, 'org_activation', ?, ?, ?, '[]', ?, ?)",
                (GROWTH_CONTACT_ID, "+5215559991111", "Cliente Growth", "growth@example.com", "2026-04-16T09:00:00Z", "2026-04-16T09:00:00Z"),
            )
        if not fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (GROWTH_CONVERSATION_ID,)):
            execute(
                conn,
                "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, 'open', 0, 1, NULL, NULL, ?, NULL, NULL, NULL, ?, ?)",
                (GROWTH_CONVERSATION_ID, GROWTH_CONTACT_ID, "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z"),
            )
        if not fetch_one(conn, "SELECT * FROM crm_leads WHERE id = ?", (GROWTH_LEAD_ID,)):
            execute(
                conn,
                """INSERT INTO crm_leads (id, organization_id, bot_id, conversation_id, contact_id, stage, estimated_amount, owner_user_id, next_action, followup_at, tags_json, notes, lost_reason, language, source_channel, source_campaign, pipeline_json, score_buying_intent, close_probability, detected_objections_json, best_next_action, temperature_status, last_qualification_at, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, ?, 'propuesta', 2500, 'usr_activation', 'Cobrar', ?, '[]', '', NULL, 'es', 'whatsapp', 'organico', '{}', 90, 85, '[]', 'Enviar link de pago', 'hot', ?, ?, ?)""",
                (GROWTH_LEAD_ID, GROWTH_CONVERSATION_ID, GROWTH_CONTACT_ID, "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z"),
            )
        payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (GROWTH_PAYMENT_ID,))
        if payment:
            execute(conn, "DELETE FROM commerce_payments WHERE id = ?", (GROWTH_PAYMENT_ID,))
        execute(
            conn,
            "INSERT INTO commerce_payments (id, organization_id, bot_id, conversation_id, contact_id, crm_lead_id, title, amount, currency, status, payment_link_url, payment_link_status, reminder_scheduled_at, confirmed_at, receipt_sent_at, cart_recovery_status, send_receipt_on_confirm, metadata_json, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, ?, ?, 'Pago Growth', 1200, 'MXN', 'pending', NULL, 'generated', NULL, NULL, NULL, 'inactive', 1, '{}', ?, ?)",
            (GROWTH_PAYMENT_ID, GROWTH_CONVERSATION_ID, GROWTH_CONTACT_ID, GROWTH_LEAD_ID, "2026-04-16T08:00:00Z", "2026-04-16T08:00:00Z"),
        )
        execute(conn, "DELETE FROM proactive_playbook_runs WHERE contact_id = ?", (GROWTH_CONTACT_ID,))
        execute(conn, "DELETE FROM proactive_contact_candidates WHERE contact_id = ?", (GROWTH_CONTACT_ID,))
        execute(conn, "DELETE FROM proactive_signal_events WHERE contact_id = ?", (GROWTH_CONTACT_ID,))
        conn.commit()


def test_growth_os_prioritizes_and_materializes_growth_targets() -> None:
    headers = _auth_headers()
    _seed_proactive_entities()
    _seed_growth_target()

    evaluate = client.post(
        "/api/v1/proactive-engine/evaluate",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "contact_ids": ["ct_proactive_engine"],
            "persist": True,
            "include_suppressed": True,
        },
    )
    candidate = next(item for item in evaluate.json()["data"]["items"] if item["signal_key"] == "payment_pending")
    materialize = client.post(
        f"/api/v1/proactive-engine/candidates/{candidate['id']}/materialize",
        headers=headers,
        json={"organization_id": "org_activation", "record_exposure": True},
    )
    assert materialize.status_code == 200
    paid = client.post(
        "/api/v1/outcomes/events",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": "conv_proactive_engine",
            "contact_id": "ct_proactive_engine",
            "payment_id": "pay_proactive_engine",
            "event_name": "payment_completed",
            "event_category": "payment",
            "event_timestamp": utcnow_iso(),
            "source_system": "payments",
            "value_number": 900.0,
            "vertical": "fitness",
            "funnel_stage": "payment",
        },
    )
    assert paid.status_code == 200

    run = client.post(
        "/api/v1/growth-os/run",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "goals": ["payments"],
            "mode": "autopilot",
            "auto_execute": True,
            "max_targets": 3,
        },
    )
    assert run.status_code == 200, run.text
    data = run.json()["data"]
    assert data["selected_count"] >= 1
    assert data["materialized_count"] >= 1
    target = data["run"]["targets"][0]
    assert target["goal"] == "payments"
    assert target["specialist_agent_key"] == "collections"
    assert target["status"] == "executed"
    assert target["scorecard"]["playbook"] is not None

    overview = client.get(
        "/api/v1/growth-os/overview",
        headers=headers,
        params={"organization_id": "org_activation", "bot_id": "bot_activation"},
    )
    assert overview.status_code == 200
    overview_data = overview.json()["data"]
    assert overview_data["engine_version"] == "growth_os_v1"
    assert overview_data["latest_run"] is not None
    assert overview_data["goal_distribution"]["payments"] >= 1
