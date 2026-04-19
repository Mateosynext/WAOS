from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_SQLITE_FOR_TESTS", "true")

from backend.app.db import SCHEMA_PATH, execute, fetch_one, get_connection, init_db
from backend.app.human_ops_runtime import (
    build_human_reply_suggestion,
    build_supervisor_console,
    build_takeover_brief,
    detect_failed_takeover,
    qa_scorecard,
    recommend_ai_reactivation,
    save_structured_internal_note,
)
from backend.app.main import app
from backend.app.migrations import apply_migrations
from backend.app.security import create_access_token


client = TestClient(app)


PASSWORD_HASH = "$2b$12$abcdefghijklmnopqrstuv12345678901234567890123456789012"
NOW = "2026-04-17T10:00:00Z"


def _conn():
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.row_factory = sqlite3.Row
    conn.executescript(Path(SCHEMA_PATH).read_text())
    apply_migrations(conn)
    return conn, tmp.name



def _seed_minimal_runtime(conn, *, org_id: str = "org_hops", bot_id: str = "bot_hops", contact_id: str = "ct_hops", conversation_id: str = "conv_hops", user_id: str = "usr_hops") -> None:
    execute(conn, "INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)", (user_id, f"{user_id}@example.com", "Human Ops User", PASSWORD_HASH, "org_admin", NOW, NOW))
    execute(conn, "INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at) VALUES (?, ?, ?, 'active', 'America/Mexico_City', 'health', '{}', ?, ?)", (org_id, "Human Ops Org", f"slug-{org_id}", NOW, NOW))
    execute(conn, "INSERT INTO organization_members (id, organization_id, user_id, role, is_active, created_at) VALUES (?, ?, ?, 'org_admin', 1, ?)", (f"mem_{user_id}", org_id, user_id, NOW))
    execute(conn, "INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, published_version_id, config_draft_json, created_at, updated_at, deleted_at) VALUES (?, ?, ?, ?, 'health', 'es', 'America/Mexico_City', 'active', 0, 'draft', NULL, '{}', ?, ?, NULL)", (bot_id, org_id, "Human Ops Bot", "Human Ops Bot", NOW, NOW))
    execute(conn, "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES (?, ?, '+5215551112222', 'Cliente Hops', 'cliente.hops@example.com', '[]', ?, ?)", (contact_id, org_id, NOW, NOW))
    execute(conn, "INSERT INTO contact_memory (id, organization_id, contact_id, bot_id, lead_stage, lead_score, interest, objections, summary, next_action, followup_at, memory_json, last_updated_at, urgency_score, urgency_level, current_intent) VALUES (?, ?, ?, ?, 'hot', 81, 'consulta', '[]', 'Cliente quiere resolver pago y agenda', 'Cerrar con pago o agenda', '2026-04-18T12:00:00Z', '{}', ?, 72, 'high', 'payment')", (f"mem_{contact_id}", org_id, contact_id, bot_id, NOW))
    execute(conn, "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, 'human_takeover', 1, 0, NULL, '2026-04-17T10:15:00Z', '2026-04-17T10:12:00Z', '2026-04-17T10:00:00Z', NULL, ?, ?, ?)", (conversation_id, org_id, bot_id, contact_id, user_id, NOW, NOW))
    execute(conn, "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, 'inbound', 'text', 'whatsapp', 'Necesito precio y quiero que me atienda una persona hoy', NULL, 'received', '{}', '2026-04-17T10:00:00Z')", (f"msg_{conversation_id}_1", org_id, conversation_id, contact_id, bot_id))
    execute(conn, "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, 'inbound', 'text', 'whatsapp', 'Sigo esperando respuesta humana', NULL, 'received', '{}', '2026-04-17T10:12:00Z')", (f"msg_{conversation_id}_2", org_id, conversation_id, contact_id, bot_id))
    execute(conn, "INSERT INTO commerce_payments (id, organization_id, bot_id, conversation_id, contact_id, title, amount, currency, status, payment_link_url, payment_link_status, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'Pago pendiente', 799, 'MXN', 'pending', NULL, 'pending', '{}', ?, ?)", (f"pay_{conversation_id}", org_id, bot_id, conversation_id, contact_id, NOW, NOW))



