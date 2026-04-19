from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_one, get_connection, init_db
from backend.app.main import app
from backend.app.security import create_access_token


client = TestClient(app)


def _auth_headers(org_id: str = "org_activation") -> dict[str, str]:
    init_db()
    is_default_scope = org_id == "org_activation"
    org_slug = "org-activation" if is_default_scope else org_id.replace("_", "-")
    org_name = "Org Activation" if is_default_scope else org_slug.replace("-", " ").title()
    member_id = "mem_activation" if is_default_scope else f"mem_{org_id}"
    bot_id = "bot_activation" if is_default_scope else f"bot_{org_id}"
    integration_id = "int_activation" if is_default_scope else f"int_{org_id}"
    service_id = "svc_activation" if is_default_scope else f"svc_{org_id}"
    contact_id = "ct_activation" if is_default_scope else f"ct_{org_id}"
    memory_id = "mem_contact_activation" if is_default_scope else f"mem_contact_{org_id}"
    conversation_id = "conv_activation" if is_default_scope else f"conv_{org_id}"
    message_id = "msg_activation" if is_default_scope else f"msg_{org_id}"
    appointment_id = "apt_activation" if is_default_scope else f"apt_{org_id}"
    lead_id = "lead_activation" if is_default_scope else f"lead_{org_id}"
    ai_run_id = "air_activation" if is_default_scope else f"air_{org_id}"
    reasoning_id = "reason_activation" if is_default_scope else f"reason_{org_id}"
    receipt_id = "whrec_activation" if is_default_scope else f"whrec_{org_id}"
    payment_id = "pay_activation" if is_default_scope else f"pay_{org_id}"

    with get_connection() as conn:
        user = fetch_one(conn, "SELECT * FROM users WHERE id = ?", ("usr_activation",))
        if not user:
            execute(
                conn,
                "INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                (
                    "usr_activation",
                    "activation@example.com",
                    "Activation User",
                    "$2b$12$abcdefghijklmnopqrstuv12345678901234567890123456789012",
                    "org_admin",
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                ),
            )
        org = fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (org_id,))
        if not org:
            execute(
                conn,
                "INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, '{}', ?, ?)",
                (org_id, org_name, org_slug, "active", "America/Mexico_City", "fitness", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
        member = fetch_one(conn, "SELECT * FROM organization_members WHERE organization_id = ? AND user_id = ?", (org_id, "usr_activation"))
        if not member:
            execute(
                conn,
                "INSERT INTO organization_members (id, organization_id, user_id, role, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
                (member_id, org_id, "usr_activation", "org_admin", "2026-01-01T00:00:00Z"),
            )

        if not is_default_scope:
            conn.commit()
            user = fetch_one(conn, "SELECT * FROM users WHERE id = ?", ("usr_activation",))
            token = create_access_token(user)
            return {"Authorization": f"Bearer {token}", "x-organization-id": org_id}

        bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ?", (bot_id,))
        if not bot:
            execute(
                conn,
                "INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, published_version_id, config_draft_json, created_at, updated_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, NULL, '{}', ?, ?, NULL)",
                (bot_id, org_id, "Bot Activation", "Org Activation", "fitness", "es", "America/Mexico_City", "active", "draft", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
        else:
            execute(
                conn,
                "UPDATE bots SET organization_id = ?, name = ?, business_name = ?, vertical = ?, language = ?, timezone = ?, status = 'active', ai_paused = 0, current_state = 'draft', deleted_at = NULL, updated_at = ? WHERE id = ?",
                (org_id, "Bot Activation", "Org Activation", "fitness", "es", "America/Mexico_City", "2026-01-01T00:00:00Z", bot_id),
            )
        integration = fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (integration_id,))
        if not integration:
            execute(
                conn,
                "INSERT INTO integration_connections (id, organization_id, bot_id, integration_type, provider, name, status, health_status, credential_status, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, ?)",
                (integration_id, org_id, bot_id, "whatsapp", "meta", "WhatsApp", "connected", "healthy", "valid", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
        service = fetch_one(conn, "SELECT * FROM catalog_services WHERE id = ?", (service_id,))
        if not service:
            execute(
                conn,
                "INSERT INTO catalog_services (id, organization_id, bot_id, category_id, name, duration_minutes, price, currency, preparation, restrictions, availability_json, photos_json, associated_staff, branch, status, created_at, updated_at) VALUES (?, ?, ?, NULL, ?, 30, 100, 'MXN', NULL, NULL, '{}', '[]', NULL, NULL, 'active', ?, ?)",
                (service_id, org_id, bot_id, "Consulta inicial", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
        contact = fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", (contact_id,))
        if not contact:
            execute(
                conn,
                "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, '[]', ?, ?)",
                (contact_id, org_id, "+5215550001111", "Cliente Demo", "cliente@example.com", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
        memory = fetch_one(conn, "SELECT * FROM contact_memory WHERE id = ?", (memory_id,))
        if not memory:
            execute(
                conn,
                "INSERT INTO contact_memory (id, organization_id, contact_id, bot_id, lead_stage, lead_score, interest, objections, summary, next_action, followup_at, memory_json, last_updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    memory_id,
                    org_id,
                    contact_id,
                    bot_id,
                    "hot",
                    82,
                    "consulta",
                    "[]",
                    "Lead caliente",
                    "Llamar y cerrar cita",
                    "2026-01-05T00:00:00Z",
                    '{"relationship_intelligence":{"status":"known","relation_key":"client","current_mode":"sales","urgency_level":"high","urgency_score":50,"attention_tier":"owner_now","known_contact":true}}',
                    "2026-01-01T00:00:00Z",
                ),
            )
        else:
            execute(
                conn,
                "UPDATE contact_memory SET organization_id = ?, contact_id = ?, bot_id = ?, lead_stage = ?, lead_score = ?, interest = ?, objections = ?, summary = ?, next_action = ?, followup_at = ?, memory_json = ?, last_updated_at = ? WHERE id = ?",
                (
                    org_id,
                    contact_id,
                    bot_id,
                    "hot",
                    82,
                    "consulta",
                    "[]",
                    "Lead caliente",
                    "Llamar y cerrar cita",
                    "2026-01-05T00:00:00Z",
                    '{"relationship_intelligence":{"status":"known","relation_key":"client","current_mode":"sales","urgency_level":"high","urgency_score":50,"attention_tier":"owner_now","known_contact":true}}',
                    "2026-01-01T00:00:00Z",
                    memory_id,
                ),
            )
        conversation = fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        if not conversation:
            execute(
                conn,
                "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 0, 1, NULL, NULL, ?, NULL, NULL, NULL, ?, ?)",
                (conversation_id, org_id, bot_id, contact_id, "open", "2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"),
            )
        else:
            execute(
                conn,
                "UPDATE conversations SET organization_id = ?, bot_id = ?, contact_id = ?, status = ?, human_takeover = 0, ai_active = 1, paused_until = NULL, automation_freeze_until = NULL, last_message_at = ?, last_human_at = NULL, last_ai_at = NULL, assigned_user_id = NULL, updated_at = ? WHERE id = ?",
                (org_id, bot_id, contact_id, "open", "2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z", conversation_id),
            )
        message = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (message_id,))
        if not message:
            execute(
                conn,
                "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, '{}', ?)",
                (message_id, org_id, conversation_id, contact_id, bot_id, "inbound", "text", "whatsapp", "Quiero una cita hoy", "received", "2026-01-02T00:00:00Z"),
            )
        else:
            execute(
                conn,
                "UPDATE messages SET organization_id = ?, conversation_id = ?, contact_id = ?, bot_id = ?, direction = 'inbound', kind = 'text', source = 'whatsapp', body = ?, status = ?, metadata_json = '{}' WHERE id = ?",
                (org_id, conversation_id, contact_id, bot_id, "Quiero una cita hoy", "received", message_id),
            )
        appointment = fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        if not appointment:
            execute(
                conn,
                "INSERT INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, external_id, provider, provider_payload_json, integration_id, synced_at, reminder_scheduled_at, confirmed_at, cancelled_at, no_show_at, followup_status, followup_sent_at, rescheduled_from_appointment_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 30, ?, NULL, NULL, 'waos', '{}', NULL, NULL, NULL, NULL, NULL, NULL, 'pending', NULL, NULL, ?, ?)",
                (appointment_id, org_id, bot_id, conversation_id, contact_id, "2026-01-03T12:00:00Z", "scheduled", "America/Mexico_City", "2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z"),
            )
        lead = fetch_one(conn, "SELECT * FROM crm_leads WHERE id = ?", (lead_id,))
        if not lead:
            execute(
                conn,
                """INSERT INTO crm_leads (id, organization_id, bot_id, conversation_id, contact_id, stage, estimated_amount, owner_user_id, next_action, followup_at, tags_json, notes, lost_reason, language, source_channel, source_campaign, pipeline_json, score_buying_intent, close_probability, detected_objections_json, best_next_action, temperature_status, last_qualification_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1200, ?, ?, ?, '[]', '', NULL, 'es', 'whatsapp', 'organico', '{}', 80, 72, '["precio"]', 'Enviar propuesta y cerrar cita', 'hot', ?, ?, ?)""",
                (lead_id, org_id, bot_id, conversation_id, contact_id, "nuevo", "usr_activation", "Llamar y cerrar cita", "2026-01-05T00:00:00Z", "2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z"),
            )
        ai_run = fetch_one(conn, "SELECT * FROM message_ai_runs WHERE id = ?", (ai_run_id,))
        if not ai_run:
            execute(
                conn,
                """INSERT INTO message_ai_runs (id, organization_id, message_id, conversation_id, bot_id, classifier_input, classifier_output, decision_input, decision_output, generator_input, generator_output, action_taken, error, created_at, correlation_id, classifier_source, decision_policy, generator_source, fallback_chain_json) VALUES (?, ?, ?, ?, ?, '{}', '{"intent":"schedule"}', '{}', '{"action":"reply","policy":"heuristic"}', '{}', '{"summary":"booking flow"}', 'reply', NULL, ?, 'corr-activation', 'classifier-v1', 'heuristic', 'generator-v1', '[]')""",
                (ai_run_id, org_id, message_id, conversation_id, bot_id, "2026-01-02T00:00:00Z"),
            )
        reasoning = fetch_one(conn, "SELECT * FROM message_operational_reasoning WHERE id = ?", (reasoning_id,))
        if not reasoning:
            execute(
                conn,
                """INSERT INTO message_operational_reasoning (id, organization_id, message_id, conversation_id, bot_id, intent_detected, urgency_level, urgency_score, takeover_reason, policy_applied, classifier_source, generator_source, summary_json, created_at) VALUES (?, ?, ?, ?, ?, 'schedule', 'high', 50, NULL, 'heuristic', 'classifier-v1', 'generator-v1', '{"why":"schedule lead"}', ?)""",
                (reasoning_id, org_id, message_id, conversation_id, bot_id, "2026-01-02T00:00:00Z"),
            )
        receipt = fetch_one(conn, "SELECT * FROM webhook_event_receipts WHERE id = ?", (receipt_id,))
        if not receipt:
            execute(
                conn,
                "INSERT INTO webhook_event_receipts (id, channel, organization_id, external_event_id, status, payload_hash, created_at) VALUES (?, 'stripe', ?, 'evt_activation', 'failed', 'hash-1', ?)",
                (receipt_id, org_id, "2026-01-02T00:00:00Z"),
            )
        payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))
        if not payment:
            execute(
                conn,
                "INSERT INTO commerce_payments (id, organization_id, bot_id, conversation_id, contact_id, crm_lead_id, title, amount, currency, status, payment_link_url, payment_link_status, reminder_scheduled_at, confirmed_at, receipt_sent_at, cart_recovery_status, send_receipt_on_confirm, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'Anticipo', 500, 'MXN', 'pending', NULL, 'generated', NULL, NULL, NULL, 'inactive', 1, '{}', ?, ?)",
                (payment_id, org_id, bot_id, conversation_id, contact_id, lead_id, "2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z"),
            )
        else:
            execute(
                conn,
                "UPDATE commerce_payments SET organization_id = ?, bot_id = ?, conversation_id = ?, contact_id = ?, crm_lead_id = ?, status = 'pending', payment_link_url = NULL, payment_link_status = 'generated', reminder_scheduled_at = NULL, confirmed_at = NULL, receipt_sent_at = NULL, cart_recovery_status = 'inactive', send_receipt_on_confirm = 1, metadata_json = '{}', updated_at = ? WHERE id = ?",
                (org_id, bot_id, conversation_id, contact_id, lead_id, "2026-01-02T00:00:00Z", payment_id),
            )
        conn.commit()
        user = fetch_one(conn, "SELECT * FROM users WHERE id = ?", ("usr_activation",))
    token = create_access_token(user)
    return {"Authorization": f"Bearer {token}", "x-organization-id": org_id}


def test_onboarding_summary_and_tenant_mode_update() -> None:
    headers = _auth_headers()
    response = client.get("/api/v1/onboarding/summary", params={"organization_id": "org_activation", "bot_id": "bot_activation"}, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["readiness_score"] >= 80
    assert data["counts"]["channels"] >= 1
    assert data["counts"]["catalog_items"] >= 1
    assert data["tenant_mode"] == "sandbox"
    assert data["next_step"]["key"] in {"run_test", "optimize"}

    switch = client.post("/api/v1/onboarding/tenant-mode", json={"organization_id": "org_activation", "tenant_mode": "go_live"}, headers=headers)
    assert switch.status_code == 200
    switched = switch.json()["data"]
    assert switched["tenant_mode"] == "go_live"


def test_saved_views_and_priority_enrichment() -> None:
    headers = _auth_headers()
    create_view = client.post(
        "/api/v1/inbox/saved-views",
        json={
            "organization_id": "org_activation",
            "name": "Hot leads",
            "filters": {"filter": "hot", "sort": "priority", "mode": "sales"},
            "is_default": True,
        },
        headers=headers,
    )
    assert create_view.status_code == 200
    assert create_view.json()["data"]["name"] == "Hot leads"

    listed = client.get("/api/v1/inbox/saved-views", params={"organization_id": "org_activation"}, headers=headers)
    assert listed.status_code == 200
    listed_payload = listed.json()["data"]
    assert len(listed_payload) >= 1
    assert listed_payload[0]["filters"]["sort"] == "priority"

    conversations = client.get("/api/v1/conversations", params={"organization_id": "org_activation", "sort": "priority"}, headers=headers)
    assert conversations.status_code == 200
    items = conversations.json()
    assert len(items) >= 1
    first = items[0]
    assert first["priority_score"] >= 50
    assert first["next_best_action"]
    assert first["attention_class"] in {"requires_human", "follow_up_only", "ai_or_operator"}


def test_phase2_inbox_queues_and_decision_support() -> None:
    headers = _auth_headers()
    queues = client.get("/api/v1/inbox/queues", params={"organization_id": "org_activation"}, headers=headers)
    assert queues.status_code == 200
    queue_payload = queues.json()["data"]
    assert any(item["role_key"] in {"ventas", "agenda", "cobranza", "soporte"} for item in queue_payload["queues"])

    support = client.get("/api/v1/conversations/conv_activation/decision-support", headers=headers)
    assert support.status_code == 200
    data = support.json()["data"]
    assert data["confidence_score"] >= 40
    assert data["queue"]["role_key"] in {"ventas", "agenda", "cobranza", "soporte"}
    assert data["sla"]["status"] in {"healthy", "at_risk", "breached"}
    assert data["explanation"]


def test_phase2_crm_pipeline_and_integration_center() -> None:
    headers = _auth_headers()
    pipeline = client.get("/api/v1/crm/pipeline-summary", params={"organization_id": "org_activation", "bot_id": "bot_activation"}, headers=headers)
    assert pipeline.status_code == 200
    pipeline_data = pipeline.json()["data"]
    assert pipeline_data["total_leads"] >= 1
    assert pipeline_data["stages"]

    center = client.get("/api/v1/integrations/center", params={"organization_id": "org_activation"}, headers=headers)
    assert center.status_code == 200
    center_data = center.json()["data"]
    assert center_data["summary"]["total_integrations"] >= 1
    assert isinstance(center_data["failed_receipts"], list)

    replay = client.post("/api/v1/integrations/webhooks/whrec_activation/replay", json={"dry_run": True, "note": "test replay"}, headers=headers)
    assert replay.status_code == 200
    replay_data = replay.json()["data"]
    assert replay_data["dry_run"] is True
    assert replay_data["recommended_action"] in {"safe_replay", "skip_duplicate"}


def test_phase3_assignment_simulation_and_capacity() -> None:
    headers = _auth_headers()
    with get_connection() as conn:
        user = fetch_one(conn, "SELECT * FROM users WHERE id = ?", ("usr_operator",))
        if not user:
            execute(
                conn,
                "INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                ("usr_operator", "operator@example.com", "Operador Cola", "$2b$12$abcdefghijklmnopqrstuv12345678901234567890123456789012", "operator", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
        member = fetch_one(conn, "SELECT * FROM organization_members WHERE organization_id = ? AND user_id = ?", ("org_activation", "usr_operator"))
        if not member:
            execute(conn, "INSERT INTO organization_members (id, organization_id, user_id, role, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)", ("mem_operator", "org_activation", "usr_operator", "operator", "2026-01-01T00:00:00Z"))
        conn.commit()

    ownership_before = client.get("/api/v1/inbox/ownership", params={"organization_id": "org_activation"}, headers=headers)
    assert ownership_before.status_code == 200
    assert ownership_before.json()["data"]["unassigned_open"] >= 1

    auto_assign = client.post("/api/v1/inbox/auto-assign", json={"organization_id": "org_activation", "limit": 10}, headers=headers)
    assert auto_assign.status_code == 200
    assert auto_assign.json()["data"]["assigned_count"] >= 1

    assigned = client.post("/api/v1/conversations/conv_activation/assign", json={"assigned_user_id": "usr_operator", "mode": "manual", "note": "phase3"}, headers=headers)
    assert assigned.status_code == 200
    assert assigned.json()["assigned_user_id"] == "usr_operator"

    snapshot = client.post("/api/v1/bots/bot_activation/versions/draft-snapshot", json={"notes": "before simulator"}, headers=headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["status"] == "draft_snapshot"

    case = client.post("/api/v1/bots/bot_activation/simulation-cases", json={"organization_id": "org_activation", "title": "Reprogramar cita", "scenario_text": "Quiero reprogramar mi cita para mañana", "expected_action": "schedule", "expected_queue": "agenda", "expected_must_escalate": False, "tags": []}, headers=headers)
    assert case.status_code == 200

    simulation = client.post("/api/v1/bots/bot_activation/simulate", json={"compare_target": "published", "case_ids": []}, headers=headers)
    assert simulation.status_code == 200
    sim_data = simulation.json()
    assert sim_data["passed_count"] >= 1

    resource = client.post("/api/v1/agenda/resources", json={"organization_id": "org_activation", "bot_id": "bot_activation", "name": "Dra. Sofía", "resource_type": "professional", "branch": "Polanco"}, headers=headers)
    assert resource.status_code == 200
    resource_id = resource.json()["id"]

    rule = client.post("/api/v1/agenda/capacity-rules", json={"organization_id": "org_activation", "bot_id": "bot_activation", "resource_id": resource_id, "day_of_week": 1, "start_time": "09:00", "end_time": "12:00", "slot_capacity": 1}, headers=headers)
    assert rule.status_code == 200

    assign_resource = client.post("/api/v1/appointments/apt_activation/assign-resource", json={"resource_id": resource_id, "note": "primary"}, headers=headers)
    assert assign_resource.status_code == 200

    capacity = client.get("/api/v1/agenda/capacity/overview", params={"organization_id": "org_activation", "bot_id": "bot_activation"}, headers=headers)
    assert capacity.status_code == 200
    capacity_data = capacity.json()
    assert capacity_data["summary"]["resources"] >= 1
    assert capacity_data["summary"]["capacity_rules"] >= 1
