from __future__ import annotations

from typing import Any

from ..contact_intelligence import relationship_snapshot
from ..db import execute, fetch_all, has_column, table_exists
from ..domain_events import emit_domain_event
from ..domains.language import get_language_config
from ..knowledge_runtime import sync_config_knowledge
from ..platform import finish_execution_run, start_execution_run
from ..repositories import create_audit_log, create_message
from ..repositories.ai_runtime import (
    create_message_ai_run,
    create_message_operational_reasoning,
    create_response_candidate_ranking,
)
from ..talent_runtime import maybe_register_candidate_confirmation
from ..telemetry_runtime import record_stage_metric
from ..utils import add_minutes, from_json, utcnow_iso
from ..world_class import index_bot_knowledge, maybe_create_conversation_checkpoint
from .memory import update_memory
from .post_send import maybe_schedule_followups


def load_pipeline_context(
    conn,
    *,
    incoming_message: dict[str, Any],
    conversation: dict[str, Any],
    bot: dict[str, Any],
    memory: dict[str, Any],
    correlation_id: str | None,
) -> dict[str, Any]:
    message_metadata = from_json(incoming_message.get("metadata_json"), {}) if incoming_message.get("metadata_json") else {}
    effective_correlation_id = correlation_id or incoming_message.get("correlation_id") or message_metadata.get("correlation_id")
    trace_seed = message_metadata.get("trace_id") or effective_correlation_id
    bot_config = from_json(bot["config_draft_json"], {})
    index_bot_knowledge(conn, organization_id=conversation["organization_id"], bot_id=bot["id"], bot_config=bot_config)
    sync_config_knowledge(conn, organization_id=conversation["organization_id"], bot_id=bot["id"], bot_config=bot_config)
    recent_messages = fetch_all(
        conn,
        "SELECT direction, body, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation["id"],),
    )
    recent_voice_notes = fetch_all(
        conn,
        "SELECT transcript, summary, detected_language, intent, urgency_level, emotion, transcription_confidence, audio_quality, background_noise_level, processing_status, reply_mode, created_at FROM voice_notes WHERE bot_id = ? AND conversation_id = ? ORDER BY created_at DESC LIMIT 3",
        (bot["id"], conversation["id"]),
    )
    language_config = get_language_config(conn, conversation["organization_id"], bot["id"])
    classification_input = {
        "message": incoming_message["body"],
        "memory": memory,
        "relationship_intelligence": relationship_snapshot(memory),
        "bot_identity": bot_config.get("identity", {}),
        "objective": bot_config.get("objective", {}),
        "language_context": {
            "default_language": language_config.get("default_language"),
            "supported_languages": language_config.get("supported_languages", []),
        },
        "voice_context": [
            {
                "summary": item.get("summary"),
                "detected_language": item.get("detected_language"),
                "intent": item.get("intent"),
                "urgency_level": item.get("urgency_level"),
                "emotion": item.get("emotion"),
            }
            for item in recent_voice_notes
        ],
    }
    run = start_execution_run(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        version_id=bot.get("published_version_id"),
        conversation_id=conversation["id"],
        message_id=incoming_message["id"],
        job_id=None,
        source_type="inbound_message",
        queue_name="runtime.inbound",
        input_payload=classification_input,
        trace_id=trace_seed,
        correlation_id=effective_correlation_id,
    )
    return {
        "message_metadata": message_metadata,
        "effective_correlation_id": effective_correlation_id,
        "bot_config": bot_config,
        "recent_messages": recent_messages,
        "recent_voice_notes": recent_voice_notes,
        "language_config": language_config,
        "classification_input": classification_input,
        "run": run,
    }


