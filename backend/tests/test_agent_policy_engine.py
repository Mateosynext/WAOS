from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_one, get_connection
from backend.app.main import app
from backend.tests.test_activation_foundations import _auth_headers


client = TestClient(app)


POLICY_BUDGET_CONTACT_ID = "ct_policy_budget"
POLICY_BUDGET_CONVERSATION_ID = "conv_policy_budget"
POLICY_ACTION_CONTACT_ID = "ct_policy_action"
POLICY_ACTION_CONVERSATION_ID = "conv_policy_action"


def _seed_contact_and_conversation(contact_id: str, conversation_id: str, *, body: str) -> None:
    _auth_headers()
    with get_connection() as conn:
        contact = fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", (contact_id,))
        if not contact:
            execute(
                conn,
                "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES (?, 'org_activation', ?, ?, ?, '[]', ?, ?)",
                (
                    contact_id,
                    f"+521555{contact_id[-4:]}",
                    f"Policy {contact_id}",
                    f"{contact_id}@example.com",
                    "2026-04-17T10:00:00Z",
                    "2026-04-17T10:00:00Z",
                ),
            )
        conversation = fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        if not conversation:
            execute(
                conn,
                "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, 'open', 0, 1, NULL, NULL, ?, NULL, NULL, NULL, ?, ?)",
                (
                    conversation_id,
                    contact_id,
                    "2026-04-17T10:00:00Z",
                    "2026-04-17T10:00:00Z",
                    "2026-04-17T10:00:00Z",
                ),
            )
        message = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (f"msg_{conversation_id}",))
        if not message:
            execute(
                conn,
                "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES (?, 'org_activation', ?, ?, 'bot_activation', 'inbound', 'text', 'whatsapp', ?, NULL, 'received', '{}', ?)",
                (f"msg_{conversation_id}", conversation_id, contact_id, body, "2026-04-17T10:00:00Z"),
            )
        conn.commit()



def test_agent_policy_profiles_and_budget_evaluation() -> None:
    headers = _auth_headers()
    _seed_contact_and_conversation(POLICY_BUDGET_CONTACT_ID, POLICY_BUDGET_CONVERSATION_ID, body="Quiero pagar ahora")
    with get_connection() as conn:
        execute(conn, "DELETE FROM tool_execution_runs WHERE contact_id = ?", (POLICY_BUDGET_CONTACT_ID,))
        for idx in range(3):
            now = f"2026-04-17T10:0{idx}:00Z"
            done = f"2026-04-17T10:0{idx}:30Z"
            execute(
                conn,
                """
                INSERT INTO tool_execution_runs (
                    id, organization_id, bot_id, action, adapter_key, provider, execution_mode, status,
                    permission_required, requires_confirmation, request_json, normalized_payload_json,
                    validation_json, target_ref_json, result_json, error_json, metadata_json,
                    conversation_id, contact_id, payment_id, requested_by,
                    started_at, completed_at, created_at, updated_at,
                    specialist_agent_key, policy_profile_key, policy_profile_version, policy_json
                ) VALUES (?, 'org_activation', 'bot_activation', 'create_payment_link', 'stripe_payments', 'stripe', 'execute', 'completed',
                    'revenue.manage', 1, '{}', '{}', '{}', '{}', '{}', '{}', '{}',
                    ?, ?, ?, 'usr_activation',
                    ?, ?, ?, ?,
                    'collections', 'collections_ops', 'collections_ops_policy_v1', '{}')
                """,
                (
                    f"toolrun_budget_{idx}",
                    POLICY_BUDGET_CONVERSATION_ID,
                    POLICY_BUDGET_CONTACT_ID,
                    f"pay_budget_{idx}",
                    now,
                    done,
                    now,
                    done,
                ),
            )
        conn.commit()

    profiles = client.get("/api/v1/agent-policy/profiles", headers=headers, params={"organization_id": "org_activation"})
    assert profiles.status_code == 200
    assert any(item["key"] == "collections_ops" for item in profiles.json()["data"]["items"])

    evaluated = client.post(
        "/api/v1/agent-policy/evaluate",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "specialist_agent_key": "collections",
            "conversation_id": POLICY_BUDGET_CONVERSATION_ID,
            "contact_id": POLICY_BUDGET_CONTACT_ID,
            "requested_action": "create_payment_link",
            "persist": True,
        },
    )
    assert evaluated.status_code == 200
    payload = evaluated.json()["data"]["evaluation"]
    assert payload["policy_profile_key"] == "collections_ops"
    assert payload["budget_state"]["blocked"] is True
    assert any(item["name"] == "max_payment_links_per_contact_24h" and item["status"] == "blocked" for item in payload["budget_state"]["checks"])



def test_tool_execution_preview_and_execute_enforce_specialist_policy() -> None:
    headers = _auth_headers()
    _seed_contact_and_conversation(POLICY_ACTION_CONTACT_ID, POLICY_ACTION_CONVERSATION_ID, body="Necesito reagendar mi cita para mañana")
    routed = client.post(
        "/api/v1/agent-orchestration/route",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": POLICY_ACTION_CONVERSATION_ID,
            "contact_id": POLICY_ACTION_CONTACT_ID,
            "text": "Necesito reagendar mi cita para mañana",
            "persist": True,
            "record_exposure": False,
        },
    )
    assert routed.status_code == 200
    route_run_id = routed.json()["data"]["route_run"]["id"]
    assert routed.json()["data"]["route"]["specialist_agent_key"] == "booking"

    preview = client.post(
        "/api/v1/tool-executions/preview",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "action": "create_payment_link",
            "payload": {
                "bot_id": "bot_activation",
                "conversation_id": POLICY_ACTION_CONVERSATION_ID,
                "contact_id": POLICY_ACTION_CONTACT_ID,
                "title": "Anticipo",
                "amount": 500,
                "currency": "MXN",
            },
            "metadata": {"agent_routing_run_id": route_run_id},
        },
    )
    assert preview.status_code == 200
    data = preview.json()["data"]
    assert data["execution"]["status"] == "preview_blocked"
    assert data["policy"]["decision"]["enforcement"] == "block"
    assert data["confirmation_token"] is None

    execute_response = client.post(
        "/api/v1/tool-executions/execute",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "action": "create_payment_link",
            "payload": {
                "bot_id": "bot_activation",
                "conversation_id": POLICY_ACTION_CONVERSATION_ID,
                "contact_id": POLICY_ACTION_CONTACT_ID,
                "title": "Anticipo",
                "amount": 500,
                "currency": "MXN",
            },
            "metadata": {"agent_routing_run_id": route_run_id},
        },
    )
    assert execute_response.status_code == 409
    assert "tool_execution_policy_blocked" in execute_response.json()["detail"]
