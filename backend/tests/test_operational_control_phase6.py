from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.application.operational_control_service import operational_control_service
from backend.app.db import execute, fetch_one, get_connection
from backend.app.main import app
from backend.app.utils import utcnow_iso
from backend.tests.test_activation_foundations import _auth_headers

client = TestClient(app)


def test_whatsapp_scope_enforcement_filters_impacted_appointments() -> None:
    headers = _auth_headers()
    client.get("/healthz" if False else "/openapi.json")
    with get_connection() as conn:
        execute(conn, "INSERT OR REPLACE INTO agenda_resources (id, organization_id, bot_id, name, resource_type, branch, status, metadata_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'active', '{}', ?, ?, ?)", ("ares_scope_centro", "org_activation", "bot_activation", "Dra. Centro", "professional", "Centro", "usr_activation", utcnow_iso(), utcnow_iso()))
        execute(conn, "INSERT OR REPLACE INTO agenda_resources (id, organization_id, bot_id, name, resource_type, branch, status, metadata_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'active', '{}', ?, ?, ?)", ("ares_scope_norte", "org_activation", "bot_activation", "Dra. Norte", "professional", "Norte", "usr_activation", utcnow_iso(), utcnow_iso()))
        execute(conn, "INSERT OR REPLACE INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, provider_payload_json, followup_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'scheduled', 30, ?, NULL, '{}', 'pending', ?, ?)", ("apt_scope_centro", "org_activation", "bot_activation", None, None, "2026-04-17T10:00:00Z", "America/Mexico_City", utcnow_iso(), utcnow_iso()))
        execute(conn, "INSERT OR REPLACE INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, provider_payload_json, followup_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'scheduled', 30, ?, NULL, '{}', 'pending', ?, ?)", ("apt_scope_norte", "org_activation", "bot_activation", None, None, "2026-04-17T11:00:00Z", "America/Mexico_City", utcnow_iso(), utcnow_iso()))
        execute(conn, "INSERT OR REPLACE INTO appointment_resource_assignments (id, organization_id, appointment_id, resource_id, assigned_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", ("aras_scope_centro", "org_activation", "apt_scope_centro", "ares_scope_centro", "usr_activation", utcnow_iso(), utcnow_iso()))
        execute(conn, "INSERT OR REPLACE INTO appointment_resource_assignments (id, organization_id, appointment_id, resource_id, assigned_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", ("aras_scope_norte", "org_activation", "apt_scope_norte", "ares_scope_norte", "usr_activation", utcnow_iso(), utcnow_iso()))
        execute(conn, "DELETE FROM authorized_operational_numbers WHERE phone_e164 = ?", ("+5215557776600",))
        execute(conn, "INSERT INTO authorized_operational_numbers (id, organization_id, bot_id, phone_e164, role, allowed_intents_json, scope_json, status, verified_at, last_used_at, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, 'manager', '[]', ?, 'verified', ?, NULL, ?, ?, ?)", ("opnum_scope", "org_activation", "bot_activation", "+5215557776600", '{"branches": ["Centro"]}', utcnow_iso(), "usr_activation", utcnow_iso(), utcnow_iso()))
        conn.commit()
        result = operational_control_service.handle_chat_command(conn, bot_id="bot_activation", phone="+5215557776600", body="qué citas se verían afectadas si cierro mañana", conversation_id="conv_activation", contact_id="ct_activation")
        assert result is not None
        assert result["handled"] is True
        command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE actor_phone_e164 = ? ORDER BY created_at DESC LIMIT 1", ("+5215557776600",))
        impact = operational_control_service._json(command.get("result_json"), {}).get("impact") or {}
        assert impact.get("appointments_affected") == 1
        assert impact.get("appointment_ids") == ["apt_scope_centro"]


