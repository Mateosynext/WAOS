from __future__ import annotations

import hashlib
from typing import Any

from fastapi import HTTPException

from ..agent_policy_runtime import evaluate_specialist_policy, get_policy_profile_for_specialist, persist_agent_policy_evaluation
from ..contracts import ok
from ..db import execute, fetch_all, fetch_one
from ..job_idempotency import begin_job_execution, get_job_execution, mark_job_completed, mark_job_failed
from ..multi_agent_runtime import build_shared_memory_context
from ..repositories import create_audit_log, get_bot
from ..security import ensure_bot_access, ensure_org_access
from ..utils import from_json, hash_value, new_id, to_json, utcnow_iso
from .outcomes_service import outcomes_service
from .support import require_permission
from .uow import UnitOfWork


from .tool_execution_adapters import (
    DEFAULT_ACTION_POLICIES,
    ActionPolicy,
    BaseAdapter,
    GoogleCalendarAdapter,
    StripePaymentsAdapter,
    WaosCalendarAdapter,
    WaosCrmAdapter,
)


class ToolExecutionService:
    def preview(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        normalized = self._normalize_payload(uow.conn, payload=payload)
        policy = self._policy(payload.action)
        require_permission(user, payload.organization_id, policy.permission)
        bot = self._validate_bot_access(uow.conn, organization_id=payload.organization_id, bot_id=normalized.get("bot_id") or payload.bot_id, user=user)
        adapter, context = self._resolve_adapter(uow.conn, action=payload.action, organization_id=payload.organization_id, bot_id=(bot or {}).get("id") or payload.bot_id)
        route_context, policy_evaluation = self._resolve_specialist_policy_context(
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
        confirmation_token = self._build_confirmation_token(run_id=run_id, normalized_payload=normalized)
        blocked = bool(policy_evaluation and (policy_evaluation.get("decision") or {}).get("enforcement") == "block")
        status = "preview_blocked" if blocked else "preview_ready"
        confirmation_hash = self._hash_confirmation_token(confirmation_token) if policy.requires_confirmation and not blocked else None
        policy_row = None
        self._insert_run(
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
        self._insert_step(uow.conn, execution_run_id=run_id, organization_id=payload.organization_id, action=payload.action, step_name="preview.validated", status="blocked" if blocked else "ok", adapter_key=adapter.key, provider=adapter.provider, payload={"summary": preview.get("summary")})
        if policy_evaluation:
            self._insert_step(uow.conn, execution_run_id=run_id, organization_id=payload.organization_id, action=payload.action, step_name="policy.evaluated", status="blocked" if blocked else ((policy_evaluation.get("decision") or {}).get("enforcement") or "ok"), adapter_key=adapter.key, provider=adapter.provider, payload=policy_evaluation)
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
            "execution": self._serialize_run(uow.conn, row),
            "preview": preview,
            "policy": self._serialize_policy(policy_row) if policy_row else policy_evaluation,
            "confirmation_token": confirmation_token if policy.requires_confirmation and not blocked else None,
        })

    def execute(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        normalized = self._normalize_payload(uow.conn, payload=payload)
        policy = self._policy(payload.action)
        require_permission(user, payload.organization_id, policy.permission)
        bot = self._validate_bot_access(uow.conn, organization_id=payload.organization_id, bot_id=normalized.get("bot_id") or payload.bot_id, user=user)
        adapter, context = self._resolve_adapter(uow.conn, action=payload.action, organization_id=payload.organization_id, bot_id=(bot or {}).get("id") or payload.bot_id)
        route_context, policy_evaluation = self._resolve_specialist_policy_context(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=(bot or {}).get("id") or payload.bot_id,
            normalized_payload=normalized,
            metadata=payload.metadata,
            requested_action=payload.action,
        )
        self._enforce_policy_or_raise(policy_evaluation)
        preview_run = self._resolve_preview_run(uow.conn, payload=payload, user=user, normalized=normalized, policy=policy)
        idempotency_key = payload.idempotency_key or self._default_idempotency_key(payload.action, payload.organization_id, normalized)
        existing_job = get_job_execution(uow.conn, dedupe_key=idempotency_key)
        if existing_job and existing_job.get("status") == "completed":
            replay_id = new_id("toolrun")
            original = fetch_one(
                uow.conn,
                "SELECT * FROM tool_execution_runs WHERE organization_id = ? AND idempotency_key = ? AND status = 'completed' ORDER BY created_at DESC LIMIT 1",
                (payload.organization_id, idempotency_key),
            )
            now = utcnow_iso()
            self._insert_run(
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
                metadata={**payload.metadata, "idempotent": True},
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
            self._insert_step(uow.conn, execution_run_id=replay_id, organization_id=payload.organization_id, action=payload.action, step_name="idempotency.replayed", status="ok", adapter_key=adapter.key, provider=adapter.provider, payload={"original_run_id": (original or {}).get("id")})
            uow.commit()
            row = fetch_one(uow.conn, "SELECT * FROM tool_execution_runs WHERE id = ?", (replay_id,))
            return ok({"execution": self._serialize_run(uow.conn, row), "idempotent": True, "result": from_json(existing_job.get("result_json"), {})})
        if existing_job and existing_job.get("status") == "running":
            raise HTTPException(status_code=409, detail="tool_execution_already_running")
        if existing_job and existing_job.get("status") == "failed" and not payload.force_retry_failed:
            raise HTTPException(status_code=409, detail="tool_execution_failed_use_new_idempotency_key_or_force_retry_failed")

        begin_job_execution(uow.conn, job_type=f"tool_execution:{payload.action}", dedupe_key=idempotency_key, payload={"action": payload.action, "payload": normalized})
        run_id = new_id("toolrun")
        now = utcnow_iso()
        self._insert_run(
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
            metadata=payload.metadata,
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
        self._insert_step(uow.conn, execution_run_id=run_id, organization_id=payload.organization_id, action=payload.action, step_name="authorization.checked", status="ok", adapter_key=adapter.key, provider=adapter.provider, payload={"permission": policy.permission, "requires_confirmation": policy.requires_confirmation})
        if policy_evaluation:
            self._insert_step(uow.conn, execution_run_id=run_id, organization_id=payload.organization_id, action=payload.action, step_name="policy.evaluated", status=(policy_evaluation.get("decision") or {}).get("enforcement") or "ok", adapter_key=adapter.key, provider=adapter.provider, payload=policy_evaluation)
        try:
            result = adapter.execute(uow.conn, action=payload.action, normalized_payload=normalized, context=context, actor_user=user)
            completed_at = utcnow_iso()
            appointment_id = ((result.get("appointment") or {}).get("id")) or normalized.get("appointment_id")
            payment_id = ((result.get("payment") or {}).get("id")) or normalized.get("payment_id")
            lead_id = ((result.get("lead") or {}).get("id")) or normalized.get("lead_id")
            conversation_id = normalized.get("conversation_id") or ((result.get("payment") or {}).get("conversation_id")) or ((result.get("appointment") or {}).get("conversation_id"))
            contact_id = normalized.get("contact_id") or ((result.get("payment") or {}).get("contact_id")) or ((result.get("appointment") or {}).get("contact_id"))
            execute(
                uow.conn,
                "UPDATE tool_execution_runs SET status = 'completed', target_ref_json = ?, result_json = ?, completed_at = ?, updated_at = ?, appointment_id = COALESCE(appointment_id, ?), payment_id = COALESCE(payment_id, ?), lead_id = COALESCE(lead_id, ?), conversation_id = COALESCE(conversation_id, ?), contact_id = COALESCE(contact_id, ?) WHERE id = ?",
                (
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
            closed_loop = self._record_closed_loop_feedback(
                uow.conn,
                run_id=run_id,
                organization_id=payload.organization_id,
                bot=bot,
                action=payload.action,
                adapter=adapter,
                normalized_payload={**normalized, "appointment_id": appointment_id, "payment_id": payment_id, "lead_id": lead_id, "conversation_id": conversation_id, "contact_id": contact_id},
                result=result,
                metadata={**payload.metadata, "policy_profile_key": (policy_evaluation or {}).get("policy_profile_key")},
                actor_user=user,
                completed_at=completed_at,
            )
            if closed_loop:
                result = {**result, "closed_loop": closed_loop}
                execute(uow.conn, "UPDATE tool_execution_runs SET result_json = ?, updated_at = ? WHERE id = ?", (to_json(result), completed_at, run_id))
            self._insert_step(uow.conn, execution_run_id=run_id, organization_id=payload.organization_id, action=payload.action, step_name="adapter.executed", status="ok", adapter_key=adapter.key, provider=adapter.provider, payload={"target_ref": result.get("target_ref") or {}, "closed_loop": closed_loop})
            mark_job_completed(uow.conn, dedupe_key=idempotency_key, result=result)
            create_audit_log(
                uow.conn,
                organization_id=payload.organization_id,
                actor_user_id=user["id"],
                actor_type="user",
                entity_type="tool_execution_run",
                entity_id=run_id,
                action="tool_execution.executed",
                metadata={"action": payload.action, "adapter_key": adapter.key, "provider": adapter.provider, "idempotency_key": idempotency_key, "policy_profile_key": (policy_evaluation or {}).get("policy_profile_key")},
            )
            uow.commit()
            row = fetch_one(uow.conn, "SELECT * FROM tool_execution_runs WHERE id = ?", (run_id,))
            return ok({"execution": self._serialize_run(uow.conn, row), "idempotent": False, "result": result, "policy": self._serialize_policy(policy_row) if policy_row else policy_evaluation})
        except HTTPException as exc:
            self._handle_execution_failure(uow, run_id=run_id, idempotency_key=idempotency_key, organization_id=payload.organization_id, action=payload.action, adapter=adapter, error={"detail": exc.detail, "status_code": exc.status_code}, user=user)
            raise
        except Exception as exc:
            self._handle_execution_failure(uow, run_id=run_id, idempotency_key=idempotency_key, organization_id=payload.organization_id, action=payload.action, adapter=adapter, error={"message": str(exc)}, user=user)
            raise HTTPException(status_code=500, detail=f"tool_execution_failed:{exc}") from exc

    def list_runs(self, uow: UnitOfWork, *, organization_id: str, action: str | None, status: str | None, limit: int, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        where = ["organization_id = ?"]
        params: list[Any] = [organization_id]
        if action:
            where.append("action = ?")
            params.append(action)
        if status:
            where.append("status = ?")
            params.append(status)
        rows = fetch_all(
            uow.conn,
            f"SELECT * FROM tool_execution_runs WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT ?",
            tuple([*params, limit]),
        )
        return ok({"items": [self._serialize_run(uow.conn, row) for row in rows], "count": len(rows)})

    def get_run(self, uow: UnitOfWork, *, execution_id: str, user: dict) -> dict[str, Any]:
        row = fetch_one(uow.conn, "SELECT * FROM tool_execution_runs WHERE id = ?", (execution_id,))
        if not row:
            raise HTTPException(status_code=404, detail="tool_execution_run_not_found")
        ensure_org_access(user, row["organization_id"])
        require_permission(user, row["organization_id"], "operations.read")
        return ok(self._serialize_run(uow.conn, row))

    def _handle_execution_failure(self, uow: UnitOfWork, *, run_id: str, idempotency_key: str, organization_id: str, action: str, adapter: BaseAdapter, error: dict[str, Any], user: dict) -> None:
        now = utcnow_iso()
        execute(uow.conn, "UPDATE tool_execution_runs SET status = 'failed', error_json = ?, completed_at = ?, updated_at = ? WHERE id = ?", (to_json(error), now, now, run_id))
        self._insert_step(uow.conn, execution_run_id=run_id, organization_id=organization_id, action=action, step_name="adapter.executed", status="failed", adapter_key=adapter.key, provider=adapter.provider, payload=error)
        mark_job_failed(uow.conn, dedupe_key=idempotency_key, error_text=to_json(error))
        create_audit_log(
            uow.conn,
            organization_id=organization_id,
            actor_user_id=user["id"],
            actor_type="user",
            entity_type="tool_execution_run",
            entity_id=run_id,
            action="tool_execution.failed",
            metadata={"action": action, "adapter_key": adapter.key, "provider": adapter.provider, "error": error},
            severity="error",
        )
        uow.commit()

    def _record_closed_loop_feedback(
        self,
        conn,
        *,
        run_id: str,
        organization_id: str,
        bot: dict[str, Any] | None,
        action: str,
        adapter: BaseAdapter,
        normalized_payload: dict[str, Any],
        result: dict[str, Any],
        metadata: dict[str, Any],
        actor_user: dict[str, Any],
        completed_at: str,
    ) -> dict[str, Any]:
        if not _table_exists(conn, "outcome_exposures") or not _table_exists(conn, "outcome_events"):
            return {}
        resolved_bot_id = (bot or {}).get("id") or normalized_payload.get("bot_id") or (result.get("payment") or {}).get("bot_id") or (result.get("appointment") or {}).get("bot_id") or (result.get("lead") or {}).get("bot_id")
        if not resolved_bot_id:
            return {}
        exposure_id = new_id("outcome_exposure")
        vertical = normalized_payload.get("vertical") or (bot or {}).get("vertical")
        funnel_stage = self._derive_funnel_stage(action=action, normalized_payload=normalized_payload, result=result)
        execute(
            conn,
            """
            INSERT INTO outcome_exposures (
                id, organization_id, bot_id, conversation_id, contact_id, lead_id, appointment_id, payment_id,
                message_id, source_type, channel, prompt_run_id, prompt_version_id, flow_id, flow_version_id,
                template_id, template_version_id, routing_rule_id, decision_path_id, timing_policy_id,
                tone_policy_id, nba_policy_id, escalation_policy_id, playbook_id, playbook_version_id,
                handoff_id, handoff_kind, operator_user_id, assigned_variant, vertical, funnel_stage,
                metadata_json, sent_at, created_at, tool_execution_run_id, tool_action, tool_adapter_key, tool_provider,
                policy_profile_key, policy_profile_version, policy_evaluation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exposure_id,
                organization_id,
                resolved_bot_id,
                normalized_payload.get("conversation_id"),
                normalized_payload.get("contact_id"),
                normalized_payload.get("lead_id"),
                normalized_payload.get("appointment_id"),
                normalized_payload.get("payment_id"),
                None,
                "tool_execution",
                str((metadata or {}).get("channel") or "system"),
                (metadata or {}).get("prompt_run_id"),
                None,
                (metadata or {}).get("flow_id"),
                None,
                (metadata or {}).get("template_id"),
                None,
                None,
                (metadata or {}).get("decision_path_id"),
                None,
                None,
                None,
                None,
                None,
                None,
                (metadata or {}).get("handoff_id"),
                None,
                actor_user.get("id"),
                None,
                vertical,
                funnel_stage,
                to_json({
                    **(metadata or {}),
                    "tool_execution_run_id": run_id,
                    "tool_action": action,
                    "tool_adapter_key": adapter.key,
                    "tool_provider": adapter.provider,
                    "idempotency_key": normalized_payload.get("idempotency_key"),
                }),
                completed_at,
                completed_at,
                run_id,
                action,
                adapter.key,
                adapter.provider,
                (metadata or {}).get("policy_profile_key"),
                (metadata or {}).get("policy_profile_version"),
                (metadata or {}).get("policy_evaluation_id"),
            ),
        )
        auto_event = self._build_auto_outcome_event(
            run_id=run_id,
            organization_id=organization_id,
            bot_id=resolved_bot_id,
            action=action,
            adapter=adapter,
            normalized_payload=normalized_payload,
            result=result,
            actor_user=actor_user,
            vertical=vertical,
            funnel_stage=funnel_stage,
            completed_at=completed_at,
        )
        attribution_summary = None
        event_row = None
        if auto_event:
            execute(
                conn,
                """
                INSERT INTO outcome_events (
                    id, organization_id, bot_id, conversation_id, contact_id, lead_id, appointment_id, payment_id,
                    review_id, event_name, event_category, event_timestamp, source_system, external_event_id,
                    status, value_number, value_text, value_json, operator_user_id, vertical, funnel_stage,
                    dedupe_key, created_at, source_execution_run_id, source_tool_action, source_tool_provider
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    auto_event["id"],
                    organization_id,
                    auto_event["bot_id"],
                    auto_event.get("conversation_id"),
                    auto_event.get("contact_id"),
                    auto_event.get("lead_id"),
                    auto_event.get("appointment_id"),
                    auto_event.get("payment_id"),
                    auto_event["event_name"],
                    auto_event["event_category"],
                    auto_event["event_timestamp"],
                    auto_event["source_system"],
                    auto_event.get("external_event_id"),
                    auto_event.get("status") or "recorded",
                    auto_event.get("value_number"),
                    auto_event.get("value_text"),
                    to_json(auto_event.get("value") or {}),
                    actor_user.get("id"),
                    vertical,
                    funnel_stage,
                    auto_event["dedupe_key"],
                    completed_at,
                    run_id,
                    action,
                    adapter.provider,
                ),
            )
            event_row = fetch_one(conn, "SELECT * FROM outcome_events WHERE id = ?", (auto_event["id"],))
            attribution_summary = outcomes_service._materialize_attribution_for_event(conn, event_row=event_row, attribution_window_hours=168)
        outcomes_service._recompute_scorecards(conn, organization_id=organization_id, bot_id=resolved_bot_id, windows=["7d", "28d"], attribution_window_hours=168)
        return {
            "exposure_id": exposure_id,
            "event_id": (event_row or {}).get("id") if event_row else None,
            "event_name": (event_row or {}).get("event_name") if event_row else None,
            "funnel_stage": funnel_stage,
            "scorecards_refreshed": ["7d", "28d"],
            "attribution": attribution_summary,
        }

    def _build_auto_outcome_event(
        self,
        *,
        run_id: str,
        organization_id: str,
        bot_id: str | None,
        action: str,
        adapter: BaseAdapter,
        normalized_payload: dict[str, Any],
        result: dict[str, Any],
        actor_user: dict[str, Any],
        vertical: str | None,
        funnel_stage: str | None,
        completed_at: str,
    ) -> dict[str, Any] | None:
        base: dict[str, Any] = {
            "id": new_id("outcome_event"),
            "organization_id": organization_id,
            "bot_id": bot_id,
            "conversation_id": normalized_payload.get("conversation_id"),
            "contact_id": normalized_payload.get("contact_id"),
            "lead_id": normalized_payload.get("lead_id"),
            "appointment_id": normalized_payload.get("appointment_id"),
            "payment_id": normalized_payload.get("payment_id"),
            "event_timestamp": completed_at,
            "source_system": "tool_execution",
            "external_event_id": run_id,
            "status": "recorded",
            "value": {
                "tool_execution_run_id": run_id,
                "tool_action": action,
                "tool_adapter_key": adapter.key,
                "tool_provider": adapter.provider,
            },
            "vertical": vertical,
            "funnel_stage": funnel_stage,
        }
        if action == "book_appointment":
            return {
                **base,
                "event_name": "appointment_scheduled",
                "event_category": "appointment",
                "value_number": None,
                "value_text": normalized_payload.get("scheduled_for"),
                "dedupe_key": f"tool-execution:{run_id}:appointment_scheduled",
            }
        if action == "reschedule":
            return {
                **base,
                "event_name": "appointment_rescheduled",
                "event_category": "appointment",
                "value_number": None,
                "value_text": normalized_payload.get("scheduled_for"),
                "dedupe_key": f"tool-execution:{run_id}:appointment_rescheduled",
            }
        if action == "create_payment_link":
            return {
                **base,
                "event_name": "payment_started",
                "event_category": "payment",
                "value_number": float(normalized_payload.get("amount") or 0),
                "value_text": normalized_payload.get("currency"),
                "dedupe_key": f"tool-execution:{run_id}:payment_started",
            }
        if action == "update_contact_stage":
            lead = result.get("lead") or {}
            value = {**base["value"], "stage": lead.get("stage") or normalized_payload.get("stage"), "estimated_amount": normalized_payload.get("estimated_amount")}
            return {
                **base,
                "event_name": "lead_stage_progressed",
                "event_category": "crm",
                "value_number": float(normalized_payload.get("estimated_amount") or 0) if normalized_payload.get("estimated_amount") is not None else None,
                "value_text": lead.get("stage") or normalized_payload.get("stage"),
                "value": value,
                "dedupe_key": f"tool-execution:{run_id}:lead_stage_progressed",
            }
        if action == "send_receipt":
            return {
                **base,
                "event_name": "receipt_sent",
                "event_category": "payment_ops",
                "value_number": None,
                "value_text": normalized_payload.get("payment_id"),
                "dedupe_key": f"tool-execution:{run_id}:receipt_sent",
            }
        return None

    def _derive_funnel_stage(self, *, action: str, normalized_payload: dict[str, Any], result: dict[str, Any]) -> str | None:
        if action in {"book_appointment", "reschedule"}:
            return "appointment"
        if action in {"create_payment_link", "send_receipt"}:
            return "payment"
        if action == "update_contact_stage":
            return str((result.get("lead") or {}).get("stage") or normalized_payload.get("stage") or "crm")
        return normalized_payload.get("funnel_stage")


    def _policy(self, action: str) -> ActionPolicy:
        policy = DEFAULT_ACTION_POLICIES.get(action)
        if not policy:
            raise HTTPException(status_code=400, detail="unsupported_tool_action")
        return policy

    def _validate_bot_access(self, conn, *, organization_id: str, bot_id: str | None, user: dict) -> dict[str, Any] | None:
        if not bot_id:
            return None
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if bot["organization_id"] != organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)
        return bot

    def _resolve_preview_run(self, conn, *, payload, user: dict, normalized: dict[str, Any], policy: ActionPolicy) -> dict[str, Any] | None:
        if not policy.requires_confirmation:
            return None
        if payload.preview_execution_id:
            preview = fetch_one(conn, "SELECT * FROM tool_execution_runs WHERE id = ?", (payload.preview_execution_id,))
            if not preview:
                raise HTTPException(status_code=404, detail="tool_execution_preview_not_found")
            ensure_org_access(user, preview["organization_id"])
            if preview["organization_id"] != payload.organization_id or preview["action"] != payload.action:
                raise HTTPException(status_code=409, detail="tool_execution_preview_scope_mismatch")
            expected = preview.get("confirmation_token_hash")
            if expected and self._hash_confirmation_token(payload.confirmation_token or "") != expected:
                raise HTTPException(status_code=409, detail="tool_execution_confirmation_token_invalid")
            if from_json(preview.get("normalized_payload_json"), {}) != normalized:
                raise HTTPException(status_code=409, detail="tool_execution_preview_payload_mismatch")
            now = utcnow_iso()
            execute(conn, "UPDATE tool_execution_runs SET confirmed_by = ?, confirmed_at = ?, updated_at = ? WHERE id = ?", (user["id"], now, now, preview["id"]))
            return preview
        if payload.confirm:
            return None
        raise HTTPException(status_code=409, detail="tool_execution_requires_confirmation")

    def _normalize_payload(self, conn, *, payload) -> dict[str, Any]:
        raw = dict(payload.payload or {})
        if payload.bot_id and "bot_id" not in raw:
            raw["bot_id"] = payload.bot_id
        raw.setdefault("organization_id", payload.organization_id)
        if payload.action == "book_appointment":
            if not raw.get("bot_id"):
                raise HTTPException(status_code=400, detail="book_appointment_requires_bot_id")
            if not raw.get("scheduled_for"):
                raise HTTPException(status_code=400, detail="book_appointment_requires_scheduled_for")
            if not raw.get("conversation_id") and not raw.get("contact_id"):
                raise HTTPException(status_code=400, detail="book_appointment_requires_contact_or_conversation")
            return {
                "organization_id": payload.organization_id,
                "bot_id": raw["bot_id"],
                "conversation_id": raw.get("conversation_id"),
                "contact_id": raw.get("contact_id"),
                "scheduled_for": raw["scheduled_for"],
                "status": raw.get("status") or "scheduled",
                "duration_minutes": int(raw.get("duration_minutes") or 30),
                "timezone": raw.get("timezone") or "America/Mexico_City",
                "notes": raw.get("notes") or "",
            }
        if payload.action == "reschedule":
            appointment = fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", (raw.get("appointment_id"),)) if raw.get("appointment_id") else None
            if not appointment:
                raise HTTPException(status_code=404, detail="appointment_not_found")
            if appointment["organization_id"] != payload.organization_id:
                raise HTTPException(status_code=403, detail="appointment_scope_mismatch")
            if not raw.get("scheduled_for"):
                raise HTTPException(status_code=400, detail="reschedule_requires_scheduled_for")
            return {
                "organization_id": payload.organization_id,
                "bot_id": appointment.get("bot_id"),
                "appointment_id": raw["appointment_id"],
                "scheduled_for": raw["scheduled_for"],
                "conversation_id": appointment.get("conversation_id"),
                "contact_id": appointment.get("contact_id"),
            }
        if payload.action == "create_payment_link":
            required = ["bot_id", "conversation_id", "contact_id", "title"]
            missing = [item for item in required if not raw.get(item)]
            if missing:
                raise HTTPException(status_code=400, detail=f"create_payment_link_missing:{','.join(missing)}")
            amount = float(raw.get("amount") or 0)
            if amount <= 0:
                raise HTTPException(status_code=400, detail="create_payment_link_requires_positive_amount")
            return {
                "organization_id": payload.organization_id,
                "bot_id": raw["bot_id"],
                "conversation_id": raw["conversation_id"],
                "contact_id": raw["contact_id"],
                "title": raw["title"],
                "amount": amount,
                "currency": raw.get("currency") or "MXN",
                "reminder_minutes": int(raw.get("reminder_minutes") or 60),
                "send_receipt_on_confirm": bool(raw.get("send_receipt_on_confirm", True)),
                "metadata": {**(raw.get("metadata") or {}), **({"appointment_id": raw["appointment_id"]} if raw.get("appointment_id") else {})},
            }
        if payload.action == "update_contact_stage":
            required = ["bot_id", "contact_id", "stage"]
            missing = [item for item in required if not raw.get(item)]
            if missing:
                raise HTTPException(status_code=400, detail=f"update_contact_stage_missing:{','.join(missing)}")
            return {
                "organization_id": payload.organization_id,
                "bot_id": raw["bot_id"],
                "contact_id": raw["contact_id"],
                "conversation_id": raw.get("conversation_id"),
                "stage": str(raw["stage"]),
                "estimated_amount": float(raw.get("estimated_amount") or 0),
                "owner_user_id": raw.get("owner_user_id"),
                "next_action": raw.get("next_action") or "Calificar lead",
                "followup_at": raw.get("followup_at"),
                "tags": list(raw.get("tags") or []),
                "notes": raw.get("notes") or "",
                "lost_reason": raw.get("lost_reason"),
                "language": raw.get("language") or "es",
                "source_channel": raw.get("source_channel") or "whatsapp",
                "source_campaign": raw.get("source_campaign") or "orgánico",
            }
        if payload.action == "send_receipt":
            payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (raw.get("payment_id"),)) if raw.get("payment_id") else None
            if not payment:
                raise HTTPException(status_code=404, detail="payment_not_found")
            if payment["organization_id"] != payload.organization_id:
                raise HTTPException(status_code=403, detail="payment_scope_mismatch")
            return {
                "organization_id": payload.organization_id,
                "bot_id": payment.get("bot_id"),
                "payment_id": raw["payment_id"],
                "conversation_id": payment.get("conversation_id"),
                "contact_id": payment.get("contact_id"),
                "allow_unpaid_receipt": bool(raw.get("allow_unpaid_receipt", False)),
                "receipt_body": raw.get("receipt_body"),
            }
        raise HTTPException(status_code=400, detail="unsupported_tool_action")

    def _resolve_adapter(self, conn, *, action: str, organization_id: str, bot_id: str | None) -> tuple[BaseAdapter, dict[str, Any]]:
        integration = None
        if action in {"book_appointment", "reschedule"}:
            integration = self._latest_integration(conn, organization_id=organization_id, bot_id=bot_id, integration_type="calendar", provider="google_calendar")
            if integration:
                return GoogleCalendarAdapter(), {"integration": integration}
            return WaosCalendarAdapter(), {"integration": None}
        if action in {"create_payment_link", "send_receipt"}:
            integration = self._latest_integration(conn, organization_id=organization_id, bot_id=bot_id, integration_type="payments", provider="stripe") or self._latest_integration(conn, organization_id=organization_id, bot_id=bot_id, integration_type="commerce", provider="stripe")
            return StripePaymentsAdapter(), {"integration": integration}
        if action == "update_contact_stage":
            return WaosCrmAdapter(), {"integration": None}
        raise HTTPException(status_code=400, detail="unsupported_tool_action")

    def _latest_integration(self, conn, *, organization_id: str, bot_id: str | None, integration_type: str, provider: str | None = None) -> dict[str, Any] | None:
        where = ["organization_id = ?", "integration_type = ?", "status IN ('active','configured','connected')"]
        params: list[Any] = [organization_id, integration_type]
        if provider:
            where.append("provider = ?")
            params.append(provider)
        if bot_id:
            row = fetch_one(
                conn,
                f"SELECT * FROM integration_connections WHERE {' AND '.join(where)} AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY updated_at DESC LIMIT 1",
                tuple([*params, bot_id]),
            )
            if row:
                return row
        return fetch_one(
            conn,
            f"SELECT * FROM integration_connections WHERE {' AND '.join(where)} AND bot_id IS NULL ORDER BY updated_at DESC LIMIT 1",
            tuple(params),
        )

    def _default_idempotency_key(self, action: str, organization_id: str, normalized_payload: dict[str, Any]) -> str:
        return f"tool-exec:{organization_id}:{action}:{hash_value(to_json(normalized_payload))}"

    def _build_confirmation_token(self, *, run_id: str, normalized_payload: dict[str, Any]) -> str:
        return hashlib.sha256(f"{run_id}:{to_json(normalized_payload)}".encode("utf-8")).hexdigest()[:24]

    def _hash_confirmation_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest() if token else ""

    def _resolve_specialist_policy_context(self, conn, *, organization_id: str, bot_id: str | None, normalized_payload: dict[str, Any], metadata: dict[str, Any], requested_action: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        metadata = dict(metadata or {})
        route_row = None
        conversation = None
        if metadata.get("agent_routing_run_id") and _table_exists(conn, "agent_routing_runs"):
            route_row = fetch_one(conn, "SELECT * FROM agent_routing_runs WHERE id = ?", (metadata.get("agent_routing_run_id"),))
        conversation_id = normalized_payload.get("conversation_id")
        contact_id = normalized_payload.get("contact_id")
        if conversation_id and _table_exists(conn, "conversations"):
            conversation = fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (conversation_id,))
            contact_id = contact_id or (conversation or {}).get("contact_id")
        route_context = None
        if route_row:
            route_context = {
                "specialist_agent_key": route_row.get("specialist_agent_key"),
                "specialist_agent_version": route_row.get("specialist_agent_version"),
                "intent_family": route_row.get("intent_family"),
                "prompt_base_id": route_row.get("prompt_base_id"),
                "allowed_tools": from_json(route_row.get("allowed_tools_json"), []),
                "risk_policy": from_json(route_row.get("risk_policy_json"), {}),
                "agent_routing_run_id": route_row.get("id"),
            }
        elif metadata.get("specialist_agent_key"):
            profile = get_policy_profile_for_specialist(metadata.get("specialist_agent_key"))
            route_context = {
                "specialist_agent_key": profile.specialist_agent_key,
                "specialist_agent_version": profile.version,
                "intent_family": profile.intent_family,
                "prompt_base_id": f"prompt_{profile.specialist_agent_key}_policy_proxy_v1",
                "allowed_tools": list(profile.allowed_actions),
                "risk_policy": {"level": "medium"},
                "agent_routing_run_id": metadata.get("agent_routing_run_id"),
            }
        if not route_context:
            return None, None
        shared_memory = build_shared_memory_context(
            conn=conn,
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            contact_id=contact_id,
            memory={},
            recent_messages=[],
        )
        classification = {
            "intent": metadata.get("intent") or route_context.get("intent_family"),
            "urgency_score": metadata.get("urgency_score") or 0,
            "requested_human": bool(metadata.get("requested_human")),
        }
        policy_evaluation = evaluate_specialist_policy(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            contact_id=contact_id,
            route=route_context,
            classification=classification,
            conversation=conversation or {},
            shared_memory=shared_memory,
            requested_action=requested_action,
        )
        return route_context, policy_evaluation

    def _enforce_policy_or_raise(self, policy_evaluation: dict[str, Any] | None) -> None:
        if not policy_evaluation:
            return
        decision = policy_evaluation.get("decision") or {}
        if decision.get("enforcement") == "block":
            violations = ",".join(decision.get("violations") or ["policy_blocked"])
            raise HTTPException(status_code=409, detail=f"tool_execution_policy_blocked:{violations}")

    def _serialize_policy(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {
            **row,
            "decision": from_json(row.get("decision_json"), {}),
            "budget_state": from_json(row.get("budget_state_json"), {}),
            "sla_state": from_json(row.get("sla_state_json"), {}),
            "observed": from_json(row.get("observed_json"), {}),
        }

    def _insert_run(
        self,
        conn,
        *,
        run_id: str,
        organization_id: str,
        bot_id: str | None,
        action: str,
        adapter_key: str,
        provider: str | None,
        execution_mode: str,
        status: str,
        permission_required: str,
        requires_confirmation: bool,
        confirmation_token_hash: str | None,
        request: dict[str, Any],
        normalized_payload: dict[str, Any],
        validation: dict[str, Any],
        target_ref: dict[str, Any],
        result: dict[str, Any],
        error: dict[str, Any],
        metadata: dict[str, Any],
        user_id: str,
        preview_run_id: str | None = None,
        idempotency_key: str | None = None,
        idempotent_replay_of_run_id: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        specialist_agent_key: str | None = None,
        agent_routing_run_id: str | None = None,
        policy_profile_key: str | None = None,
        policy_profile_version: str | None = None,
        policy_evaluation_id: str | None = None,
        policy_payload: dict[str, Any] | None = None,
    ) -> None:
        now = utcnow_iso()
        execute(
            conn,
            """
            INSERT INTO tool_execution_runs (
                id, organization_id, bot_id, action, adapter_key, provider, execution_mode, status,
                permission_required, requires_confirmation, confirmation_token_hash, confirmed_by, confirmed_at,
                preview_run_id, idempotency_key, idempotent_replay_of_run_id, request_json, normalized_payload_json,
                validation_json, target_ref_json, result_json, error_json, metadata_json,
                prompt_run_id, flow_id, template_id, decision_path_id, handoff_id,
                conversation_id, contact_id, lead_id, appointment_id, payment_id,
                requested_by, started_at, completed_at, specialist_agent_key, agent_routing_run_id,
                policy_profile_key, policy_profile_version, policy_evaluation_id, policy_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                organization_id,
                bot_id,
                action,
                adapter_key,
                provider,
                execution_mode,
                status,
                permission_required,
                1 if requires_confirmation else 0,
                confirmation_token_hash,
                preview_run_id,
                idempotency_key,
                idempotent_replay_of_run_id,
                to_json(request),
                to_json(normalized_payload),
                to_json(validation),
                to_json(target_ref),
                to_json(result),
                to_json(error),
                to_json(metadata),
                (metadata or {}).get("prompt_run_id"),
                (metadata or {}).get("flow_id"),
                (metadata or {}).get("template_id"),
                (metadata or {}).get("decision_path_id"),
                (metadata or {}).get("handoff_id"),
                normalized_payload.get("conversation_id"),
                normalized_payload.get("contact_id"),
                normalized_payload.get("lead_id"),
                normalized_payload.get("appointment_id"),
                normalized_payload.get("payment_id"),
                user_id,
                started_at,
                completed_at,
                specialist_agent_key,
                agent_routing_run_id,
                policy_profile_key,
                policy_profile_version,
                policy_evaluation_id,
                to_json(policy_payload or {}),
                now,
                now,
            ),
        )

    def _insert_step(self, conn, *, execution_run_id: str, organization_id: str, action: str, step_name: str, status: str, adapter_key: str | None, provider: str | None, payload: dict[str, Any]) -> None:
        execute(
            conn,
            "INSERT INTO tool_execution_step_logs (id, execution_run_id, organization_id, action, step_name, status, adapter_key, provider, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id("toolstep"), execution_run_id, organization_id, action, step_name, status, adapter_key, provider, to_json(payload), utcnow_iso()),
        )

    def _serialize_run(self, conn, row: dict[str, Any]) -> dict[str, Any]:
        steps = fetch_all(conn, "SELECT * FROM tool_execution_step_logs WHERE execution_run_id = ? ORDER BY created_at ASC", (row["id"],))
        closed_loop = None
        if _table_exists(conn, "outcome_exposures") and _table_exists(conn, "outcome_attribution_facts") and _table_exists(conn, "outcome_scorecard_snapshots"):
            exposure = fetch_one(conn, "SELECT * FROM outcome_exposures WHERE tool_execution_run_id = ? ORDER BY sent_at DESC LIMIT 1", (row["id"],))
            auto_events = fetch_all(conn, "SELECT * FROM outcome_events WHERE source_execution_run_id = ? ORDER BY event_timestamp DESC", (row["id"],)) if _table_exists(conn, "outcome_events") else []
            attribution_rows = fetch_all(
                conn,
                """
                SELECT af.*, oe.event_name, oe.event_category, oe.event_timestamp, oe.value_number, oe.value_text, oe.value_json
                FROM outcome_attribution_facts af
                JOIN outcome_events oe ON oe.id = af.outcome_event_id
                JOIN outcome_exposures ox ON ox.id = af.exposure_id
                WHERE ox.tool_execution_run_id = ?
                ORDER BY oe.event_timestamp DESC, af.created_at DESC
                LIMIT 25
                """,
                (row["id"],),
            )
            action_scorecard = fetch_one(conn, "SELECT * FROM outcome_scorecard_snapshots WHERE organization_id = ? AND entity_type = 'tool_action' AND entity_id = ? ORDER BY computed_at DESC LIMIT 1", (row["organization_id"], row["action"]))
            provider_scorecard = fetch_one(conn, "SELECT * FROM outcome_scorecard_snapshots WHERE organization_id = ? AND entity_type = 'tool_provider' AND entity_id = ? ORDER BY computed_at DESC LIMIT 1", (row["organization_id"], row.get("provider") or "waos"))
            policy_scorecard = fetch_one(conn, "SELECT * FROM outcome_scorecard_snapshots WHERE organization_id = ? AND entity_type = 'policy_profile' AND entity_id = ? ORDER BY computed_at DESC LIMIT 1", (row["organization_id"], row.get("policy_profile_key"))) if row.get("policy_profile_key") else None
            closed_loop = {
                "exposure": {**exposure, "metadata": from_json((exposure or {}).get("metadata_json"), {})} if exposure else None,
                "auto_events": [{**event, "value": from_json(event.get("value_json"), {})} for event in auto_events],
                "linked_attribution": [{**item, "value": from_json(item.get("value_json"), {}), "details": from_json(item.get("details_json"), {})} for item in attribution_rows],
                "action_scorecard": outcomes_service._serialize_scorecard(action_scorecard) if action_scorecard else None,
                "provider_scorecard": outcomes_service._serialize_scorecard(provider_scorecard) if provider_scorecard else None,
                "policy_scorecard": outcomes_service._serialize_scorecard(policy_scorecard) if policy_scorecard else None,
            }
        return {
            **row,
            "request": from_json(row.get("request_json"), {}),
            "normalized_payload": from_json(row.get("normalized_payload_json"), {}),
            "validation": from_json(row.get("validation_json"), {}),
            "target_ref": from_json(row.get("target_ref_json"), {}),
            "result": from_json(row.get("result_json"), {}),
            "error": from_json(row.get("error_json"), {}),
            "metadata": from_json(row.get("metadata_json"), {}),
            "policy": from_json(row.get("policy_json"), {}),
            "requires_confirmation": bool(row.get("requires_confirmation")),
            "steps": [
                {
                    **step,
                    "payload": from_json(step.get("payload_json"), {}),
                }
                for step in steps
            ],
            "closed_loop": closed_loop,
        }


def _table_exists(conn, table: str) -> bool:
    row = fetch_one(conn, "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)) if getattr(conn, "backend", "sqlite") == "sqlite" else fetch_one(conn, "SELECT 1 AS present FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = ? LIMIT 1", (table,))
    return bool(row)


tool_execution_service = ToolExecutionService()
