from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.ai import run_ai_pipeline
from backend.app.db import execute, fetch_one, get_connection, init_db
from backend.app.main import app
from backend.app.world_class import record_ai_usage
from backend.app.platform.runtime import compute_observability_overview
from backend.app.telemetry_runtime import (
    ai_cost_dashboard,
    pipeline_latency_dashboard,
    queue_depth_dashboard,
    record_queue_depth_sample,
)
from backend.app.utils import to_json
from backend.tests.test_activation_foundations import _auth_headers

client = TestClient(app)


def _seed_execution_runs_for_error_dashboard(conn) -> None:
    for idx in range(3):
        execute(
            conn,
                """
                INSERT INTO execution_runs (id, organization_id, bot_id, version_id, conversation_id, message_id, job_id, source_type, status, trace_id, execution_id, queue_name, attempt, input_json, output_json, error_json, started_at, finished_at, duration_ms, created_at)
                VALUES (?, ?, ?, NULL, ?, ?, NULL, 'inbound_message', ?, ?, ?, 'runtime.inbound', 1, '{}', '{}', '{}', ?, ?, ?, ?)
                """,
                (
                    f"exec_obs_{idx}",
                    "org_activation",
                    "bot_activation",
                    "conv_activation",
                    "msg_activation",
                    "failed" if idx == 0 else "completed",
                    f"trace_obs_{idx}",
                    f"run_obs_{idx}",
                    f"2026-01-02T00:0{idx}:00Z",
                    f"2026-01-02T00:0{idx}:03Z",
                    3000,
                    f"2026-01-02T00:0{idx}:00Z",
                ),
            )


def test_observability_dashboards_expose_latency_queue_and_ai_costs() -> None:
    headers = _auth_headers()
    init_db()
    with get_connection() as conn:
        execute(conn, "UPDATE bots SET config_draft_json = ? WHERE id = ?", (to_json({"identity": {"name": "WAOS"}, "objective": {"primary": "Responder"}}), "bot_activation"))
        inbound = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", ("msg_activation",))
        conversation = fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", ("conv_activation",))
        bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ?", ("bot_activation",))
        contact = fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", ("ct_activation",))
        memory = fetch_one(conn, "SELECT * FROM contact_memory WHERE bot_id = ? AND contact_id = ?", ("bot_activation", "ct_activation"))
        result = run_ai_pipeline(conn, incoming_message=inbound, conversation=conversation, bot=bot, contact=contact, memory=memory, correlation_id="trace-observability-e2e")
        assert result["execution_run"]["trace_id"] == "trace-observability-e2e"

        record_ai_usage(conn, organization_id="org_activation", bot_id="bot_activation", conversation_id="conv_activation", model="gpt-4o-mini", operation="generation", prompt_tokens=120, completion_tokens=40, latency_ms=420, cache_hit=False, metadata={"source": "test-observability"})

        record_queue_depth_sample(
            conn,
            organization_id="org_activation",
            snapshot={"jobs_queued": 120, "outbox_queued": 4, "integrations_due": 1, "callbacks_pending": 0, "queue_pressure": 125, "oldest_age_seconds": 320},
            metadata={"source": "test"},
        )
        _seed_execution_runs_for_error_dashboard(conn)
        conn.commit()

        overview = compute_observability_overview(conn, organization_id="org_activation", bot_id="bot_activation")
        assert overview["dashboards"]["latency"]["stages"]
        assert overview["dashboards"]["queues"]["latest"]["total_depth"] >= 125
        assert overview["dashboards"]["ai_costs"]["conversations"]

        latency = pipeline_latency_dashboard(conn, organization_id="org_activation", bot_id="bot_activation", minutes=60)
        assert any(stage["stage_name"] == "pipeline.total" for stage in latency["stages"])

        costs = ai_cost_dashboard(conn, organization_id="org_activation", bot_id="bot_activation", limit=20)
        assert costs["conversations"][0]["conversation_id"] == "conv_activation"

        queue = queue_depth_dashboard(conn, organization_id="org_activation", minutes=60)
        assert queue["latest"]["oldest_age_seconds"] >= 320

    response = client.get("/api/v1/observability/overview", params={"organization_id": "org_activation", "bot_id": "bot_activation"}, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["dashboards"]["latency"]["stages"]
    assert payload["dashboards"]["ai_costs"]["conversations"]



def test_ai_dashboard_includes_costs_by_conversation_and_apm_block() -> None:
    headers = _auth_headers()
    init_db()
    response = client.get("/api/v1/ai/dashboard", params={"organization_id": "org_activation", "bot_id": "bot_activation"}, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert "costs_by_conversation" in payload
    assert "apm" in payload