def test_whatsapp_operational_rate_limit_creates_alert() -> None:
    with get_connection() as conn:
        execute(conn, "DELETE FROM authorized_operational_numbers WHERE phone_e164 = ?", ("+5215557776601",))
        execute(conn, "INSERT INTO authorized_operational_numbers (id, organization_id, bot_id, phone_e164, role, allowed_intents_json, scope_json, status, verified_at, last_used_at, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, 'owner', '[]', '{}', 'verified', ?, NULL, ?, ?, ?)", ("opnum_rate", "org_activation", "bot_activation", "+5215557776601", utcnow_iso(), "usr_activation", utcnow_iso(), utcnow_iso()))
        conn.commit()
        last = None
        for _ in range(9):
            last = operational_control_service.handle_chat_command(conn, bot_id="bot_activation", phone="+5215557776601", body="estado del bot", conversation_id="conv_activation", contact_id="ct_activation")
        assert last is not None
        assert last["status"] == "rate_limited"
        alert = fetch_one(conn, "SELECT * FROM operational_command_alerts WHERE bot_id = ? AND alert_type = 'rate_limit' ORDER BY created_at DESC LIMIT 1", ("bot_activation",))
        assert alert is not None


def test_undo_reschedule_restores_appointment_and_marks_reverted() -> None:
    headers = _auth_headers()
    with get_connection() as conn:
        execute(conn, "INSERT OR REPLACE INTO agenda_resources (id, organization_id, bot_id, name, resource_type, branch, status, metadata_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'active', '{}', ?, ?, ?)", ("ares_phase6", "org_activation", "bot_activation", "Cabina 6", "room", "Centro", "usr_activation", utcnow_iso(), utcnow_iso()))
        execute(conn, "DELETE FROM agenda_resource_capacity_rules WHERE id = ?", ("acap_phase6",))
        execute(conn, "INSERT INTO agenda_resource_capacity_rules (id, organization_id, bot_id, resource_id, day_of_week, start_time, end_time, slot_capacity, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)", ("acap_phase6", "org_activation", "bot_activation", "ares_phase6", 5, "09:00", "11:00", 1, "usr_activation", utcnow_iso(), utcnow_iso()))
        execute(conn, "INSERT OR REPLACE INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, external_id, provider, provider_payload_json, integration_id, synced_at, reminder_scheduled_at, confirmed_at, cancelled_at, no_show_at, followup_status, followup_sent_at, rescheduled_from_appointment_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'scheduled', 30, ?, NULL, NULL, 'waos', '{}', NULL, NULL, NULL, NULL, NULL, NULL, 'pending', NULL, NULL, ?, ?)", ("apt_phase6_a", "org_activation", "bot_activation", "conv_activation", "ct_activation", "2026-04-17T10:00:00Z", "America/Mexico_City", utcnow_iso(), utcnow_iso()))
        conn.commit()

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
            "notify_clients": False,
            "confirm_large_impact": True,
        },
        headers=headers,
    )
    assert execute_resp.status_code == 200
    data = execute_resp.json()
    if data["status"] == "awaiting_confirmation":
        confirmed = client.post(
            f"/api/v1/client/operations/commands/{data['id']}/confirm",
            json={"confirmation_code": data["confirmation_code"]},
            headers=headers,
        )
        assert confirmed.status_code == 200
        data = confirmed.json()
    assert data["status"] == "executed"
    command_id = data["id"]
    with get_connection() as conn:
        moved = fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", ("apt_phase6_a",))
        assert str(moved["scheduled_for"]).startswith("2026-04-18T")

    undone = client.post(
        f"/api/v1/client/operations/commands/{command_id}/undo",
        json={"reason": "undo_from_test"},
        headers=headers,
    )
    assert undone.status_code == 200
    with get_connection() as conn:
        restored = fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", ("apt_phase6_a",))
        command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,))
        assert str(restored["scheduled_for"]).startswith("2026-04-17T10:00:00")
        assert command["status"] in {"reverted", "partially_reverted"}