def persist_decision_outcome(
    conn,
    *,
    run: dict[str, Any],
    incoming_message: dict[str, Any],
    conversation: dict[str, Any],
    bot: dict[str, Any],
    contact: dict[str, Any],
    memory: dict[str, Any],
    bot_config: dict[str, Any],
    recent_messages: list[dict[str, Any]],
    classification: dict[str, Any],
    decision: dict[str, Any],
    generated: dict[str, Any] | None,
    verification: dict[str, Any] | None,
    candidate_ranking: dict[str, Any] | None,
    post_send_evaluation: dict[str, Any],
    memory_curation: dict[str, Any],
    self_state: dict[str, Any],
    execution_plan: dict[str, Any],
    correlation_id: str | None,
) -> dict[str, Any]:
    from ..self_state_runtime import maybe_trigger_self_state_playbook, persist_self_state

    verification = verification or {}
    candidate_ranking = candidate_ranking or {}
    persist_self_state(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        contact_id=contact["id"],
        message_id=incoming_message["id"],
        turn_self_state=self_state.get("turn") or {},
        conversation_self_state=self_state.get("conversation") or {},
    )

    response_message = None
    generator_output: dict[str, Any] = {}
    action = decision["action"]

    if action == "handoff":
        execute(
            conn,
            """
            UPDATE conversations
            SET status = 'human_takeover', human_takeover = 1, ai_active = 0, automation_freeze_until = ?, updated_at = ?
            WHERE id = ?
            """,
            (add_minutes(utcnow_iso(), 30), utcnow_iso(), conversation["id"]),
        )
        emit_domain_event(
            conn,
            event_name="handoff_triggered",
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            conversation_id=conversation["id"],
            message_id=incoming_message["id"],
            correlation_id=correlation_id,
            payload={"reason": decision.get("reason"), "action": action},
        )
        response_message = create_message(
            conn,
            organization_id=conversation["organization_id"],
            conversation_id=conversation["id"],
            contact_id=contact["id"],
            bot_id=bot["id"],
            direction="outbound",
            kind="text",
            source="system",
            body="He marcado esta conversación para atención humana.",
            status="internal",
            metadata={"reason": decision.get("reason"), "trace_id": run["trace_id"], "execution_id": run["execution_id"]},
        )
        generator_output = {"self_state": self_state}
    elif action in {"respond", "respond_and_schedule_followup", "verify", "request_missing_data"}:
        response_text = (generated or {}).get("text") or ""
        classification["_generator_source"] = (generated or {}).get("source")
        classification["_verifier_status"] = verification.get("status")
        generator_output = {
            "text": response_text,
            "raw_text": (generated or {}).get("raw_text"),
            "source": (generated or {}).get("source"),
            "selected_variant": candidate_ranking.get("selected_variant"),
            "candidate_ranking": candidate_ranking,
            "verification": verification,
            "post_send_evaluation": post_send_evaluation,
        }
        response_message = create_message(
            conn,
            organization_id=conversation["organization_id"],
            conversation_id=conversation["id"],
            contact_id=contact["id"],
            bot_id=bot["id"],
            direction="outbound",
            kind="text",
            source="ai",
            body=response_text,
            status="simulated",
            metadata={
                "provider": "simulated",
                "trace_id": run["trace_id"],
                "execution_id": run["execution_id"],
                "correlation_id": correlation_id,
                "verification": verification,
                "candidate_ranking": candidate_ranking.get("summary") or {},
                "post_send_evaluation": post_send_evaluation,
            },
            correlation_id=correlation_id,
        )
        emit_domain_event(
            conn,
            event_name="reply_generated",
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            conversation_id=conversation["id"],
            message_id=response_message.get("id"),
            correlation_id=correlation_id,
            payload={
                "source": (generated or {}).get("source"),
                "action": action,
                "verification_status": verification.get("status"),
            },
        )
        execute(
            conn,
            "UPDATE conversations SET status = 'ai_active', last_ai_at = ?, updated_at = ? WHERE id = ?",
            (utcnow_iso(), utcnow_iso(), conversation["id"]),
        )
    elif action == "trigger_playbook":
        playbook_result = maybe_trigger_self_state_playbook(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            contact_id=contact["id"],
            conversation_id=conversation["id"],
            decision=decision,
        )
        generator_output = {"playbook_result": playbook_result, "self_state": self_state}
        response_message = create_message(
            conn,
            organization_id=conversation["organization_id"],
            conversation_id=conversation["id"],
            contact_id=contact["id"],
            bot_id=bot["id"],
            direction="outbound",
            kind="text",
            source="ai",
            body="Estoy activando el siguiente mejor playbook para dar continuidad sin perder contexto.",
            status="simulated",
            metadata={
                "provider": "simulated",
                "trace_id": run["trace_id"],
                "execution_id": run["execution_id"],
                "correlation_id": correlation_id,
                "playbook_result": playbook_result,
                "self_state": self_state,
            },
            correlation_id=correlation_id,
        )
    elif action == "wait":
        generator_output = {"self_state": self_state}
        response_message = create_message(
            conn,
            organization_id=conversation["organization_id"],
            conversation_id=conversation["id"],
            contact_id=contact["id"],
            bot_id=bot["id"],
            direction="outbound",
            kind="text",
            source="system",
            body="La conversación quedó en espera por estado operacional.",
            status="internal",
            metadata={
                "trace_id": run["trace_id"],
                "execution_id": run["execution_id"],
                "correlation_id": correlation_id,
                "self_state": self_state,
            },
            correlation_id=correlation_id,
        )

    updated_memory = update_memory(
        conn,
        organization_id=conversation["organization_id"],
        contact_id=contact["id"],
        bot_id=bot["id"],
        incoming_text=incoming_message["body"],
        classification=classification,
        contact=contact,
        recent_messages=recent_messages,
        conversation_id=conversation["id"],
        source_message_id=incoming_message["id"],
    )
    maybe_create_conversation_checkpoint(
        conn,
        organization_id=conversation["organization_id"],
        conversation_id=conversation["id"],
        bot_id=bot["id"],
        recent_messages=recent_messages + [{"direction": incoming_message.get("direction"), "body": incoming_message.get("body")}],
        classification=classification,
        memory=updated_memory or memory,
    )
    candidate_confirmation = maybe_register_candidate_confirmation(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        contact_id=contact["id"],
        classification=classification,
        memory=updated_memory or memory,
        bot_config=bot_config,
    )
    jobs = maybe_schedule_followups(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        contact_id=contact["id"],
        classification=classification,
        decision=decision,
        bot_config=bot_config,
    )
    for job in jobs:
        emit_domain_event(
            conn,
            event_name="followup_scheduled",
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            conversation_id=conversation["id"],
            message_id=incoming_message["id"],
            correlation_id=correlation_id,
            payload={"job_id": job.get("id"), "job_type": job.get("job_type")},
        )
    if candidate_confirmation:
        emit_domain_event(
            conn,
            event_name="talent_candidate_confirmed",
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            conversation_id=conversation["id"],
            message_id=incoming_message["id"],
            correlation_id=correlation_id,
            payload={"candidate_id": candidate_confirmation.get("id"), "vacancy_id": candidate_confirmation.get("vacancy_id")},
        )
    if action == "handoff":
        emit_domain_event(
            conn,
            event_name="handoff_triggered",
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            conversation_id=conversation["id"],
            message_id=incoming_message["id"],
            correlation_id=correlation_id,
            payload={"reason": decision.get("reason"), "policy": decision.get("policy")},
        )
    return {
        "generator_output": generator_output,
        "response_message": response_message,
        "updated_memory": updated_memory,
        "jobs": jobs,
    }


