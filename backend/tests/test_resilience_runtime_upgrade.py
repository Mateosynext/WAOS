from __future__ import annotations

import pytest

from backend.app.backpressure import queue_depth_snapshot, resolve_failure_outcome
from backend.app.circuit_breaker import record_provider_failure
from backend.app.config import settings
from backend.app.db import execute, fetch_one, get_connection, init_db
from backend.app.rate_limiter import inbound_client_rate_limit
from backend.app.world_class_plus import module_health_checks, runtime_autoscaling_plan
from backend.tests.test_activation_foundations import _auth_headers


def test_resilience_failure_outcome_dead_letters_and_opens_circuit() -> None:
    init_db()
    with get_connection() as conn:
        record_provider_failure(conn, provider="openai", circuit_key="generation:test", error_text="timeout", organization_id="org_activation")
        record_provider_failure(conn, provider="openai", circuit_key="generation:test", error_text="timeout", organization_id="org_activation")
        opened = record_provider_failure(conn, provider="openai", circuit_key="generation:test", error_text="timeout", organization_id="org_activation")
        assert opened["state"] == "open"

        outcome = resolve_failure_outcome(
            conn,
            provider="automation_jobs",
            scope_key="bot_activation",
            attempts=3,
            max_attempts=3,
            organization_id="org_activation",
            channel="job",
            source_table="automation_jobs",
            source_id="job_resilience_dead",
            reason_code="job_execution_failed",
            payload_snapshot={"job_type": "followup"},
            error_payload={"error": "boom", "attempts": 3},
            metadata={"job_type": "followup"},
        )
        assert outcome["status"] == "dead_letter"
        dead_letter = fetch_one(conn, "SELECT * FROM dead_letter_events WHERE source_table = ? AND source_id = ?", ("automation_jobs", "job_resilience_dead"))
        assert dead_letter is not None


@pytest.mark.parametrize("count", [10, 80])
def test_backpressure_autoscaling_and_health_modules_are_granular(count: int) -> None:
    _auth_headers()
    with get_connection() as conn:
        for idx in range(count):
            execute(
                conn,
                """
                INSERT INTO automation_jobs (id, organization_id, bot_id, conversation_id, contact_id, job_type, dedupe_key, scheduled_for, status, attempts, payload_json, priority, last_error, locked_at, executed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', 0, '{}', 50, NULL, NULL, NULL, ?)
                """,
                (
                    f"job_bp_{count}_{idx}",
                    "org_activation",
                    "bot_activation",
                    "conv_activation",
                    "ct_activation",
                    "followup",
                    f"job-bp-{count}-{idx}",
                    "2026-01-02T00:00:00Z",
                    "2026-01-02T00:00:00Z",
                ),
            )
        execute(
            conn,
            "UPDATE integration_connections SET provider = 'stripe', health_status = 'degraded', status = 'active', last_error = 'provider_timeout' WHERE id = ?",
            ("int_activation",),
        )
        conn.commit()

        snapshot = queue_depth_snapshot(conn, organization_id="org_activation")
        auto = runtime_autoscaling_plan(conn, organization_id="org_activation")
        health = module_health_checks(conn, organization_id="org_activation")

    assert snapshot["jobs_queued"] >= count
    assert auto["autoscaling"]["desired_workers"] >= 1
    modules = {item["module"]: item for item in health["modules"]}
    assert {"database", "workers", "ai", "whatsapp", "payments", "graceful_degradation"}.issubset(modules.keys())
    assert modules["payments"]["detail"]["degraded_integrations"] >= 1


def test_inbound_defensive_rate_limiter_blocks_spam_before_crash() -> None:
    _auth_headers()
    with get_connection() as conn:
        for idx in range(settings.inbound_spam_max_events):
            state = inbound_client_rate_limit(
                conn,
                organization_id="org_activation",
                bot_id="bot_activation",
                phone="+5215559990000",
                metadata={"message_index": idx},
            )
            assert state["allowed"] is True

        blocked = inbound_client_rate_limit(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            phone="+5215559990000",
            metadata={"message_index": "blocked"},
        )
        assert blocked["allowed"] is False

