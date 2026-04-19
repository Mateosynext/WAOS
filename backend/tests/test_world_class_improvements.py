from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_one, get_connection, init_db
from backend.app.main import app
from backend.app.platform.runtime import append_technical_log
from backend.app.utils import new_id
from backend.app.world_class import (
    circuit_breaker_summary,
    circuit_record_failure,
    circuit_record_success,
    consume_retry_budget,
    finish_trace_span,
    record_ai_usage,
    record_dead_letter_event,
    record_revenue_event,
    search_memory_vectors,
    start_trace_span,
    summarize_ai_usage,
    trace_timeline,
    upsert_memory_vector,
)
from backend.app.world_class_plus import append_immutable_audit_event, compliance_overview, consume_defensive_rate_limit, runtime_autoscaling_plan
from backend.app.world_class_ext import authenticate_public_api_credential, create_shadow_run, issue_public_api_credential, register_channel_event
from backend.tests.test_activation_foundations import _auth_headers


client = TestClient(app)


def test_retry_budget_and_circuit_breaker_lifecycle() -> None:
    init_db()
    with get_connection() as conn:
        circuit_record_failure(conn, provider="openai", circuit_key="bot_activation", error_text="timeout")
        circuit_record_failure(conn, provider="openai", circuit_key="bot_activation", error_text="timeout")
        opened = circuit_record_failure(conn, provider="openai", circuit_key="bot_activation", error_text="timeout")
        assert opened["state"] == "open"
        assert circuit_breaker_summary(conn, provider="openai")["open"] >= 1

        budget_1 = consume_retry_budget(conn, provider="meta_whatsapp", scope_key="org_activation:outbox", max_retries=2)
        budget_2 = consume_retry_budget(conn, provider="meta_whatsapp", scope_key="org_activation:outbox", max_retries=2)
        budget_3 = consume_retry_budget(conn, provider="meta_whatsapp", scope_key="org_activation:outbox", max_retries=2)
        assert budget_1["allowed"] is True
        assert budget_2["allowed"] is True
        assert budget_3["allowed"] is False

        closed = circuit_record_success(conn, provider="openai", circuit_key="bot_activation")
        assert closed["state"] == "closed"


def test_ai_usage_memory_and_trace_helpers() -> None:
    init_db()
    with get_connection() as conn:
        record_ai_usage(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            model="gpt-4o-mini",
            operation="generation",
            prompt_tokens=100,
            completion_tokens=40,
            latency_ms=321,
            cache_hit=False,
            metadata={"source": "test"},
        )
        usage = summarize_ai_usage(conn, organization_id="org_activation", bot_id="bot_activation")
        assert usage["totals"]["events"] >= 1
        assert usage["totals"]["estimated_cost"] > 0

        upsert_memory_vector(
            conn,
            organization_id="org_activation",
            contact_id="ct_activation",
            bot_id="bot_activation",
            scope="facts",
            content_text="Cliente prefiere cita por la tarde y pagar por Stripe",
            metadata={"source": "test"},
        )
        memory_hits = search_memory_vectors(
            conn,
            organization_id="org_activation",
            contact_id="ct_activation",
            bot_id="bot_activation",
            query="prefiere cita en la tarde",
        )
        assert memory_hits
        assert "tarde" in memory_hits[0]["content_text"]

        trace_id = new_id("trace")
        start_trace_span(
            conn,
            trace_id=trace_id,
            span_id="span-test-1",
            parent_span_id=None,
            name="runtime.test",
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            attributes={"phase": "start"},
        )
        finish_trace_span(conn, trace_id=trace_id, span_id="span-test-1", status="ok", attributes={"phase": "end"})
        timeline = trace_timeline(conn, trace_id=trace_id)
        assert timeline["spans"]
        assert timeline["spans"][0]["status"] == "ok"