def persist_specialist_route_artifacts(
    conn,
    *,
    conversation: dict[str, Any],
    bot: dict[str, Any],
    contact: dict[str, Any],
    incoming_message: dict[str, Any],
    run: dict[str, Any],
    classification: dict[str, Any],
    specialist_route: dict[str, Any],
    shared_memory: dict[str, Any],
    execution_plan: dict[str, Any],
    supervisor: dict[str, Any],
    status: str,
    decision: dict[str, Any],
    candidate_ranking: dict[str, Any] | None,
    response_message: dict[str, Any] | None,
) -> None:
    from ..multi_agent_runtime import persist_agent_route_run, record_specialist_exposure

    candidate_ranking = candidate_ranking or {}
    specialist_route_row = persist_agent_route_run(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        contact_id=contact["id"],
        message_id=incoming_message["id"],
        text=incoming_message["body"],
        classification=classification,
        route=specialist_route,
        shared_memory=shared_memory,
        execution_plan=execution_plan,
        supervisor=supervisor,
        status=status,
    )
    if status == "completed" and decision.get("action") in {"respond", "respond_and_schedule_followup", "handoff"}:
        record_specialist_exposure(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=bot["id"],
            conversation_id=conversation["id"],
            contact_id=contact["id"],
            message_id=(response_message or {}).get("id") if response_message else incoming_message.get("id"),
            route=specialist_route,
            flow_id=specialist_route.get("specialist_agent_key"),
            prompt_run_id=run["id"],
            metadata={
                "agent_routing_run_id": (specialist_route_row or {}).get("id"),
                "decision_action": decision.get("action"),
                "supervisor_needs_review": bool(supervisor.get("needs_review")),
                "assigned_variant": candidate_ranking.get("selected_variant"),
                "candidate_count": int(candidate_ranking.get("candidate_count") or 0),
                "ranking_version": candidate_ranking.get("ranker_version"),
            },
        )


