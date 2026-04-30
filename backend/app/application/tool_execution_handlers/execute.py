from __future__ import annotations

import hashlib
from typing import Any

from fastapi import HTTPException

from ...agent_policy_runtime import evaluate_specialist_policy, get_policy_profile_for_specialist, persist_agent_policy_evaluation
from ...contracts import ok
from ...db import execute, fetch_all, fetch_one
from ...job_idempotency import begin_job_execution, get_job_execution, mark_job_completed, mark_job_failed
from ...multi_agent_runtime import build_shared_memory_context
from ...repositories import create_audit_log, get_bot
from ...security import ensure_bot_access, ensure_org_access
from ...utils import canonical_hash, from_json, new_id, to_json, utcnow_iso
from ...operational_events import record_operational_event
from ..support import require_permission
from ..uow import UnitOfWork


from ..tool_execution_adapters import (
    ActionPolicy,
    BaseAdapter,
    GoogleCalendarAdapter,
    StripePaymentsAdapter,
    WaosCalendarAdapter,
    WaosCrmAdapter,
)
from ..tool_execution_policy import resolve_action_policy
from ..tool_execution_presenters import serialize_tool_execution_run



def handle(service, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
    ensure_org_access(user, payload.organization_id)
    normalized = service._normalize_payload(uow.conn, payload=payload)
    policy = service._policy(payload.action)
    require_permission(user, payload.organization_id, policy.permission)
    bot = service._validate_bot_access(uow.conn, organization_id=payload.organization_id, bot_id=normalized.get("bot_id") or payload.bot_id, user=user)
    adapter, context = service._resolve_adapter(uow.conn, action=payload.action, organization_id=payload.organization_id, bot_id=(bot or {}).get("id") or payload.bot_id)
    route_context, policy_evaluation = service._resolve_specialist_policy_context(
        uow.conn,
        organization_id=payload.organization_id,
        bot_id=(bot or {}).get("id") or payload.bot_id,
        normalized_payload=normalized,
        metadata=payload.metadata,
        requested_action=payload.action,
    )
    service._enforce_policy_or_raise(policy_evaluation)
    preview_run = service._resolve_preview_run(uow.conn, payload=payload, user=user, normalized=normalized, policy=policy)
    idempotency_key, idempotency_target_id, client_request_id = service._resolve_idempotency_key(payload.action, payload.organization_id, normalized, payload)
    service._ensure_preview_idempotency_scope(uow.conn, preview_run_id=(preview_run or {}).get("id"), idempotency_key=idempotency_key)
    execution_metadata = {
        **payload.metadata,
        "idempotency_key": idempotency_key,
        "idempotency_target_id": idempotency_target_id,
        "client_request_id": client_request_id,
        "preview_execution_id": (preview_run or {}).get("id"),
        "confirmation_token_hash": service._hash_confirmation_token(payload.confirmation_token) if payload.confirmation_token else None,
        "correlation_id": (payload.metadata or {}).get("correlation_id") or client_request_id or idempotency_key,
    }
    job_payload = {
        "organization_id": payload.organization_id,
        "action_type": payload.action,
        "target_id": idempotency_target_id,
        "client_request_id": client_request_id,
        "payload": normalized,
    }
    expected_payload_hash = canonical_hash(job_payload)
    existing_job = get_job_execution(uow.conn, dedupe_key=idempotency_key)
    if existing_job and existing_job.get("payload_hash") and existing_job.get("payload_hash") != expected_payload_hash:
        raise HTTPException(status_code=409, detail="idempotency_key_payload_mismatch")
    if existing_job and existing_job.get("status") == "completed":
        replay_id = new_id("toolrun")
        original = fetch_one(
            uow.conn,
            "SELECT * FROM tool_execution_runs WHERE organization_id = ? AND idempotency_key = ? AND status = 'completed' ORDER BY created_at DESC LIMIT 1",
            (payload.organization_id, idempotency_key),
        )
        now = utcnow_iso()
        service._insert_run(
            uow.conn,
            run_id=replay_id,
            organization_id=payload.organization_id,
            bot_id=(bot or {}).get("id") or payload.bot_id,
            action=payload.action,
            adapter_key=adapter.key,
            provider=adapter.provider,
            execution_mode="execute",
            status="completed",
            permission_required=policy.permission,
            requires_confirmation=policy.requires_confirmation,
            confirmation_token_hash=None,
            request=payload.model_dump(),
            normalized_payload=normalized,
            validation={"idempotent": True},
            target_ref=from_json((original or {}).get("target_ref_json"), {}),
            result=from_json(existing_job.get("result_json"), {}),
            error={},
            metadata={**execution_metadata, "idempotent": True},
            user_id=user["id"],
            preview_run_id=(preview_run or {}).get("id"),
            idempotency_key=idempotency_key,
            idempotent_replay_of_run_id=(original or {}).get("id"),
            started_at=now,
            completed_at=now,
            specialist_agent_key=(original or {}).get("specialist_agent_key") or (route_context or {}).get("specialist_agent_key"),
            agent_routing_run_id=(original or {}).get("agent_routing_run_id") or (route_context or {}).get("agent_routing_run_id"),
            policy_profile_key=(original or {}).get("policy_profile_key") or (policy_evaluation or {}).get("policy_profile_key"),
            policy_profile_version=(original or {}).get("policy_profile_version") or (policy_evaluation or {}).get("policy_profile_version"),
            policy_evaluation_id=(original or {}).get("policy_evaluation_id"),
            policy_payload=policy_evaluation,
        )
        service._insert_step(uow.conn, execution_run_id=replay_id, organization_id=payload.organization_id, action=payload.action, step_name="idempotency.replayed", status="ok", adapter_key=adapter.key, provider=adapter.provider, payload={"original_run_id": (original or {}).get("id")})
        uow.commit()
        row = fetch_one(uow.conn, "SELECT * FROM tool_execution_runs WHERE id = ?", (replay_id,))
        return ok({"execution": service._serialize_run(uow.conn, row), "idempotent": True, "result": from_json(existing_job.get("result_json"), {})})
    if existing_job and existing_job.get("status") == "running":
        raise HTTPException(status_code=409, detail="tool_execution_already_running")
    if existing_job and existing_job.get("status") == "failed" and not payload.force_retry_failed:
        raise HTTPException(status_code=409, detail="tool_execution_failed_use_new_idempotency_key_or_force_retry_failed")

    claim = begin_job_execution(uow.conn, job_type=f"tool_execution:{payload.action}", dedupe_key=idempotency_key, payload=job_payload)
    if claim.get("_payload_mismatch"):
        raise HTTPException(status_code=409, detail="idempotency_key_payload_mismatch")
    if claim.get("_already_existing") and claim.get("status") == "running":
        raise HTTPException(status_code=409, detail="tool_execution_already_running")
    if claim.get("_already_existing") and claim.get("status") == "failed" and not payload.force_retry_failed:
        raise HTTPException(status_code=409, detail="tool_execution_failed_use_new_idempotency_key_or_force_retry_failed")

    preview_claim_key = f"tool-preview-consume:{preview_run['id']}" if preview_run else None
    if preview_claim_key:
        preview_claim = begin_job_execution(
            uow.conn,
            job_type=f"tool_execution_preview:{payload.action}",
            dedupe_key=preview_claim_key,
            payload={"preview_execution_id": preview_run["id"], "idempotency_key": idempotency_key},
        )
        if preview_claim.get("_payload_mismatch"):
            mark_job_failed(uow.conn, dedupe_key=idempotency_key, error_text="tool_execution_preview_already_consumed")
            raise HTTPException(status_code=409, detail="tool_execution_preview_already_consumed")
        if preview_claim.get("_already_existing") and preview_claim.get("status") == "running":
            mark_job_failed(uow.conn, dedupe_key=idempotency_key, error_text="tool_execution_preview_already_running")
            raise HTTPException(status_code=409, detail="tool_execution_preview_already_running")
        if preview_claim.get("_already_existing") and preview_claim.get("status") == "failed" and not payload.force_retry_failed:
            mark_job_failed(uow.conn, dedupe_key=idempotency_key, error_text="tool_execution_preview_failed")
            raise HTTPException(status_code=409, detail="tool_execution_preview_failed_use_new_preview_or_force_retry_failed")
    run_id = new_id("toolrun")
    now = utcnow_iso()
    service._insert_run(
        uow.conn,
        run_id=run_id,
        organization_id=payload.organization_id,
        bot_id=(bot or {}).get("id") or payload.bot_id,
        action=payload.action,
        adapter_key=adapter.key,
        provider=adapter.provider,
        execution_mode="execute",
        status="running",
        permission_required=policy.permission,
        requires_confirmation=policy.requires_confirmation,
        confirmation_token_hash=None,
        request=payload.model_dump(),
        normalized_payload=normalized,
        validation={"high_impact": policy.high_impact},
        target_ref=adapter.target_ref(uow.conn, action=payload.action, normalized_payload=normalized, context=context),
        result={},
        error={},
        metadata=execution_metadata,
        user_id=user["id"],
        preview_run_id=(preview_run or {}).get("id"),
        idempotency_key=idempotency_key,
        started_at=now,
        completed_at=None,
        specialist_agent_key=(route_context or {}).get("specialist_agent_key"),
        agent_routing_run_id=(route_context or {}).get("agent_routing_run_id"),
        policy_profile_key=(policy_evaluation or {}).get("policy_profile_key"),
        policy_profile_version=(policy_evaluation or {}).get("policy_profile_version"),
        policy_evaluation_id=None,
        policy_payload=policy_evaluation,
    )
    policy_row = None
    if payload.action in {"create_payment_link", "send_receipt"}:
        record_operational_event(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=(bot or {}).get("id") or payload.bot_id,
            conversation_id=normalized.get("conversation_id"),
            correlation_id=execution_metadata.get("correlation_id"),
            tool_execution_id=run_id,
            provider=adapter.provider,
            provider_request_id=idempotency_key,
            state="provider_pending",
            event_type=f"tool_execution.{payload.action}.provider_pending",
            source="tool_execution.execute",
            request={"action": payload.action, "target_id": idempotency_target_id},
        )
        execute(uow.conn, "UPDATE tool_execution_runs SET operational_status = 'provider_pending', correlation_id = ?, provider_request_id = ? WHERE id = ?", (execution_metadata.get("correlation_id"), idempotency_key, run_id))

    if policy_evaluation:
        policy_row = persist_agent_policy_evaluation(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=(bot or {}).get("id") or payload.bot_id,
            conversation_id=normalized.get("conversation_id"),
            contact_id=normalized.get("contact_id"),
            specialist_agent_key=(route_context or {}).get("specialist_agent_key"),
            policy_evaluation=policy_evaluation,
            requested_action=payload.action,
            agent_routing_run_id=(route_context or {}).get("agent_routing_run_id"),
            tool_execution_run_id=run_id,
        )
        execute(uow.conn, "UPDATE tool_execution_runs SET policy_evaluation_id = ?, policy_json = ?, updated_at = ? WHERE id = ?", (policy_row.get("id"), to_json(policy_evaluation), now, run_id))
    service._insert_step(uow.conn, execution_run_id=run_id, organization_id=payload.organization_id, action=payload.action, step_name="authorization.checked", status="ok", adapter_key=adapter.key, provider=adapter.provider, payload={"permission": policy.permission, "requires_confirmation": policy.requires_confirmation})
    if policy_evaluation:
        service._insert_step(uow.conn, execution_run_id=run_id, organization_id=payload.organization_id, action=payload.action, step_name="policy.evaluated", status=(policy_evaluation.get("decision") or {}).get("enforcement") or "ok", adapter_key=adapter.key, provider=adapter.provider, payload=policy_evaluation)
    try:
        execute_normalized = {
            **normalized,
            "metadata": {
                **(normalized.get("metadata") or {}),
                "tool_execution_idempotency_key": idempotency_key,
                "client_request_id": client_request_id,
                "idempotency_target_id": idempotency_target_id,
                "preview_execution_id": (preview_run or {}).get("id"),
                "confirmation_token_hash": service._hash_confirmation_token(payload.confirmation_token) if payload.confirmation_token else None,
                "correlation_id": execution_metadata.get("correlation_id"),
            },
        }
        result = adapter.execute(uow.conn, action=payload.action, normalized_payload=execute_normalized, context=context, actor_user=user)
        completed_at = utcnow_iso()
        appointment_id = ((result.get("appointment") or {}).get("id")) or normalized.get("appointment_id")
        payment_id = ((result.get("payment") or {}).get("id")) or normalized.get("payment_id")
        lead_id = ((result.get("lead") or {}).get("id")) or normalized.get("lead_id")
        conversation_id = normalized.get("conversation_id") or ((result.get("payment") or {}).get("conversation_id")) or ((result.get("appointment") or {}).get("conversation_id"))
        contact_id = normalized.get("contact_id") or ((result.get("payment") or {}).get("contact_id")) or ((result.get("appointment") or {}).get("contact_id"))
        execute(
            uow.conn,
            "UPDATE tool_execution_runs SET status = 'completed', operational_status = CASE WHEN ? IS NOT NULL THEN 'provider_confirmed' ELSE COALESCE(operational_status, 'local_created') END, target_ref_json = ?, result_json = ?, completed_at = ?, updated_at = ?, appointment_id = COALESCE(appointment_id, ?), payment_id = COALESCE(payment_id, ?), lead_id = COALESCE(lead_id, ?), conversation_id = COALESCE(conversation_id, ?), contact_id = COALESCE(contact_id, ?) WHERE id = ?",
            (
                payment_id if payload.action in {"create_payment_link", "send_receipt"} else None,
                to_json(result.get("target_ref") or {}),
                to_json(result),
                completed_at,
                completed_at,
                appointment_id,
                payment_id,
                lead_id,
                conversation_id,
                contact_id,
                run_id,
            ),
        )
        closed_loop = service._record_closed_loop_feedback(
            uow.conn,
            run_id=run_id,
            organization_id=payload.organization_id,
            bot=bot,
            action=payload.action,
            adapter=adapter,
            normalized_payload={**normalized, "appointment_id": appointment_id, "payment_id": payment_id, "lead_id": lead_id, "conversation_id": conversation_id, "contact_id": contact_id},
            result=result,
            metadata={**execution_metadata, "policy_profile_key": (policy_evaluation or {}).get("policy_profile_key")},
            actor_user=user,
            completed_at=completed_at,
        )
        if closed_loop:
            result = {**result, "closed_loop": closed_loop}
            execute(uow.conn, "UPDATE tool_execution_runs SET result_json = ?, updated_at = ? WHERE id = ?", (to_json(result), completed_at, run_id))
        if payload.action in {"create_payment_link", "send_receipt"}:
            record_operational_event(
                uow.conn,
                organization_id=payload.organization_id,
                bot_id=(bot or {}).get("id") or payload.bot_id,
                conversation_id=conversation_id,
                correlation_id=execution_metadata.get("correlation_id"),
                tool_execution_id=run_id,
                payment_id=payment_id,
                provider=adapter.provider,
                provider_request_id=idempotency_key,
                provider_message_id=((result.get("payment") or {}).get("external_payment_id")),
                state="provider_confirmed",
                event_type=f"tool_execution.{payload.action}.provider_confirmed",
                source="tool_execution.execute",
                response=result.get("target_ref") or {},
            )
        service._insert_step(uow.conn, execution_run_id=run_id, organization_id=payload.organization_id, action=payload.action, step_name="adapter.executed", status="ok", adapter_key=adapter.key, provider=adapter.provider, payload={"target_ref": result.get("target_ref") or {}, "closed_loop": closed_loop})
        mark_job_completed(uow.conn, dedupe_key=idempotency_key, result=result)
        if preview_claim_key:
            mark_job_completed(uow.conn, dedupe_key=preview_claim_key, result={"idempotency_key": idempotency_key, "run_id": run_id})
        create_audit_log(
            uow.conn,
            organization_id=payload.organization_id,
            actor_user_id=user["id"],
            actor_type="user",
            entity_type="tool_execution_run",
            entity_id=run_id,
            action="tool_execution.executed",
            metadata={"action": payload.action, "adapter_key": adapter.key, "provider": adapter.provider, "idempotency_key": idempotency_key, "idempotency_target_id": idempotency_target_id, "client_request_id": client_request_id, "policy_profile_key": (policy_evaluation or {}).get("policy_profile_key")},
        )
        uow.commit()
        row = fetch_one(uow.conn, "SELECT * FROM tool_execution_runs WHERE id = ?", (run_id,))
        return ok({"execution": service._serialize_run(uow.conn, row), "idempotent": False, "result": result, "policy": service._serialize_policy(policy_row) if policy_row else policy_evaluation})
    except HTTPException as exc:
        service._handle_execution_failure(uow, run_id=run_id, idempotency_key=idempotency_key, organization_id=payload.organization_id, action=payload.action, adapter=adapter, error={"detail": exc.detail, "status_code": exc.status_code}, user=user)
        if payload.action in {"create_payment_link", "send_receipt"}:
            record_operational_event(uow.conn, organization_id=payload.organization_id, bot_id=(bot or {}).get("id") or payload.bot_id, conversation_id=normalized.get("conversation_id"), correlation_id=execution_metadata.get("correlation_id"), tool_execution_id=run_id, provider=adapter.provider, provider_request_id=idempotency_key, state="provider_failed", event_type=f"tool_execution.{payload.action}.provider_failed", source="tool_execution.execute", error={"detail": exc.detail, "status_code": exc.status_code})
        if preview_claim_key:
            mark_job_failed(uow.conn, dedupe_key=preview_claim_key, error_text=str(exc.detail))
        raise
    except Exception as exc:
        service._handle_execution_failure(uow, run_id=run_id, idempotency_key=idempotency_key, organization_id=payload.organization_id, action=payload.action, adapter=adapter, error={"message": str(exc)}, user=user)
        if payload.action in {"create_payment_link", "send_receipt"}:
            record_operational_event(uow.conn, organization_id=payload.organization_id, bot_id=(bot or {}).get("id") or payload.bot_id, conversation_id=normalized.get("conversation_id"), correlation_id=execution_metadata.get("correlation_id"), tool_execution_id=run_id, provider=adapter.provider, provider_request_id=idempotency_key, state="provider_failed", event_type=f"tool_execution.{payload.action}.provider_failed", source="tool_execution.execute", error={"message": str(exc)})
        if preview_claim_key:
            mark_job_failed(uow.conn, dedupe_key=preview_claim_key, error_text=str(exc))
        raise HTTPException(status_code=500, detail=f"tool_execution_failed:{exc}") from exc