def test_runtime_world_class_endpoints_and_dead_letter_registry() -> None:
    headers = _auth_headers()
    init_db()
    with get_connection() as conn:
        record_ai_usage(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            model="gpt-4o-mini",
            operation="classification",
            prompt_tokens=12,
            completion_tokens=8,
            latency_ms=90,
            cache_hit=True,
            metadata={"source": "endpoint-test"},
        )
        record_revenue_event(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            contact_id="ct_activation",
            event_type="abandoned_quote",
            recommendation={"action": "follow_up"},
            expected_value=1500,
        )
        append_technical_log(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            execution_run_id=None,
            conversation_id="conv_activation",
            level="info",
            category="runtime",
            message="traceable world class test log",
            trace_id="trace-endpoint-test",
            execution_id="exec-endpoint-test",
            details={"kind": "searchable"},
        )
        start_trace_span(
            conn,
            trace_id="trace-endpoint-test",
            span_id="span-endpoint-test",
            parent_span_id=None,
            name="http:test",
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            attributes={"from": "endpoint"},
        )
        finish_trace_span(conn, trace_id="trace-endpoint-test", span_id="span-endpoint-test", status="ok")

        row = fetch_one(conn, "SELECT * FROM automation_jobs WHERE id = ?", ("job_world_class_dead",))
        if not row:
            execute(
                conn,
                """
                INSERT INTO automation_jobs (id, organization_id, bot_id, conversation_id, contact_id, job_type, dedupe_key, scheduled_for, status, attempts, payload_json, priority, last_error, locked_at, executed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'dead_letter', 3, ?, 50, 'timeout', NULL, NULL, ?)
                """,
                (
                    "job_world_class_dead",
                    "org_activation",
                    "bot_activation",
                    "conv_activation",
                    "ct_activation",
                    "followup",
                    "world-class-dead-letter",
                    "2026-01-02T00:00:00Z",
                    '{"max_attempts": 3}',
                    "2026-01-02T00:00:00Z",
                ),
            )
        record_dead_letter_event(
            conn,
            organization_id="org_activation",
            channel="job",
            source_table="automation_jobs",
            source_id="job_world_class_dead",
            reason_code="provider_retry_budget_exhausted",
            payload_snapshot={"job_type": "followup"},
            error_payload={"message": "timeout"},
        )
        conn.commit()

    ai_dashboard = client.get("/api/v1/ai/dashboard", params={"organization_id": "org_activation", "bot_id": "bot_activation"}, headers=headers)
    assert ai_dashboard.status_code == 200
    ai_payload = ai_dashboard.json()
    assert ai_payload["usage"]["totals"]["events"] >= 1
    assert ai_payload["revenue"]["totals"]["events"] >= 1

    logs = client.get("/api/v1/logs/search", params={"organization_id": "org_activation", "q": "traceable world class"}, headers=headers)
    assert logs.status_code == 200
    assert logs.json()["data"]

    trace = client.get("/api/v1/traces/trace-endpoint-test", params={"organization_id": "org_activation"}, headers=headers)
    assert trace.status_code == 200
    assert trace.json()["data"]["spans"]

    dead_letters = client.get("/api/v1/operations/dead-letters", params={"organization_id": "org_activation"}, headers=headers)
    assert dead_letters.status_code == 200
    assert any(item["id"] == "job_world_class_dead" and item["dead_letter_event"] for item in dead_letters.json()["jobs"])


def test_omnichannel_public_api_shadow_and_prompt_analytics() -> None:
    headers = _auth_headers()
    init_db()
    with get_connection() as conn:
        credential = issue_public_api_credential(conn, organization_id="org_activation", name="SDK test", scopes=["channels.write", "channels.read"])
        assert authenticate_public_api_credential(conn, organization_id="org_activation", token=credential["token"], required_scope="channels.write")
        event = register_channel_event(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            channel="telegram",
            direction="inbound",
            event_type="message",
            body="Hola desde Telegram",
            identities=[{"type": "phone", "value": "+5215550001111"}, {"type": "email", "value": "cliente@example.com"}],
            metadata={"source": "unit-test"},
        )
        assert event["channel"] == "telegram"
        shadow = create_shadow_run(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            experiment_key="draft-vs-published",
            production_output={"reply": "Hola, ¿cómo te ayudo?"},
            candidate_output={"reply": "Hola, te ayudo a cerrar tu cita hoy"},
        )
        assert shadow["verdict"] in {"pass", "review"}
        conn.commit()

    omni = client.get("/api/v1/omnichannel/overview", params={"organization_id": "org_activation", "bot_id": "bot_activation"}, headers=headers)
    assert omni.status_code == 200
    omni_payload = omni.json()
    assert omni_payload["summary"]["channels"]
    assert any(item["channel"] == "telegram" for item in omni_payload["summary"]["channels"])

    credential_issue = client.post("/api/v1/public-api/credentials", json={"organization_id": "org_activation", "name": "Ops key", "scopes": ["channels.write"]}, headers=headers)
    assert credential_issue.status_code == 200
    public_token = credential_issue.json()["data"]["token"]

    manifest = client.get("/api/public/sdk/manifest")
    assert manifest.status_code == 200
    assert manifest.json()["endpoints"]

    public_ingest = client.post(
        "/api/public/v1/channels/events",
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "channel": "instagram_dm",
            "direction": "inbound",
            "event_type": "message",
            "body": "Hola desde Instagram",
            "identities": [{"type": "phone", "value": "+5215550001111"}],
        },
        headers={"X-WAOS-Public-Key": public_token},
    )
    assert public_ingest.status_code == 200
    assert public_ingest.json()["data"]["channel"] == "instagram_dm"

    prompt_create = client.post(
        "/api/v1/prompts/artifacts",
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "artifact_type": "experiment",
            "artifact_key": "pricing-close-v1",
            "title": "Pricing close",
            "body": "Usa cierre consultivo con urgencia moderada",
            "metadata": {"owner": "qa"},
        },
        headers=headers,
    )
    assert prompt_create.status_code == 200

    prompt_analytics = client.get("/api/v1/prompts/analytics", params={"organization_id": "org_activation", "bot_id": "bot_activation"}, headers=headers)
    assert prompt_analytics.status_code == 200
    assert prompt_analytics.json()["data"]["summary"]["artifacts"] >= 1

    shadow_endpoint = client.post(
        "/api/v1/shadow/runs",
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": "conv_activation",
            "experiment_key": "regression-shadow",
            "production_output": {"reply": "A"},
            "candidate_output": {"reply": "B"},
        },
        headers=headers,
    )
    assert shadow_endpoint.status_code == 200

    shadow_over = client.get("/api/v1/shadow/overview", params={"organization_id": "org_activation"}, headers=headers)
    assert shadow_over.status_code == 200
    assert shadow_over.json()["data"]["totals"]["runs"] >= 1