def persist_pipeline_artifacts(
    conn,
    *,
    ai_run_id: str,
    incoming_message: dict[str, Any],
    conversation: dict[str, Any],
    bot: dict[str, Any],
    classification_input: dict[str, Any],
    classification: dict[str, Any],
    decision_input: dict[str, Any],
    decision: dict[str, Any],
    generator_input: dict[str, Any],
    generator_output: dict[str, Any] | None,
    error: str | None,
    effective_correlation_id: str | None,
    candidate_ranking: dict[str, Any] | None,
    verification: dict[str, Any] | None,
    grounded_context: dict[str, Any],
    execution_plan: dict[str, Any],
    post_send_evaluation: dict[str, Any],
    memory_curation: dict[str, Any],
    self_state: dict[str, Any],
) -> None:
    candidate_ranking = candidate_ranking or {}
    verification = verification or {}
    create_message_ai_run(
        conn,
        ai_run_id=ai_run_id,
        organization_id=conversation['organization_id'],
        message_id=incoming_message['id'],
        conversation_id=conversation['id'],
        bot_id=bot['id'],
        classifier_input=classification_input,
        classifier_output=classification,
        decision_input=decision_input,
        decision_output=decision,
        generator_input=generator_input,
        generator_output=generator_output or {},
        action_taken=decision.get('action'),
        error=error,
        correlation_id=effective_correlation_id,
        classifier_source=classification.get('_classifier_source'),
        decision_policy=decision.get('policy') or 'heuristic',
        generator_source=classification.get('_generator_source'),
        fallback_chain=classification.get('_fallback_chain') or [],
        selected_variant=candidate_ranking.get('selected_variant'),
        candidate_count=int(candidate_ranking.get('candidate_count') or 0),
        ranking_version=candidate_ranking.get('ranker_version'),
        ranking_summary=candidate_ranking.get('summary') or {},
        include_extended_fields=has_column(conn, 'message_ai_runs', 'correlation_id'),
    )
    if table_exists(conn, 'response_candidate_rankings') and decision.get('action') in {'respond', 'respond_and_schedule_followup'}:
        for item in candidate_ranking.get('candidates') or []:
            create_response_candidate_ranking(
                conn,
                organization_id=conversation['organization_id'],
                ai_run_id=ai_run_id,
                message_id=incoming_message['id'],
                conversation_id=conversation['id'],
                bot_id=bot['id'],
                item=item,
            )
    if table_exists(conn, 'message_operational_reasoning'):
        create_message_operational_reasoning(
            conn,
            organization_id=conversation['organization_id'],
            message_id=incoming_message['id'],
            conversation_id=conversation['id'],
            bot_id=bot['id'],
            classification=classification,
            decision=decision,
            execution_plan=execution_plan,
            grounded_context=grounded_context,
            verification=verification,
            candidate_ranking=candidate_ranking,
            post_send_evaluation=post_send_evaluation,
            memory_curation=memory_curation,
            self_state=self_state,
        )



def finalize_pipeline_run(
    conn,
    *,
    run: dict[str, Any],
    conversation: dict[str, Any],
    bot: dict[str, Any],
    effective_correlation_id: str | None,
    total_duration_ms: int,
    status: str,
    error: str | None,
    decision: dict[str, Any],
    classification: dict[str, Any],
    execution_plan: dict[str, Any],
    grounded_context: dict[str, Any],
    verification: dict[str, Any] | None,
    candidate_ranking: dict[str, Any] | None,
    post_send_evaluation: dict[str, Any],
    self_state: dict[str, Any],
    response_message: dict[str, Any] | None,
    jobs: list[dict[str, Any]],
    incoming_message: dict[str, Any],
) -> dict[str, Any]:
    verification = verification or {}
    candidate_ranking = candidate_ranking or {}
    finished_run = finish_execution_run(
        conn,
        run_id=run['id'],
        status=status,
        output_payload={
            'classification': classification,
            'decision': decision,
            'plan': execution_plan,
            'grounded_context': {'source_count': grounded_context.get('source_count'), 'coverage': grounded_context.get('coverage')},
            'verification': verification,
            'candidate_ranking': candidate_ranking,
            'post_send_evaluation': post_send_evaluation,
            'self_state': self_state,
            'response_message_id': response_message.get('id') if response_message else None,
            'jobs': [job.get('id') for job in jobs],
        },
        error_payload={'error': error} if error else {},
    )
    record_stage_metric(
        conn,
        organization_id=conversation['organization_id'],
        bot_id=bot['id'],
        conversation_id=conversation['id'],
        trace_id=run['trace_id'],
        correlation_id=effective_correlation_id,
        vertical=bot.get('vertical'),
        source_type='inbound_message',
        stage_name='pipeline.total',
        duration_ms=total_duration_ms,
        status='ok' if status == 'completed' else 'error',
        metrics={'action': decision.get('action'), 'verification_status': verification.get('status')},
    )
    create_audit_log(
        conn,
        organization_id=conversation['organization_id'],
        actor_user_id=None,
        actor_type='system',
        entity_type='message',
        entity_id=incoming_message['id'],
        action='ai.pipeline_executed',
        metadata={
            'action': decision.get('action'),
            'error': error,
            'execution_run_id': run['id'],
            'verification_status': verification.get('status'),
            'quality_score': post_send_evaluation.get('quality_score'),
        },
    )
    return finished_run
