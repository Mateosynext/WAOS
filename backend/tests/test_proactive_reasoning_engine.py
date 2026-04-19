from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_one, get_connection
from backend.app.main import app
from backend.tests.test_activation_foundations import _auth_headers
from backend.app.utils import utcnow_iso


client = TestClient(app)

PROACTIVE_CONTACT_ID = "ct_proactive_engine"
PROACTIVE_CONVERSATION_ID = "conv_proactive_engine"
PROACTIVE_PAYMENT_ID = "pay_proactive_engine"


def _seed_proactive_entities() -> None:
    _auth_headers()
    with get_connection() as conn:
        if not fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", (PROACTIVE_CONTACT_ID,)):
            execute(
                conn,
                "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES (?, 'org_activation', ?, ?, ?, '[]', ?, ?)",
                (PROACTIVE_CONTACT_ID, "+5215557778888", "Cliente Proactivo", "proactive@example.com", "2026-04-16T09:00:00Z", "2026-04-16T09:00:00Z"),
            )
        if not fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (PROACTIVE_CONVERSATION_ID,)):
            execute(
                conn,
                "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, 'open', 0, 1, NULL, NULL, ?, NULL, NULL, NULL, ?, ?)",
                (PROACTIVE_CONVERSATION_ID, PROACTIVE_CONTACT_ID, "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z"),
            )
        if not fetch_one(conn, "SELECT * FROM crm_leads WHERE contact_id = ? AND bot_id = ?", (PROACTIVE_CONTACT_ID, "bot_activation")):
            execute(
                conn,
                """INSERT INTO crm_leads (id, organization_id, bot_id, conversation_id, contact_id, stage, estimated_amount, owner_user_id, next_action, followup_at, tags_json, notes, lost_reason, language, source_channel, source_campaign, pipeline_json, score_buying_intent, close_probability, detected_objections_json, best_next_action, temperature_status, last_qualification_at, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, ?, 'propuesta', 1800, 'usr_activation', 'Cobrar hoy', ?, '[]', '', NULL, 'es', 'whatsapp', 'organico', '{}', 88, 80, '[]', 'Enviar link de pago', 'hot', ?, ?, ?)""",
                ("lead_proactive_engine", PROACTIVE_CONVERSATION_ID, PROACTIVE_CONTACT_ID, "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z"),
            )
        payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (PROACTIVE_PAYMENT_ID,))
        if payment:
            execute(conn, "DELETE FROM commerce_payments WHERE id = ?", (PROACTIVE_PAYMENT_ID,))
        execute(
            conn,
            "INSERT INTO commerce_payments (id, organization_id, bot_id, conversation_id, contact_id, crm_lead_id, title, amount, currency, status, payment_link_url, payment_link_status, reminder_scheduled_at, confirmed_at, receipt_sent_at, cart_recovery_status, send_receipt_on_confirm, metadata_json, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, ?, 'lead_proactive_engine', 'Pago de anticipo', 900, 'MXN', 'pending', NULL, 'generated', NULL, NULL, NULL, 'inactive', 1, '{}', ?, ?)",
            (PROACTIVE_PAYMENT_ID, PROACTIVE_CONVERSATION_ID, PROACTIVE_CONTACT_ID, "2026-04-16T08:00:00Z", "2026-04-16T08:00:00Z"),
        )
        execute(conn, "DELETE FROM proactive_playbook_runs WHERE contact_id = ?", (PROACTIVE_CONTACT_ID,))
        execute(conn, "DELETE FROM proactive_contact_candidates WHERE contact_id = ?", (PROACTIVE_CONTACT_ID,))
        execute(conn, "DELETE FROM proactive_signal_events WHERE contact_id = ?", (PROACTIVE_CONTACT_ID,))
        conn.commit()



def test_proactive_engine_scores_candidates_materializes_playbook_and_feeds_outcomes() -> None:
    headers = _auth_headers()
    _seed_proactive_entities()

    evaluate = client.post(
        "/api/v1/proactive-engine/evaluate",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "contact_ids": [PROACTIVE_CONTACT_ID],
            "persist": True,
            "include_suppressed": True,
        },
    )
    assert evaluate.status_code == 200
    payload = evaluate.json()["data"]
    assert payload["engine_version"] == "proactive_reasoning_v1"
    assert payload["count"] >= 1
    candidate = next(item for item in payload["items"] if item["signal_key"] == "payment_pending")
    assert candidate["eligible"] is True
    assert candidate["specialist_agent_key"] == "collections"
    assert candidate["recommended_action"] == "create_payment_link"
    assert candidate["playbook_id"] == "playbook_pending_payment_followup"
    assert "link de cobro" in candidate["message_text"].lower()

    materialize = client.post(
        f"/api/v1/proactive-engine/candidates/{candidate['id']}/materialize",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "record_exposure": True,
        },
    )
    assert materialize.status_code == 200
    materialized = materialize.json()["data"]
    assert materialized["run"]["playbook_id"] == "playbook_pending_payment_followup"
    assert materialized["run"]["status"] == "materialized"
    assert materialized["exposure"]["playbook_id"] == "playbook_pending_payment_followup"

    paid = client.post(
        "/api/v1/outcomes/events",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": PROACTIVE_CONVERSATION_ID,
            "contact_id": PROACTIVE_CONTACT_ID,
            "payment_id": PROACTIVE_PAYMENT_ID,
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

    score = client.get(
        "/api/v1/outcomes/scorecards",
        headers=headers,
        params={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "entity_type": "playbook",
            "entity_id": "playbook_pending_payment_followup",
            "scorecard_window": "28d",
        },
    )
    assert score.status_code == 200
    item = score.json()["data"]["items"][0]
    assert item["entity_id"] == "playbook_pending_payment_followup"
    assert item["metrics"]["revenue_sum"] >= 900.0
    assert item["metrics"]["by_event"]["payment_completed"] >= 1

    rerun = client.post(
        "/api/v1/proactive-engine/evaluate",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "contact_ids": [PROACTIVE_CONTACT_ID],
            "persist": True,
            "include_suppressed": True,
        },
    )
    assert rerun.status_code == 200
    rerun_candidate = next(item for item in rerun.json()["data"]["items"] if item["signal_key"] == "payment_pending")
    assert rerun_candidate["eligible"] is False
    assert rerun_candidate["suppression_reason"] == "objective_already_touched_24h"

    runs = client.get(
        "/api/v1/proactive-engine/runs",
        headers=headers,
        params={"organization_id": "org_activation", "bot_id": "bot_activation"},
    )
    assert runs.status_code == 200
    assert any(item["candidate_id"] == candidate["id"] for item in runs.json()["data"]["items"])
