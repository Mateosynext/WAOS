from __future__ import annotations

import hashlib
from typing import Any

from fastapi import HTTPException

from ..agent_policy_runtime import evaluate_specialist_policy, get_policy_profile_for_specialist, persist_agent_policy_evaluation
from ..db import execute, fetch_all, fetch_one
from ..job_idempotency import begin_job_execution, get_job_execution, mark_job_completed, mark_job_failed
from ..multi_agent_runtime import build_shared_memory_context
from ..repositories import create_audit_log, get_bot
from ..security import ensure_bot_access, ensure_org_access
from ..utils import from_json, hash_value, new_id, to_json, utcnow_iso
from .outcomes_service import outcomes_service
from .tool_execution_adapters import (
    ActionPolicy,
    BaseAdapter,
    GoogleCalendarAdapter,
    StripePaymentsAdapter,
    WaosCalendarAdapter,
    WaosCrmAdapter,
)
from .tool_execution_policy import resolve_action_policy
from .tool_execution_presenters import serialize_tool_execution_run


def _table_exists(conn, table: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "sqlite":
        row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
        return bool(row)
    row = conn.execute(
        """
        SELECT 1 AS present
        FROM information_schema.tables
        WHERE table_schema = current_schema() AND table_name = ?
        LIMIT 1
        """,
        (table,),
    ).fetchone()
    return bool(row)

class ToolExecutionPersistenceMixin:
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
        return serialize_tool_execution_run(conn, row)
