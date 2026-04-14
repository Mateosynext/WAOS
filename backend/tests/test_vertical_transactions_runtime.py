from __future__ import annotations

from pathlib import Path

from backend.app.db import execute, fetch_one, get_connection, init_db
from backend.app.utils import new_id, to_json, utcnow_iso
from backend.app.vertical_transactions import vertical_transaction_service
from backend.app.verticals import list_vertical_profiles


def _seed_actor_and_org() -> tuple[dict, str]:
    organization_id = new_id("org")
    user_id = new_id("user")
    now = utcnow_iso()
    with get_connection() as conn:
        execute(
            conn,
            "INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (user_id, f"{user_id}@example.com", "Test User", "not-used", "super_admin", now, now),
        )
        execute(
            conn,
            "INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at) VALUES (?, ?, ?, 'active', 'America/Mexico_City', NULL, '{}', ?, ?)",
            (organization_id, "Org Test", f"org-{organization_id[-8:]}", now, now),
        )
    return ({"id": user_id, "global_role": "super_admin", "organization_ids": [organization_id]}, organization_id)


def test_vertical_transaction_playbooks_run_end_to_end_for_every_vertical() -> None:
    init_db()
    actor, organization_id = _seed_actor_and_org()
    with get_connection() as conn:
        for profile in list_vertical_profiles():
            account = vertical_transaction_service.create_account(
                conn,
                organization_id=organization_id,
                vertical_id=profile["id"],
                actor_user=actor,
                external_reference=f"{profile['id']}-demo",
                metadata={"source": "pytest"},
            )
            result = vertical_transaction_service.execute_playbook(
                conn,
                organization_id=organization_id,
                account_id=account["id"],
                actor_user=actor,
            )
            final_account = result["account"]
            expected_commands = len(profile["transactional_motor_v12"]["command_catalog"])
            assert len(result["commands_executed"]) == expected_commands
            assert len(final_account["commands"]) == expected_commands
            assert len(final_account["timeline"]) == expected_commands
            assert final_account["views"]
            assert final_account["last_event"]
            assert final_account["amount_expected"] >= 0
            assert final_account["amount_collected"] >= 0
            if any(item["command"] in {"create_quote", "request_deposit", "collect_payment", "sell_session_package", "capture_order", "collect_order_payment"} for item in profile["transactional_motor_v12"]["command_catalog"]):
                assert final_account["ledger"]
            if profile["vertical_runtime"]["document_flow"]["required_documents"]:
                assert final_account["documents"]


def test_vertical_transaction_commands_are_idempotent() -> None:
    init_db()
    actor, organization_id = _seed_actor_and_org()
    with get_connection() as conn:
        account = vertical_transaction_service.create_account(conn, organization_id=organization_id, vertical_id="fitness", actor_user=actor)
        first = vertical_transaction_service.dispatch_command(
            conn,
            organization_id=organization_id,
            account_id=account["id"],
            command_name="create_quote",
            payload={"idempotency_key": "same-key", "amount": 2500},
            actor_user=actor,
        )
        second = vertical_transaction_service.dispatch_command(
            conn,
            organization_id=organization_id,
            account_id=account["id"],
            command_name="create_quote",
            payload={"idempotency_key": "same-key", "amount": 2500},
            actor_user=actor,
        )
        assert first["idempotent"] is False
        assert second["idempotent"] is True
        refreshed = vertical_transaction_service.get_account(conn, organization_id=organization_id, account_id=account["id"])
        assert len(refreshed["commands"]) == 1
        assert len(refreshed["timeline"]) == 1
