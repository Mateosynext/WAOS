from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_one, get_connection, init_db
from backend.app.main import app
from backend.app.utils import utcnow_iso
from backend.tests.test_activation_foundations import _auth_headers

client = TestClient(app)


def test_operational_command_preview_and_confirm_flow() -> None:
    headers = _auth_headers()
    preview = client.post(
        "/api/v1/client/operations/commands/preview",
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "text": "qué citas se verían afectadas si cierro mañana",
            "source_channel": "portal",
            "dry_run": True,
        },
        headers=headers,
    )
    assert preview.status_code == 200
    preview_data = preview.json()
    assert preview_data["status"] == "preview"
    assert preview_data["impact"]["appointments_affected"] >= 0

    create = client.post(
        "/api/v1/client/operations/commands",
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "text": "apaga el bot",
            "source_channel": "portal",
            "dry_run": False,
        },
        headers=headers,
    )
    assert create.status_code == 200
    data = create.json()
    assert data["status"] == "awaiting_confirmation"
    assert data["confirmation_code"]

    confirm = client.post(
        f"/api/v1/client/operations/commands/{data['id']}/confirm",
        json={"confirmation_code": data["confirmation_code"]},
        headers=headers,
    )
    assert confirm.status_code == 200
    confirmed = confirm.json()
    assert confirmed["status"] == "executed"
    with get_connection() as conn:
        bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ?", ("bot_activation",))
        assert bot["operational_state"] == "maintenance"
        assert bot["status"] == "inactive"


def test_authorized_number_and_whatsapp_operational_command() -> None:
    headers = _auth_headers()
    number = client.post(
        "/api/v1/client/operations/authorized-numbers",
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "phone_e164": "+5215559990000",
            "role": "owner",
            "allowed_intents": [],
            "scope": {},
            "status": "verified",
        },
        headers=headers,
    )
    assert number.status_code == 200

    with get_connection() as conn:
        execute(
            conn,
            "INSERT OR REPLACE INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, provider_payload_json, followup_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "appt_operational_future",
                "org_activation",
                "bot_activation",
                None,
                None,
                "2099-12-31T15:00:00Z",
                "scheduled",
                60,
                "America/Mexico_City",
                "Operational control test appointment",
                "{}",
                "pending",
                utcnow_iso(),
                utcnow_iso(),
            ),
        )

    simulate = client.post(
        "/api/v1/simulate/inbound",
        json={
            "bot_id": "bot_activation",
            "phone": "+5215559990000",
            "name": "Dueño",
            "body": "tuve una emergencia, avísale a mi próxima cita",
        },
        headers=headers,
    )
    assert simulate.status_code == 200
    payload = simulate.json()["data"]
    assert payload["ai"]["reason"] == "operational_command"
    with get_connection() as conn:
        batch = fetch_one(conn, "SELECT * FROM appointment_notification_batches ORDER BY created_at DESC LIMIT 1")
        assert batch is not None
        targets = conn.execute("SELECT COUNT(*) FROM appointment_notification_targets WHERE batch_id = ?", (batch["id"],)).fetchone()[0]
        assert targets >= 1


def test_schedule_reactivation_and_cancel_last() -> None:
    headers = _auth_headers()
    schedule = client.post(
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
    assert schedule.status_code == 200
    data = schedule.json()
    assert data["status"] in {"executed", "awaiting_confirmation"}

    undo = client.post(
        "/api/v1/client/operations/commands",
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "text": "cancela lo último",
            "source_channel": "portal",
            "dry_run": False,
        },
        headers=headers,
    )
    assert undo.status_code == 200
    undo_data = undo.json()
    assert undo_data["status"] == "executed"