def test_otel_export_queue_endpoints() -> None:
    headers = _auth_headers()
    init_db()
    with get_connection() as conn:
        start_trace_span(
            conn,
            trace_id="trace-otel-test",
            span_id="span-otel-test",
            parent_span_id=None,
            name="runtime.otel",
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            attributes={"kind": "otlp"},
        )
        finish_trace_span(conn, trace_id="trace-otel-test", span_id="span-otel-test", status="ok")
        conn.commit()

    overview = client.get("/api/v1/observability/otel", params={"organization_id": "org_activation"}, headers=headers)
    assert overview.status_code == 200
    totals = overview.json()["data"]["totals"]
    assert totals["pending"] >= 1 or totals["exported"] >= 1

    flush = client.post("/api/v1/observability/otel/flush", params={"organization_id": "org_activation", "dry_run": True}, headers=headers)
    assert flush.status_code == 200
    assert flush.json()["data"]["dry_run"] is True



def test_world_class_plus_compliance_quality_and_revenue_endpoints() -> None:
    headers = _auth_headers()
    init_db()
    with get_connection() as conn:
        append_technical_log(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            execution_run_id=None,
            conversation_id="conv_activation",
            level="info",
            category="quality",
            message="load test seeded",
            trace_id="trace-quality-seed",
            execution_id="exec-quality-seed",
            details={"phase": "seed"},
        )
        conn.commit()

    autoscaling = client.get('/api/v1/runtime/autoscaling', params={'organization_id': 'org_activation'}, headers=headers)
    assert autoscaling.status_code == 200
    assert autoscaling.json()['data']['autoscaling']['desired_workers'] >= 1

    module_health = client.get('/api/v1/runtime/health/modules', params={'organization_id': 'org_activation'}, headers=headers)
    assert module_health.status_code == 200
    assert module_health.json()['data']['modules']

    deletion = client.post('/api/v1/compliance/deletion-workflows', json={'organization_id': 'org_activation', 'subject_type': 'contact', 'subject_id': 'ct_activation', 'reason': 'user request'}, headers=headers)
    assert deletion.status_code == 200
    assert deletion.json()['data']['target_stores']

    compliance = client.get('/api/v1/compliance/overview', params={'organization_id': 'org_activation'}, headers=headers)
    assert compliance.status_code == 200
    compliance_payload = compliance.json()['data']
    assert compliance_payload['posture']['encrypted_backups'] is True
    assert compliance_payload['governance']['immutable_audit_events'] >= 1

    chaos = client.post('/api/v1/quality/chaos-runs', json={'organization_id': 'org_activation', 'scenario_key': 'openai-timeout', 'target': 'openai', 'status': 'passed', 'findings': {'fallback': 'heuristic'}}, headers=headers)
    assert chaos.status_code == 200

    load = client.post('/api/v1/quality/load-tests', json={'organization_id': 'org_activation', 'scenario_key': 'burst-inbound', 'target_rps': 80, 'peak_rps': 120, 'p95_ms': 420, 'error_rate': 0.01, 'queue_depth': 14, 'status': 'passed'}, headers=headers)
    assert load.status_code == 200

    chaos_over = client.get('/api/v1/quality/chaos-overview', params={'organization_id': 'org_activation'}, headers=headers)
    assert chaos_over.status_code == 200
    assert chaos_over.json()['data']['summary']['runs'] >= 1

    load_over = client.get('/api/v1/quality/load-overview', params={'organization_id': 'org_activation'}, headers=headers)
    assert load_over.status_code == 200
    assert load_over.json()['data']['summary']['best_peak_rps'] >= 120

    revenue = client.get('/api/v1/revenue/optimization', params={'organization_id': 'org_activation', 'bot_id': 'bot_activation'}, headers=headers)
    assert revenue.status_code == 200
    revenue_payload = revenue.json()['data']
    assert revenue_payload['summary']['recommended_actions'] >= 1
    assert any(item['type'] in {'payment_recovery', 'abandoned_cart_recovery', 'dynamic_pricing', 'smart_followup'} for item in revenue_payload['actions'])


