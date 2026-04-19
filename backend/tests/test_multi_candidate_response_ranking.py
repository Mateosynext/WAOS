from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.agent_runtime import orchestrate_runtime_turn
from backend.app.ai import run_ai_pipeline
from backend.app.db import fetch_all, fetch_one, get_connection, init_db, execute
from backend.app.main import app
from backend.app.utils import to_json
from backend.tests.test_activation_foundations import _auth_headers

client = TestClient(app)


def _bot_config() -> dict:
    return {
        "identity": {"business_name": "WAOS Clinic", "language": "es"},
        "business_knowledge": {
            "services": ["Citas", "Valoración"],
            "prices": [{"name": "Consulta", "price": "$799 MXN"}],
            "hours": "Lunes a viernes de 9:00 a 18:00",
            "location": "Av. Reforma 100",
        },
        "objective": {"primary": "book_more"},
        "personality": {"tone": "clear"},
        "rules": {},
        "handoff": {"sensitive_keywords": ["humano", "asesor"]},
    }



def test_orchestrate_runtime_turn_generates_multiple_candidates_and_selects_best() -> None:
    conversation = {
        "id": "conv_rank_1",
        "status": "ai_active",
        "human_takeover": 0,
        "ai_active": 1,
        "paused_until": None,
        "automation_freeze_until": None,
    }
    bot = {
        "id": "bot_rank_1",
        "status": "active",
        "ai_paused": 0,
    }
    result = orchestrate_runtime_turn(
        text="Hola, ¿me compartes horario para hoy?",
        conversation=conversation,
        bot=bot,
        memory={"lead_stage": "contacted", "lead_score": 10},
        bot_config=_bot_config(),
        recent_messages=[],
        conn=None,
        organization_id=None,
        bot_id="bot_rank_1",
        contact_id="ct_rank_1",
        conversation_id="conv_rank_1",
        recent_voice_notes=[],
        language_config={"default_language": "es", "supported_languages": ["es", "en"]},
    )
    ranking = result["candidate_ranking"]
    assert ranking["ranker_version"] == "response_ranker_v1"
    assert ranking["candidate_count"] >= 3
    assert len(ranking["candidates"]) == ranking["candidate_count"]
    selected = next(item for item in ranking["candidates"] if item["selected"])
    assert ranking["selected_variant"] == selected["variant_key"]
    assert selected["text"] == result["generated"]["text"]
    assert selected["score_total"] == max(item["score_total"] for item in ranking["candidates"])
    assert ranking["summary"]["selection_margin"] >= 0
    assert result["post_send_evaluation"]["selected_variant"] == selected["variant_key"]



def test_run_ai_pipeline_persists_candidate_rankings_and_feeds_variant_scorecards() -> None:
    headers = _auth_headers()
    init_db()
    with get_connection() as conn:
        execute(
            conn,
            "UPDATE bots SET config_draft_json = ? WHERE id = ?",
            (to_json(_bot_config()), "bot_activation"),
        )
        inbound = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", ("msg_activation",))
        conversation = fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", ("conv_activation",))
        bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ?", ("bot_activation",))
        contact = fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", ("ct_activation",))
        memory = fetch_one(conn, "SELECT * FROM contact_memory WHERE bot_id = ? AND contact_id = ?", ("bot_activation", "ct_activation"))
        result = run_ai_pipeline(
            conn,
            incoming_message=inbound,
            conversation=conversation,
            bot=bot,
            contact=contact,
            memory=memory,
            correlation_id="trace-rank-e2e",
        )
        assert result["decision"]["action"] in {"respond", "respond_and_schedule_followup"}

        ai_run = fetch_one(conn, "SELECT * FROM message_ai_runs WHERE correlation_id = ? ORDER BY created_at DESC LIMIT 1", ("trace-rank-e2e",))
        assert ai_run is not None
        assert ai_run["selected_variant"]
        assert int(ai_run["candidate_count"]) >= 3
        assert ai_run["ranking_version"] == "response_ranker_v1"

        candidates = fetch_all(conn, "SELECT * FROM response_candidate_rankings WHERE message_ai_run_id = ? ORDER BY candidate_index ASC", (ai_run["id"],))
        assert len(candidates) == int(ai_run["candidate_count"])
        assert sum(1 for row in candidates if int(row["selected"]) == 1) == 1
        assert any(row["variant_key"] == ai_run["selected_variant"] and int(row["selected"]) == 1 for row in candidates)

        exposure = fetch_one(conn, "SELECT * FROM outcome_exposures WHERE prompt_run_id = ? ORDER BY created_at DESC LIMIT 1", (result["execution_run"]["id"],))
        assert exposure is not None
        assert exposure["assigned_variant"] == ai_run["selected_variant"]
        conn.commit()

    outcome_event = client.post(
        "/api/v1/outcomes/events",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": "conv_activation",
            "contact_id": "ct_activation",
            "event_name": "appointment_scheduled",
            "event_category": "booking",
            "event_timestamp": "2026-04-17T13:00:00Z",
            "source_system": "appointments",
            "vertical": "fitness",
            "funnel_stage": "booking",
        },
    )
    assert outcome_event.status_code == 200

    recompute = client.post(
        "/api/v1/outcomes/recompute",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "scorecard_windows": ["28d"],
        },
    )
    assert recompute.status_code == 200

    selected_variant = None
    with get_connection() as conn:
        ai_run = fetch_one(conn, "SELECT * FROM message_ai_runs WHERE correlation_id = ? ORDER BY created_at DESC LIMIT 1", ("trace-rank-e2e",))
        selected_variant = ai_run["selected_variant"]

    scorecards = client.get(
        "/api/v1/outcomes/scorecards",
        headers=headers,
        params={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "entity_type": "response_variant",
            "entity_id": selected_variant,
            "scorecard_window": "28d",
        },
    )
    assert scorecards.status_code == 200
    items = scorecards.json()["data"]["items"]
    assert any(item["entity_id"] == selected_variant for item in items)
