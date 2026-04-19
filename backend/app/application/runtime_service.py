from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from ..contracts import dead_letter_row, ok
from ..db import execute, fetch_all, fetch_one
from ..observability import capture_message
from ..platform import compute_observability_overview, list_runtime_callbacks, queue_overview, scheduler_overview
from ..repositories import create_audit_log, get_bot, get_contact, get_contact_memory, get_conversation
from ..security import ensure_bot_access, ensure_org_access
from ..services import bot_health_summary, integration_health_summary, runtime_overview
from ..world_class import cache_efficiency_overview, circuit_breaker_summary, memory_runtime_overview, revenue_overview, search_technical_logs, summarize_ai_usage, trace_timeline
from ..world_class_ext import create_shadow_run, flush_otel_exports, issue_public_api_credential, otel_export_overview, prompt_analytics_overview, shadow_overview, upsert_prompt_artifact
from ..telemetry_runtime import ai_cost_dashboard
from ..apm import apm_overview
from ..world_class_plus import assign_prompt_experiment_variant, chaos_overview, compliance_overview, create_deletion_workflow, create_prompt_experiment, list_prompt_experiments, load_test_overview, module_health_checks, register_chaos_test_run, register_load_test_run, revenue_optimization_world_class, runtime_autoscaling_plan, unified_inbox_overview
from ..utils import from_json, utcnow_iso
from ..defaults import default_bot_config
from ..runtime_settings import ai_optimization_settings, memory_runtime_settings, read_global_settings
from .support import require_permission
from .uow import UnitOfWork


def _sse(event: str, data: dict[str, Any]) -> bytes:
    import json

    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode('utf-8')


