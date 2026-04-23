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
from ...utils import from_json, hash_value, new_id, to_json, utcnow_iso
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
    preview = adapter.preview(uow.conn, action=payload.action, normalized_payload=normalized, context=context)
    run_id = new_id("toolrun")
    now = utcnow_iso()
    confirmation_token = service._build_confirmation_token(run_id=run_id, normalized_payload=normalized)
    blocked = bool(policy_evaluation and (policy_evaluation.get("decision") or {}).get("enforcement") == "block")
    status = "preview_blocked" if blocked else "preview_ready"
    confirmation_hash = service._hash_confirmation_token(confirmation_token) if policy.requires_confirmation and not blocked else None
    policy_row = None
    service._insert_run(
        uow.conn,
        run_id=run_id,
        organization_id=payload.organization_id,
        bot_id=(bot or {}).get("id") or payload.bot_id,
        action=payload.action,
        adapter_key=adapter.key,
        provider=adapter.provider,
        execution_mode="preview",
        status=status,
        permission_required=policy.permission,
        requires_confirmation=policy.requires_confirmation,
        confirmation_token_hash=confirmation_hash,
        request=payload.model_dump(),
        normalized_payload=normalized,
        validation={
            "requires_confirmation": policy.requires_confirmation,
            "high_impact": policy.high_impact,
            "policy_enforcement": (policy_evaluation or {}).get("decision", {}).get("enforcement"),
        },
        target_ref=preview.get("target_ref") or {},
        result={"preview": preview, "policy": policy_evaluation},
        error={},
        metadata=payload.metadata,
        user_id=user["id"],
        started_at=now,
        completed_at=now,
        specialist_agent_key=(route_context or {}).get("specialist_agent_key"),
        agent_routing_run_id=(route_context or {}).get("agent_routing_run_id"),
        policy_profile_key=(policy_evaluation or {}).get("policy_profile_key"),
        policy_profile_version=(policy_evaluation or {}).get("policy_profile_version"),
        policy_evaluation_id=None,
        policy_payload=policy_evaluation,
    )
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
    service._insert_step(uow.conn, execution_run_id=run_id, organization_id=payload.organization_id, action=payload.action, step_name="preview.validated", status="blocked" if blocked else "ok", adapter_key=adapter.key, provider=adapter.provider, payload={"summary": preview.get("summary")})
    if policy_evaluation:
        service._insert_step(uow.conn, execution_run_id=run_id, organization_id=payload.organization_id, action=payload.action, step_name="policy.evaluated", status="blocked" if blocked else ((policy_evaluation.get("decision") or {}).get("enforcement") or "ok"), adapter_key=adapter.key, provider=adapter.provider, payload=policy_evaluation)
    create_audit_log(
        uow.conn,
        organization_id=payload.organization_id,
        actor_user_id=user["id"],
        actor_type="user",
        entity_type="tool_execution_run",
        entity_id=run_id,
        action="tool_execution.preview_created",
        metadata={"action": payload.action, "adapter_key": adapter.key, "provider": adapter.provider, "policy_profile_key": (policy_evaluation or {}).get("policy_profile_key"), "policy_enforcement": (policy_evaluation or {}).get("decision", {}).get("enforcement")},
    )
    uow.commit()
    row = fetch_one(uow.conn, "SELECT * FROM tool_execution_runs WHERE id = ?", (run_id,))
    return ok({
        "execution": service._serialize_run(uow.conn, row),
        "preview": preview,
        "policy": service._serialize_policy(policy_row) if policy_row else policy_evaluation,
        "confirmation_token": confirmation_token if policy.requires_confirmation and not blocked else None,
    })
