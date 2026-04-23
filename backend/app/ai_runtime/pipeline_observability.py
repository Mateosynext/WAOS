from __future__ import annotations

import time
from typing import Any

from ..domain_events import emit_domain_event
from ..platform import append_technical_log
from ..telemetry_runtime import record_stage_metric
from ..world_class import finish_trace_span



def log_runtime_acceptance(
    conn,
    *,
    conversation: dict[str, Any],
    bot: dict[str, Any],
    run: dict[str, Any],
    incoming_message: dict[str, Any],
) -> None:
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="runtime",
        message="Inbound accepted by runtime pipeline",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details={"message_id": incoming_message["id"]},
    )


def record_orchestration_completion(
    conn,
    *,
    conversation: dict[str, Any],
    bot: dict[str, Any],
    run: dict[str, Any],
    orchestration_span_id: str,
    orchestration_started: float,
    effective_correlation_id: str | None,
    understanding: dict[str, Any],
) -> None:
    duration_ms = int((time.perf_counter() - orchestration_started) * 1000)
    finish_trace_span(
        conn,
        trace_id=run["trace_id"],
        span_id=orchestration_span_id,
        status="ok",
        attributes={"duration_ms": duration_ms, "stage": "orchestration"},
    )
    record_stage_metric(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        trace_id=run["trace_id"],
        correlation_id=effective_correlation_id,
        vertical=bot.get("vertical"),
        source_type="inbound_message",
        stage_name="pipeline.orchestration",
        duration_ms=duration_ms,
        metrics={"intent": (understanding.get("classification") or {}).get("intent")},
    )


def log_understanding_artifacts(
    conn,
    *,
    conversation: dict[str, Any],
    bot: dict[str, Any],
    run: dict[str, Any],
    incoming_message: dict[str, Any],
    classification: dict[str, Any],
    execution_plan: dict[str, Any],
    grounded_context: dict[str, Any],
    decision: dict[str, Any],
    specialist_route: dict[str, Any],
    supervisor: dict[str, Any],
    correlation_id: str | None,
) -> None:
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="classifier",
        message="Message classified",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details=classification,
    )
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="planner",
        message="Execution plan prepared",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details={
            "intent": execution_plan.get("intent"),
            "objectives": execution_plan.get("objectives"),
            "risk_flags": execution_plan.get("risk_flags"),
            "tool_orchestration": execution_plan.get("tool_orchestration"),
        },
    )
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="grounding",
        message="Grounded context assembled",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details={
            "source_count": grounded_context.get("source_count"),
            "coverage": grounded_context.get("coverage"),
            "grounding_mode": grounded_context.get("grounding_mode"),
        },
    )
    emit_domain_event(
        conn,
        event_name="message_classified",
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        message_id=incoming_message["id"],
        correlation_id=correlation_id,
        payload={"intent": classification.get("intent"), "source": classification.get("_classifier_source")},
    )
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="decision",
        message="Action decided",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details=decision,
    )
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="agent_router",
        message="Intent routed to specialist agent",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details={"route": specialist_route, "supervisor": supervisor},
    )


def log_response_artifacts(
    conn,
    *,
    conversation: dict[str, Any],
    bot: dict[str, Any],
    run: dict[str, Any],
    generated: dict[str, Any] | None,
    candidate_ranking: dict[str, Any] | None,
    verification: dict[str, Any] | None,
    post_send_evaluation: dict[str, Any],
) -> None:
    candidate_ranking = candidate_ranking or {}
    verification = verification or {}
    response_text = (generated or {}).get("text") or ""
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="generator",
        message="Response generated",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details={"preview": response_text[:160], "source": (generated or {}).get("source")},
    )
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="ranker",
        message="Multi-candidate ranking completed",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details=candidate_ranking.get("summary") or {"candidate_count": 0},
    )
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="verifier",
        message="Reply verified before send",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details=verification or {"status": "not_required"},
    )
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="evaluation",
        message="Post-send evaluation completed",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details=post_send_evaluation,
    )


def record_response_completion(
    conn,
    *,
    conversation: dict[str, Any],
    bot: dict[str, Any],
    run: dict[str, Any],
    response_span_id: str,
    response_stage_started: float,
    effective_correlation_id: str | None,
    generated: dict[str, Any] | None,
) -> None:
    duration_ms = int((time.perf_counter() - response_stage_started) * 1000)
    finish_trace_span(
        conn,
        trace_id=run["trace_id"],
        span_id=response_span_id,
        status="ok",
        attributes={"duration_ms": duration_ms, "stage": "response"},
    )
    record_stage_metric(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        trace_id=run["trace_id"],
        correlation_id=effective_correlation_id,
        vertical=bot.get("vertical"),
        source_type="inbound_message",
        stage_name="pipeline.response",
        duration_ms=duration_ms,
        metrics={"generator_source": (generated or {}).get("source")},
    )


def log_memory_curation(
    conn,
    *,
    conversation: dict[str, Any],
    bot: dict[str, Any],
    run: dict[str, Any],
    memory_curation: dict[str, Any],
) -> None:
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="info",
        category="memory_curator",
        message="Memory curation prepared",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details=memory_curation,
    )


def log_pipeline_exception(
    conn,
    *,
    conversation: dict[str, Any],
    bot: dict[str, Any],
    run: dict[str, Any],
    error: str,
) -> None:
    append_technical_log(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        execution_run_id=run["id"],
        conversation_id=conversation["id"],
        level="error",
        category="runtime",
        message="Pipeline exception",
        trace_id=run["trace_id"],
        execution_id=run["execution_id"],
        details={"error": error},
    )