class RuntimeService:
    def runtime_overview(self, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        return runtime_overview(uow.conn, organization_id=organization_id, bot_id=bot_id)

    def bot_health(self, uow: UnitOfWork, *, bot_id: str, organization_id: str, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        bot = get_bot(uow.conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if bot["organization_id"] != organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)
        return ok(bot_health_summary(uow.conn, organization_id=organization_id, bot_id=bot_id))

    def integrations_health(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        return ok(integration_health_summary(uow.conn, organization_id=organization_id, bot_id=bot_id))

    def observability_overview(self, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        if bot_id:
            bot = get_bot(uow.conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            if organization_id and bot["organization_id"] != organization_id:
                raise HTTPException(status_code=403, detail="Bot does not belong to organization")
            ensure_bot_access(user, bot)
        return compute_observability_overview(uow.conn, organization_id=organization_id, bot_id=bot_id)

    def frontend_errors(self, *, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        message = str(payload.get("message") or "frontend error")
        capture_message(
            message,
            level="error",
            source=str(payload.get("source") or "frontend"),
            request_id=getattr(request.state, "request_id", None),
            organization_id=payload.get("organization_id") or getattr(request.state, "organization_id", None),
            bot_id=payload.get("bot_id") or getattr(request.state, "bot_id", None),
            user_id=payload.get("user_id") or getattr(request.state, "user_id", None),
            path=payload.get("path"),
            digest=payload.get("digest"),
        )
        return {"ok": True, "request_id": getattr(request.state, "request_id", None)}

    def runtime_queue(self, uow: UnitOfWork, *, organization_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "scheduler.read")
        return queue_overview(uow.conn, organization_id)

    def runtime_scheduler(self, uow: UnitOfWork, *, organization_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "runs.read")
        return scheduler_overview(uow.conn, organization_id=organization_id)

    def runtime_callbacks(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> list[dict[str, Any]]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "runs.read")
        if bot_id:
            bot = get_bot(uow.conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            if bot["organization_id"] != organization_id:
                raise HTTPException(status_code=403, detail="Bot does not belong to organization")
            ensure_bot_access(user, bot)
        return list_runtime_callbacks(uow.conn, organization_id=organization_id, bot_id=bot_id)

    def list_dead_letters(self, uow: UnitOfWork, *, organization_id: str, kind: str | None, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        jobs: list[dict[str, Any]] = []
        outbox: list[dict[str, Any]] = []
        registry = fetch_all(uow.conn, "SELECT * FROM dead_letter_events WHERE organization_id = ? ORDER BY updated_at DESC LIMIT 200", (organization_id,))
        registry_by_source = {(row.get('source_table'), row.get('source_id')): row for row in registry}
        if kind in (None, "jobs"):
            jobs = fetch_all(uow.conn, "SELECT * FROM automation_jobs WHERE organization_id = ? AND status = 'dead_letter' ORDER BY created_at DESC LIMIT 100", (organization_id,))
        if kind in (None, "outbox"):
            outbox = fetch_all(uow.conn, "SELECT * FROM outbox_messages WHERE organization_id = ? AND status = 'dead_letter' ORDER BY created_at DESC LIMIT 100", (organization_id,))
        def _merge(rows, table_name, channel_name):
            merged = []
            for row in rows:
                registry_row = registry_by_source.get((table_name, row.get('id'))) or {}
                merged.append({**dead_letter_row(row, channel=channel_name), 'dead_letter_event': {**registry_row, 'payload_snapshot': from_json(registry_row.get('payload_snapshot_json'), {}), 'error': from_json(registry_row.get('error_json'), {})} if registry_row else None})
            return merged
        return {
            "jobs": _merge(jobs, 'automation_jobs', 'job'),
            "outbox": _merge(outbox, 'outbox_messages', 'outbox'),
        }

    def requeue_dead_letter(self, uow: UnitOfWork, *, kind: str, item_id: str, payload, user: dict) -> dict[str, Any]:
        if kind not in {"jobs", "outbox"}:
            raise HTTPException(status_code=400, detail="Unsupported dead letter kind")
        table = "automation_jobs" if kind == "jobs" else "outbox_messages"
        row = fetch_one(uow.conn, f"SELECT * FROM {table} WHERE id = ?", (item_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Dead letter item not found")
        ensure_org_access(user, row["organization_id"])
        require_permission(user, row["organization_id"], "operations.requeue")
        scheduled_for = payload.scheduled_for or utcnow_iso()
        execute(uow.conn, f"UPDATE {table} SET status = 'retry', scheduled_for = ?, last_error = NULL WHERE id = ?", (scheduled_for, item_id))
        execute(uow.conn, "DELETE FROM dead_letter_events WHERE source_table = ? AND source_id = ?", (table, item_id))
        create_audit_log(
            uow.conn,
            organization_id=row["organization_id"],
            actor_user_id=user["id"],
            actor_type="user",
            entity_type=table,
            entity_id=item_id,
            action="dead_letter.requeued",
            metadata={"kind": kind, "scheduled_for": scheduled_for},
        )
        uow.commit()
        return fetch_one(uow.conn, f"SELECT * FROM {table} WHERE id = ?", (item_id,))

    def ai_dashboard(self, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        settings_payload = read_global_settings()
        return {
            "usage": summarize_ai_usage(uow.conn, organization_id=organization_id, bot_id=bot_id, limit=500),
            "costs_by_conversation": ai_cost_dashboard(uow.conn, organization_id=organization_id, bot_id=bot_id, limit=100),
            "circuits": circuit_breaker_summary(uow.conn),
            "cache": cache_efficiency_overview(uow.conn, organization_id=organization_id, bot_id=bot_id),
            "memory_runtime": memory_runtime_overview(uow.conn, organization_id=organization_id, bot_id=bot_id),
            "optimization_profile": settings_payload.get("ai_optimization") or ai_optimization_settings(),
            "memory_profile": settings_payload.get("memory_runtime") or memory_runtime_settings(),
            "revenue": revenue_overview(uow.conn, organization_id=organization_id or '', bot_id=bot_id) if organization_id else {"totals": {"events": 0, "expected_value": 0.0}, "recent": []},
            "apm": apm_overview(),
        }

    def ai_stream_preview(self, uow: UnitOfWork, *, conversation_id: str, message: str, user: dict):
        conversation = get_conversation(uow.conn, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        ensure_org_access(user, conversation["organization_id"])
        require_permission(user, conversation["organization_id"], "operations.read")
        bot = get_bot(uow.conn, conversation["bot_id"])
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        bot_config = from_json(bot.get("config_draft_json"), default_bot_config(business_name=bot.get("business_name") or bot.get("name") or "Business", vertical=bot.get("vertical") or "general", bot_name=bot.get("name") or "Bot", primary_objective="Responder y convertir", tone="cercano", language=bot.get("language") or "es", timezone=bot.get("timezone")))
        contact = get_contact(uow.conn, conversation["contact_id"]) or {}
        memory = get_contact_memory(uow.conn, conversation["contact_id"], conversation["bot_id"]) or {}
        recent_messages = fetch_all(uow.conn, "SELECT direction, body, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
        from ..ai import classify_message, generate_response, stream_generated_text_chunks

        classification = classify_message(
            message,
            memory,
            bot_config,
            conn=uow.conn,
            organization_id=conversation["organization_id"],
            bot_id=conversation["bot_id"],
            conversation_id=conversation_id,
        )
        response_text, payload = generate_response(
            message,
            classification,
            bot_config,
            memory,
            recent_messages,
            conn=uow.conn,
            organization_id=conversation["organization_id"],
            bot_id=conversation["bot_id"],
            contact_id=contact.get("id"),
            conversation_id=conversation_id,
        )

        def event_stream():
            yield _sse("meta", {"conversation_id": conversation_id, "intent": classification.get("intent"), "source": payload.get("generator_source")})
            for chunk in stream_generated_text_chunks(response_text, chunk_size=36):
                yield _sse("chunk", {"delta": chunk})
            yield _sse("done", {"text": response_text, "source": payload.get("generator_source")})

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    def searchable_logs(self, uow: UnitOfWork, *, organization_id: str | None, query: str, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        return ok(search_technical_logs(uow.conn, organization_id=organization_id, query=query, limit=100))

    def trace_explorer(self, uow: UnitOfWork, *, organization_id: str | None, trace_id: str, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        return ok(trace_timeline(uow.conn, trace_id=trace_id))

    def observability_otel(self, uow: UnitOfWork, *, organization_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        return ok(otel_export_overview(uow.conn))

    def observability_otel_flush(self, uow: UnitOfWork, *, organization_id: str | None, dry_run: bool, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        data = flush_otel_exports(uow.conn, dry_run=dry_run)
        uow.commit()
        return ok(data)

    def shadow_run_create(self, uow: UnitOfWork, *, payload: dict[str, Any], user: dict) -> dict[str, Any]:
        organization_id = str(payload.get("organization_id") or "")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "quality.review")
        row = create_shadow_run(
            uow.conn,
            organization_id=organization_id,
            bot_id=payload.get("bot_id"),
            conversation_id=payload.get("conversation_id"),
            experiment_key=str(payload.get("experiment_key") or "default"),
            production_output=payload.get("production_output") or {},
            candidate_output=payload.get("candidate_output") or {},
            verdict=payload.get("verdict"),
        )
        if getattr(uow, "mode", "write") != "read":
            uow.commit()
        return ok(row)

    def shadow_run_overview(self, uow: UnitOfWork, *, organization_id: str, experiment_key: str | None, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "quality.review")
        return ok(shadow_overview(uow.conn, organization_id=organization_id, experiment_key=experiment_key))

    def prompt_artifact_upsert(self, uow: UnitOfWork, *, payload: dict[str, Any], user: dict) -> dict[str, Any]:
        organization_id = str(payload.get("organization_id") or "")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "quality.review")
        row = upsert_prompt_artifact(
            uow.conn,
            organization_id=organization_id,
            bot_id=payload.get("bot_id"),
            artifact_type=str(payload.get("artifact_type") or "version"),
            artifact_key=str(payload.get("artifact_key") or payload.get("name") or "default"),
            title=payload.get("title"),
            body=str(payload.get("body") or payload.get("prompt") or ""),
            metadata=payload.get("metadata") or {},
            status=str(payload.get("status") or "active"),
        )
        uow.commit()
        return ok(row)

    def prompt_analytics(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "quality.review")
        return ok(prompt_analytics_overview(uow.conn, organization_id=organization_id, bot_id=bot_id))

    def public_api_credential_issue(self, uow: UnitOfWork, *, payload: dict[str, Any], user: dict) -> dict[str, Any]:
        organization_id = str(payload.get("organization_id") or "")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "integration.manage")
        row = issue_public_api_credential(
            uow.conn,
            organization_id=organization_id,
            name=str(payload.get("name") or "Public API key"),
            scopes=list(payload.get("scopes") or ["channels.write", "channels.read"]),
        )
        uow.commit()
        return ok(row)

    def runtime_autoscaling(self, uow: UnitOfWork, *, organization_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        return ok(runtime_autoscaling_plan(uow.conn, organization_id=organization_id))

    def runtime_module_health(self, uow: UnitOfWork, *, organization_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        return ok(module_health_checks(uow.conn, organization_id=organization_id))

    def unified_inbox(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        return ok(unified_inbox_overview(uow.conn, organization_id=organization_id, bot_id=bot_id))

    def revenue_optimization(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        data = revenue_optimization_world_class(uow.conn, organization_id=organization_id, bot_id=bot_id)
        if getattr(uow, "mode", "write") != "read":
            uow.commit()
        return ok(data)

    def compliance_world_class(self, uow: UnitOfWork, *, organization_id: str, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "security.manage")
        return ok(compliance_overview(uow.conn, organization_id=organization_id))

    def deletion_workflow_create(self, uow: UnitOfWork, *, payload: dict[str, Any], user: dict) -> dict[str, Any]:
        organization_id = str(payload.get("organization_id") or "")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "security.manage")
        row = create_deletion_workflow(
            uow.conn,
            organization_id=organization_id,
            subject_type=str(payload.get("subject_type") or payload.get("entity_type") or "contact"),
            subject_id=str(payload.get("subject_id") or payload.get("entity_id") or ""),
            requested_by=user.get("id"),
            reason=payload.get("reason"),
            target_stores=list(payload.get("target_stores") or []),
        )
        if not row.get("id"):
            raise HTTPException(status_code=400, detail="subject_id is required")
        uow.commit()
        return ok(row)

    def chaos_run_create(self, uow: UnitOfWork, *, payload: dict[str, Any], user: dict) -> dict[str, Any]:
        organization_id = str(payload.get("organization_id") or "")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "quality.review")
        row = register_chaos_test_run(
            uow.conn,
            organization_id=organization_id,
            scenario_key=str(payload.get("scenario_key") or "provider-failure"),
            target=str(payload.get("target") or "runtime"),
            blast_radius=str(payload.get("blast_radius") or "low"),
            status=str(payload.get("status") or "passed"),
            findings=dict(payload.get("findings") or {}),
        )
        uow.commit()
        return ok(row)

    def chaos_runs_overview(self, uow: UnitOfWork, *, organization_id: str, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "quality.review")
        return ok(chaos_overview(uow.conn, organization_id=organization_id))

    def load_test_create(self, uow: UnitOfWork, *, payload: dict[str, Any], user: dict) -> dict[str, Any]:
        organization_id = str(payload.get("organization_id") or "")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "quality.review")
        row = register_load_test_run(
            uow.conn,
            organization_id=organization_id,
            scenario_key=str(payload.get("scenario_key") or "runtime-sustained"),
            target_rps=int(payload.get("target_rps") or 0),
            peak_rps=int(payload.get("peak_rps") or payload.get("target_rps") or 0),
            p95_ms=int(payload.get("p95_ms") or 0),
            error_rate=float(payload.get("error_rate") or 0),
            queue_depth=int(payload.get("queue_depth") or 0),
            status=str(payload.get("status") or "passed"),
            findings=dict(payload.get("findings") or {}),
        )
        uow.commit()
        return ok(row)

    def load_tests_overview(self, uow: UnitOfWork, *, organization_id: str, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "quality.review")
        return ok(load_test_overview(uow.conn, organization_id=organization_id))

    def prompt_experiment_create(self, uow: UnitOfWork, *, payload: dict[str, Any], user: dict) -> dict[str, Any]:
        organization_id = str(payload.get("organization_id") or "")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "quality.review")
        row = create_prompt_experiment(
            uow.conn,
            organization_id=organization_id,
            bot_id=payload.get("bot_id"),
            experiment_key=str(payload.get("experiment_key") or "default"),
            artifact_a_key=str(payload.get("artifact_a_key") or "control"),
            artifact_b_key=str(payload.get("artifact_b_key") or "candidate"),
            rollout_percentage=int(payload.get("rollout_percentage") or 50),
            status=str(payload.get("status") or "active"),
        )
        uow.commit()
        return ok(row)

    def prompt_experiments(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "quality.review")
        return ok(list_prompt_experiments(uow.conn, organization_id=organization_id, bot_id=bot_id))

    def prompt_experiment_assignment(self, uow: UnitOfWork, *, organization_id: str, experiment_key: str, conversation_id: str | None, contact_id: str | None, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "quality.review")
        row = assign_prompt_experiment_variant(uow.conn, organization_id=organization_id, experiment_key=experiment_key, conversation_id=conversation_id, contact_id=contact_id)
        if not row:
            raise HTTPException(status_code=404, detail="Prompt experiment not found")
        if getattr(uow, "mode", "write") != "read":
            uow.commit()
        return ok(row)


runtime_service = RuntimeService()