def test_phase13_migrations_create_human_ops_tables() -> None:
    conn, name = _conn()
    try:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "conversation_internal_notes" in tables
        assert "conversation_takeover_briefs" in tables
        assert "human_reply_suggestions" in tables
        assert "supervisor_console_snapshots" in tables
        assert "coaching_recommendations" in tables
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)



def test_structured_notes_takeover_brief_and_reactivation_guardrails() -> None:
    conn, name = _conn()
    try:
        _seed_minimal_runtime(conn)
        note = save_structured_internal_note(
            conn,
            organization_id="org_hops",
            bot_id="bot_hops",
            conversation_id="conv_hops",
            contact_id="ct_hops",
            author_user_id="usr_hops",
            category="takeover",
            priority="high",
            summary="Cliente pidió humano y sigue sin resolución",
            detail="Validar precio antes de responder y ofrecer agenda inmediata.",
            next_steps=["Confirmar precio vigente", "Responder como humano"],
            sources=["latest_inbound", "payment_status"],
            risk_level="high",
            risk_flags=["pending_payment", "delayed_handoff"],
        )
        assert note["category"] == "takeover"
        brief = build_takeover_brief(conn, "conv_hops", brief_type="takeover", generated_by_user_id="usr_hops", persist=True)
        assert brief["queue"]["role_key"] in {"cobranza", "ventas"}
        assert brief["notes"]
        failed = detect_failed_takeover(conn, "conv_hops")
        assert failed["failed_takeover"] is True
        guardrails = recommend_ai_reactivation(conn, "conv_hops")
        assert guardrails["allowed"] is False
        assert guardrails["blockers"]
        suggestion = build_human_reply_suggestion(conn, "conv_hops", objective="reply", operator_user_id="usr_hops", persist=True)
        assert suggestion["sources"]
        assert suggestion["risk"]["flags"]
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)



def test_supervisor_console_and_qa_scorecard_aggregate_by_team_and_agent() -> None:
    conn, name = _conn()
    try:
        _seed_minimal_runtime(conn)
        execute(
            conn,
            "INSERT INTO conversation_reviews (id, organization_id, bot_id, conversation_id, agent_user_id, review_type, quality_score, response_delay_seconds, tone, missed_opportunities_json, checklist_json, recommendations_json, created_at) VALUES (?, ?, ?, ?, ?, 'commercial_quality', 78, 1200, 'frio', ?, '[]', ?, '2026-04-17T10:20:00Z')",
            ("rev_hops", "org_hops", "bot_hops", "conv_hops", "usr_hops", '["Falto CTA"]', '["Responder mas rapido"]'),
        )
        console = build_supervisor_console(conn, "org_hops")
        assert console["summary"]["failed_takeovers"] >= 1
        assert console["teams"]
        assert console["qa"]["by_agent"]
        scorecard = qa_scorecard(conn, "org_hops")
        assert scorecard["by_agent"][0]["avg_quality"] == 78.0
        assert scorecard["coaching_loops"]
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)



