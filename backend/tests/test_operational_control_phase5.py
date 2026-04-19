from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_one, get_connection
from backend.app.main import app
from backend.app.utils import utcnow_iso
from backend.tests.test_activation_foundations import _auth_headers
from backend.worker import process_due_jobs

client = TestClient(app)


def test_reschedule_batch_preview_and_execute_with_capacity_matching() -> None:
    headers = _auth_headers()
    with get_connection() as conn:
        execute(
            conn,
            "INSERT OR REPLACE INTO agenda_resources (id, organization_id, bot_id, name, resource_type, branch, status, metadata_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'active', '{}', ?, ?, ?)",
            ("ares_phase5", "org_activation", "bot_activation", "Cabina 1", "room", "Centro", "usr_activation", utcnow_iso(), utcnow_iso()),
        )
        execute(
            conn,
            "DELETE FROM agenda_resource_capacity_rules WHERE id = ?",
            ("acap_phase5",),
        )
        execute(
            conn,
            "INSERT INTO agenda_resource_capacity_rules (id, organization_id, bot_id, resource_id, day_of_week, start_time, end_time, slot_capacity, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)",
            ("acap_phase5", "org_activation", "bot_activation", "ares_phase5", 5, "09:00", "11:00", 1, "usr_activation", utcnow_iso(), utcnow_iso()),
        )
        execute(
            conn,
            "INSERT OR REPLACE INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, external_id, provider, provider_payload_json, integration_id, synced_at, reminder_scheduled_at, confirmed_at, cancelled_at, no_show_at, followup_status, followup_sent_at, rescheduled_from_appointment_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 30, ?, NULL, NULL, 'waos', '{}', NULL, NULL, NULL, NULL, NULL, NULL, 'pending', NULL, NULL, ?, ?)",
            ("apt_phase5_a", "org_activation", "bot_activation", "conv_activation", "ct_activation", "2026-04-17T10:00:00Z", "scheduled", "America/Mexico_City", utcnow_iso(), utcnow_iso()),
        )
        execute(
            conn,
            "INSERT OR REPLACE INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, external_id, provider, provider_payload_json, integration_id, synced_at, reminder_scheduled_at, confirmed_at, cancelled_at, no_show_at, followup_status, followup_sent_at, rescheduled_from_appointment_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 30, ?, NULL, NULL, 'waos', '{}', NULL, NULL, NULL, NULL, NULL, NULL, 'pending', NULL, NULL, ?, ?)",
            ("apt_phase5_b", "org_activation", "bot_activation", "conv_activation", "ct_activation", "2026-04-17T10:30:00Z", "scheduled", "America/Mexico_City", utcnow_iso(), utcnow_iso()),
        )
        conn.commit()

    preview = client.post(
        "/api/v1/client/operations/reschedule-batches/preview",
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "scope_day": "tomorrow",
            "target_date": "2026-04-18",
            "target_start_time": "09:00",
            "target_end_time": "11:00",
            "strategy": "next_available_window",
            "delay_minutes": 30,
            "notify_clients": True,
        },
        headers=headers,
    )
    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["impact"]["appointments_affected"] >= 2
    assert preview_payload["impact"]["planned"] >= 2

    execute_resp = client.post(
        "/api/v1/client/operations/reschedule-batches/execute",
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "scope_day": "tomorrow",
            "target_date": "2026-04-18",
            "target_start_time": "09:00",
            "target_end_time": "11:00",
            "strategy": "next_available_window",
            "delay_minutes": 30,
            "notify_clients": True,
            "confirm_large_impact": True,
        },
        headers=headers,
    )
    assert execute_resp.status_code == 200
    data = execute_resp.json()
    assert data["status"] in {"awaiting_confirmation", "executed"}
    if data["status"] == "awaiting_confirmation":
        confirmed = client.post(
            f"/api/v1/client/operations/commands/{data['id']}/confirm",
            json={"confirmation_code": data["confirmation_code"]},
            headers=headers,
        )
        assert confirmed.status_code == 200
    with get_connection() as conn:
        moved = fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", ("apt_phase5_a",))
        moved_b = fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", ("apt_phase5_b",))
        assert str(moved["scheduled_for"]).startswith("2026-04-18T")
        assert str(moved_b["scheduled_for"]).startswith("2026-04-18T")
        batch = fetch_one(conn, "SELECT * FROM mass_reschedule_batches ORDER BY created_at DESC LIMIT 1")
        assert batch is not None


def test_worker_executes_scheduled_operational_state_transition() -> None:
    headers = _auth_headers()
    with get_connection() as conn:
        execute(conn, "UPDATE bots SET operational_state = 'paused', ai_paused = 1, status = 'active', updated_at = ? WHERE id = ?", (utcnow_iso(), "bot_activation"))
        conn.commit()

    created = client.post(
        "/api/v1/client/operations/commands",
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "text": "reactívalo mañana a las 8 am",
            "source_channel": "portal",
            "dry_run": False,
        },
        headers=headers,
    )
    assert created.status_code == 200
    with get_connection() as conn:
        job = fetch_one(conn, "SELECT * FROM automation_jobs WHERE job_type = 'operational_state_transition_execute' ORDER BY created_at DESC LIMIT 1")
        action = fetch_one(conn, "SELECT * FROM scheduled_operational_actions ORDER BY created_at DESC LIMIT 1")
        assert job is not None
        assert action is not None
        execute(conn, "UPDATE automation_jobs SET scheduled_for = ?, status = 'queued' WHERE id = ?", (utcnow_iso(), job["id"]))
        execute(conn, "UPDATE scheduled_operational_actions SET execute_at = ? WHERE id = ?", (utcnow_iso(), action["id"]))
        conn.commit()

    processed = process_due_jobs()
    assert any(item.get("kind") == "operational_state_transition_execute" for item in processed)
    with get_connection() as conn:
        bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ?", ("bot_activation",))
        action = fetch_one(conn, "SELECT * FROM scheduled_operational_actions ORDER BY created_at DESC LIMIT 1")
        assert bot["operational_state"] == "active"
        assert int(bot["ai_paused"] or 0) == 0
        assert action["status"] == "executed"


def test_authorized_number_restricted_by_allowed_intents() -> None:
    headers = _auth_headers()
    number = client.post(
        "/api/v1/client/operations/authorized-numbers",
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "phone_e164": "+5215557770001",
            "role": "manager",
            "allowed_intents": ["bot.status_query"],
            "scope": {},
            "status": "verified",
        },
        headers=headers,
    )
    assert number.status_code == 200

    simulate = client.post(
        "/api/v1/simulate/inbound",
        json={
            "bot_id": "bot_activation",
            "phone": "+5215557770001",
            "name": "Gerente",
            "body": "apaga el bot",
        },
        headers=headers,
    )
    assert simulate.status_code == 200
    with get_connection() as conn:
        forbidden = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE actor_phone_e164 = ? AND detected_intent = 'bot.shutdown' ORDER BY created_at DESC LIMIT 1", ("+5215557770001",))
        assert forbidden is None
