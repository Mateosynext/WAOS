from __future__ import annotations

import time
from typing import Any

from ..utils import new_id
from ..world_class import start_trace_span
from .persistence import (
    finalize_pipeline_run,
    load_pipeline_context,
    persist_decision_outcome,
    persist_pipeline_artifacts,
    persist_specialist_route_artifacts,
)
from .pipeline_observability import (
    log_memory_curation,
    log_pipeline_exception,
    log_response_artifacts,
    log_runtime_acceptance,
    log_understanding_artifacts,
    record_orchestration_completion,
    record_response_completion,
)


def run_ai_pipeline(
    conn,
    *,
    incoming_message: dict,
    conversation: dict,
    bot: dict,
    contact: dict,
    memory: dict,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    pipeline_started = time.perf_counter()
    context = load_pipeline_context(
        conn,
        incoming_message=incoming_message,
        conversation=conversation,
        bot=bot,
        memory=memory,
        correlation_id=correlation_id,
    )
    effective_correlation_id = context["effective_correlation_id"]
    bot_config = context["bot_config"]
    recent_messages = context["recent_messages"]
    recent_voice_notes = context["recent_voice_notes"]
    language_config = context["language_config"]
    classification_input = context["classification_input"]
    run = context["run"]

    log_runtime_acceptance(
        conn,
        conversation=conversation,
        bot=bot,
        run=run,
        incoming_message=incoming_message,
    )

    orchestration_span_id = new_id("span")
    start_trace_span(
        conn,
        trace_id=run["trace_id"],
        span_id=orchestration_span_id,
        parent_span_id=None,
        name="pipeline.orchestration",
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        execution_run_id=run["id"],
        correlation_id=effective_correlation_id,
        attributes={"stage": "orchestration", "source_type": "inbound_message"},
    )
    orchestration_started = time.perf_counter()

    from .orchestration import orchestrate_runtime_turn

    orchestrated = orchestrate_runtime_turn(
        text=incoming_message["body"],
        conversation=conversation,
        bot=bot,
        memory=memory,
        bot_config=bot_config,
        recent_messages=recent_messages,
        conn=conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        contact_id=contact["id"],
        conversation_id=conversation["id"],
        recent_voice_notes=recent_voice_notes,
        language_config=language_config,
    )
    understanding = orchestrated["understanding"]
    classification = understanding["classification"]
    grounded_context = orchestrated["grounded_context"]
    specialist_route = orchestrated.get("specialist_route") or {}
    shared_memory = orchestrated.get("shared_memory") or {}
    execution_plan = orchestrated["plan"]
    decision = orchestrated["decision"]
    supervisor = orchestrated.get("supervisor") or {}
    generated = orchestrated.get("generated")
    verification = orchestrated.get("verification") or {}
    candidate_ranking = orchestrated.get("candidate_ranking") or {}
    memory_curation = orchestrated.get("memory_curation") or {}
    post_send_evaluation = orchestrated.get("post_send_evaluation") or {}
    self_state = orchestrated.get("self_state") or {"turn": {}, "conversation": {}}

    record_orchestration_completion(
        conn,
        conversation=conversation,
        bot=bot,
        run=run,
        orchestration_span_id=orchestration_span_id,
        orchestration_started=orchestration_started,
        effective_correlation_id=effective_correlation_id,
        understanding=understanding,
    )

    decision_input = {
        "conversation_state": {
            "status": conversation["status"],
            "human_takeover": conversation["human_takeover"],
            "ai_active": conversation["ai_active"],
        },
        "classification": classification,
        "memory": {
            "lead_stage": memory.get("lead_stage"),
            "lead_score": memory.get("lead_score"),
        },
        "plan": execution_plan,
        "grounded_context": {
            "source_count": grounded_context.get("source_count"),
            "coverage": grounded_context.get("coverage"),
        },
        "self_state": self_state,
    }
    log_understanding_artifacts(
        conn,
        conversation=conversation,
        bot=bot,
        run=run,
        incoming_message=incoming_message,
        classification=classification,
        execution_plan=execution_plan,
        grounded_context=grounded_context,
        decision=decision,
        specialist_route=specialist_route,
        supervisor=supervisor,
        correlation_id=correlation_id,
    )

    ai_run_id = new_id("airun")
    generator_input = {
        "execution_plan": execution_plan,
        "grounded_context": grounded_context,
        "memory_curation": memory_curation,
    }
    generator_output: dict[str, Any] = {}
    response_message = None
    error = None
    updated_memory = memory
    jobs: list[dict[str, Any]] = []

    try:
        response_span_id: str | None = None
        response_stage_started: float | None = None
        if decision["action"] in {"respond", "respond_and_schedule_followup", "verify", "request_missing_data"}:
            response_span_id = new_id("span")
            response_stage_started = time.perf_counter()
            start_trace_span(
                conn,
                trace_id=run["trace_id"],
                span_id=response_span_id,
                parent_span_id=None,
                name="pipeline.response",
                organization_id=conversation["organization_id"],
                bot_id=bot["id"],
                conversation_id=conversation["id"],
                execution_run_id=run["id"],
                correlation_id=effective_correlation_id,
                attributes={"stage": "response"},
            )
            generator_input = {
                **generator_input,
                "payload": (generated or {}).get("payload") or {},
                "verification": verification,
                "candidate_ranking": candidate_ranking,
                "post_send_evaluation": post_send_evaluation,
                "self_state": self_state,
            }
            log_response_artifacts(
                conn,
                conversation=conversation,
                bot=bot,
                run=run,
                generated=generated,
                candidate_ranking=candidate_ranking,
                verification=verification,
                post_send_evaluation=post_send_evaluation,
            )

        log_memory_curation(
            conn,
            conversation=conversation,
            bot=bot,
            run=run,
            memory_curation=memory_curation,
        )
        action_result = persist_decision_outcome(
            conn,
            run=run,
            incoming_message=incoming_message,
            conversation=conversation,
            bot=bot,
            contact=contact,
            memory=memory,
            bot_config=bot_config,
            recent_messages=recent_messages,
            classification=classification,
            decision=decision,
            generated=generated,
            verification=verification,
            candidate_ranking=candidate_ranking,
            post_send_evaluation=post_send_evaluation,
            memory_curation=memory_curation,
            self_state=self_state,
            execution_plan=execution_plan,
            correlation_id=correlation_id,
        )
        generator_output = action_result["generator_output"]
        response_message = action_result["response_message"]
        updated_memory = action_result["updated_memory"] or memory
        jobs = action_result["jobs"] or []
        if response_span_id and response_stage_started is not None:
            record_response_completion(
                conn,
                conversation=conversation,
                bot=bot,
                run=run,
                response_span_id=response_span_id,
                response_stage_started=response_stage_started,
                effective_correlation_id=effective_correlation_id,
                generated=generated,
            )
        status = "completed"
    except Exception as exc:
        error = str(exc)
        decision = {"action": "error", "reason": "pipeline_exception"}
        status = "failed"
        log_pipeline_exception(
            conn,
            conversation=conversation,
            bot=bot,
            run=run,
            error=error,
        )

    persist_specialist_route_artifacts(
        conn,
        conversation=conversation,
        bot=bot,
        contact=contact,
        incoming_message=incoming_message,
        run=run,
        classification=classification,
        specialist_route=specialist_route,
        shared_memory=shared_memory,
        execution_plan=execution_plan,
        supervisor=supervisor,
        status=status,
        decision=decision,
        candidate_ranking=candidate_ranking,
        response_message=response_message,
    )

    persist_pipeline_artifacts(
        conn,
        ai_run_id=ai_run_id,
        incoming_message=incoming_message,
        conversation=conversation,
        bot=bot,
        classification_input=classification_input,
        classification=classification,
        decision_input=decision_input,
        decision=decision,
        generator_input=generator_input,
        generator_output=generator_output,
        error=error,
        effective_correlation_id=effective_correlation_id,
        candidate_ranking=candidate_ranking,
        verification=verification,
        grounded_context=grounded_context,
        execution_plan=execution_plan,
        post_send_evaluation=post_send_evaluation,
        memory_curation=memory_curation,
        self_state=self_state,
    )

    total_duration_ms = int((time.perf_counter() - pipeline_started) * 1000)
    finished_run = finalize_pipeline_run(
        conn,
        run=run,
        conversation=conversation,
        bot=bot,
        effective_correlation_id=effective_correlation_id,
        total_duration_ms=total_duration_ms,
        status=status,
        error=error,
        decision=decision,
        classification=classification,
        execution_plan=execution_plan,
        grounded_context=grounded_context,
        verification=verification,
        candidate_ranking=candidate_ranking,
        post_send_evaluation=post_send_evaluation,
        self_state=self_state,
        response_message=response_message,
        jobs=jobs,
        incoming_message=incoming_message,
    )
    return {
        "classification": classification,
        "grounded_context": grounded_context,
        "plan": execution_plan,
        "decision": decision,
        "verification": verification,
        "post_send_evaluation": post_send_evaluation,
        "self_state": self_state,
        "response_message": response_message,
        "updated_memory": updated_memory,
        "jobs": jobs,
        "error": error,
        "execution_run": finished_run,
    }