def _auth_headers(org_id: str = "org_hops_api", user_id: str = "usr_hops_api") -> dict[str, str]:
    init_db()
    with get_connection() as conn:
        if not fetch_one(conn, "SELECT * FROM users WHERE id = ?", (user_id,)):
            execute(conn, "INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 'org_admin', 1, ?, ?)", (user_id, f"{user_id}@example.com", "API Human Ops User", PASSWORD_HASH, NOW, NOW))
        if not fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (org_id,)):
            execute(conn, "INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at) VALUES (?, ?, ?, 'active', 'America/Mexico_City', 'health', '{}', ?, ?)", (org_id, "API Hops Org", f"slug-{org_id}", NOW, NOW))
        if not fetch_one(conn, "SELECT * FROM organization_members WHERE organization_id = ? AND user_id = ?", (org_id, user_id)):
            execute(conn, "INSERT INTO organization_members (id, organization_id, user_id, role, is_active, created_at) VALUES (?, ?, ?, 'org_admin', 1, ?)", (f"mem_{user_id}", org_id, user_id, NOW))
        if not fetch_one(conn, "SELECT * FROM bots WHERE id = ?", ("bot_hops_api",)):
            execute(conn, "INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, published_version_id, config_draft_json, created_at, updated_at, deleted_at) VALUES ('bot_hops_api', ?, 'API Bot', 'API Bot', 'health', 'es', 'America/Mexico_City', 'active', 0, 'draft', NULL, '{}', ?, ?, NULL)", (org_id, NOW, NOW))
        if not fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", ("ct_hops_api",)):
            execute(conn, "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES ('ct_hops_api', ?, '+5215553334444', 'Cliente API', 'cliente.api@example.com', '[]', ?, ?)", (org_id, NOW, NOW))
        if not fetch_one(conn, "SELECT * FROM contact_memory WHERE id = ?", ("mem_ct_hops_api",)):
            execute(conn, "INSERT INTO contact_memory (id, organization_id, contact_id, bot_id, lead_stage, lead_score, interest, objections, summary, next_action, followup_at, memory_json, last_updated_at, urgency_score, urgency_level, current_intent) VALUES ('mem_ct_hops_api', ?, 'ct_hops_api', 'bot_hops_api', 'qualified', 74, 'agenda', '[]', 'Cliente listo para agenda', 'Cerrar cita', '2026-04-18T12:00:00Z', '{}', ?, 60, 'high', 'schedule')", (org_id, NOW))
        if not fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", ("conv_hops_api",)):
            execute(conn, "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES ('conv_hops_api', ?, 'bot_hops_api', 'ct_hops_api', 'human_takeover', 1, 0, NULL, '2026-04-17T10:20:00Z', '2026-04-17T10:10:00Z', '2026-04-17T10:00:00Z', NULL, ?, ?, ?)", (org_id, user_id, NOW, NOW))
        if not fetch_one(conn, "SELECT * FROM messages WHERE id = ?", ("msg_hops_api_1",)):
            execute(conn, "INSERT INTO messages (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at) VALUES ('msg_hops_api_1', ?, 'conv_hops_api', 'ct_hops_api', 'bot_hops_api', 'inbound', 'text', 'whatsapp', 'Quiero agendar con humano', NULL, 'received', '{}', '2026-04-17T10:00:00Z')", (org_id,))
    token = create_access_token({"id": user_id, "email": f"{user_id}@example.com", "global_role": "org_admin", "organization_ids": [org_id]})
    return {"Authorization": f"Bearer {token}"}



def test_api_endpoints_expose_human_ops_console_and_structured_notes() -> None:
    headers = _auth_headers()
    note_response = client.post(
        "/api/v1/conversations/conv_hops_api/internal-notes/structured",
        json={
            "category": "supervisor",
            "priority": "high",
            "summary": "Tomar caso manualmente",
            "detail": "Cliente pide humano y agenda inmediata.",
            "next_steps": ["Responder ahora", "Confirmar horario"],
            "sources": ["latest_inbound"],
            "risk_level": "medium",
            "risk_flags": ["handoff_pending"],
        },
        headers=headers,
    )
    assert note_response.status_code == 200
    assert note_response.json()["data"]["category"] == "supervisor"

    support = client.get("/api/v1/conversations/conv_hops_api/decision-support", headers=headers)
    assert support.status_code == 200
    support_data = support.json()["data"]
    assert support_data["takeover_brief"]["queue"]["role_key"] in {"agenda", "ventas", "soporte", "cobranza"}
    assert "reply_suggestion" in support_data

    console = client.get("/api/v1/supervisor/console", params={"organization_id": "org_hops_api"}, headers=headers)
    assert console.status_code == 200
    console_data = console.json()["data"]
    assert console_data["teams"]
    assert "summary" in console_data

    copilot = client.post(
        "/api/v1/conversations/conv_hops_api/copilot",
        json={"draft": "", "objective": "book"},
        headers=headers,
    )
    assert copilot.status_code == 200
    copilot_data = copilot.json()
    assert copilot_data["sources"]
    assert "risk" in copilot_data