def test_public_ingest_rate_limit_unified_inbox_and_prompt_experiments() -> None:
    headers = _auth_headers()
    init_db()
    credential_issue = client.post('/api/v1/public-api/credentials', json={'organization_id': 'org_activation', 'name': 'Public ingress', 'scopes': ['channels.write', 'channels.read']}, headers=headers)
    assert credential_issue.status_code == 200
    public_token = credential_issue.json()['data']['token']

    prompt_experiment = client.post('/api/v1/prompts/experiments', json={'organization_id': 'org_activation', 'bot_id': 'bot_activation', 'experiment_key': 'greeting-ab', 'artifact_a_key': 'draft_a', 'artifact_b_key': 'draft_b', 'rollout_percentage': 40}, headers=headers)
    assert prompt_experiment.status_code == 200

    assignment = client.get('/api/v1/prompts/experiments/greeting-ab/assignment', params={'organization_id': 'org_activation', 'conversation_id': 'conv_activation'}, headers=headers)
    assert assignment.status_code == 200
    assert assignment.json()['data']['assigned_variant'] in {'A', 'B'}

    experiments = client.get('/api/v1/prompts/experiments', params={'organization_id': 'org_activation', 'bot_id': 'bot_activation'}, headers=headers)
    assert experiments.status_code == 200
    assert experiments.json()['data']['summary']['experiments'] >= 1

    for idx in range(5):
        response = client.post(
            '/api/public/v1/channels/events',
            json={
                'organization_id': 'org_activation',
                'bot_id': 'bot_activation',
                'conversation_id': 'conv_activation',
                'channel': 'instagram_dm',
                'direction': 'inbound',
                'event_type': 'message',
                'body': f'Mensaje {idx}',
                'external_user_id': 'ig-user-1',
                'identities': [{'type': 'email', 'value': 'cliente@example.com'}],
            },
            headers={'X-WAOS-Public-Key': public_token},
        )
        assert response.status_code == 200

    limited = client.post(
        '/api/public/v1/channels/events',
        json={
            'organization_id': 'org_activation',
            'bot_id': 'bot_activation',
            'conversation_id': 'conv_activation',
            'channel': 'instagram_dm',
            'direction': 'inbound',
            'event_type': 'message',
            'body': 'Mensaje rate limited',
            'external_user_id': 'ig-user-1',
            'identities': [{'type': 'email', 'value': 'cliente@example.com'}],
        },
        headers={'X-WAOS-Public-Key': public_token},
    )
    assert limited.status_code == 429

    unified = client.get('/api/v1/unified-inbox/overview', params={'organization_id': 'org_activation', 'bot_id': 'bot_activation'}, headers=headers)
    assert unified.status_code == 200
    unified_payload = unified.json()['data']
    assert unified_payload['summary']['threads'] >= 1
    assert any('instagram_dm' in item['channels'] for item in unified_payload['threads'])



def test_direct_plus_helpers_work() -> None:
    init_db()
    with get_connection() as conn:
        rate_a = consume_defensive_rate_limit(conn, organization_id='org_activation', scope_key='scope:test', channel='webchat')
        rate_b = consume_defensive_rate_limit(conn, organization_id='org_activation', scope_key='scope:test', channel='webchat')
        rate_c = consume_defensive_rate_limit(conn, organization_id='org_activation', scope_key='scope:test', channel='webchat', max_events=2)
        assert rate_a['allowed'] is True
        assert rate_b['allowed'] is True
        assert rate_c['allowed'] is False

        ledger = append_immutable_audit_event(conn, organization_id='org_activation', event_type='test.audit', entity_type='unit', entity_id='unit_1', payload={'ok': True})
        assert ledger['entry_hash']

        posture = compliance_overview(conn, organization_id='org_activation')
        assert posture['posture']['data_region']

        autoscaling = runtime_autoscaling_plan(conn, organization_id='org_activation')
        assert autoscaling['autoscaling']['desired_workers'] >= 1
