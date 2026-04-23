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

class ToolExecutionOutcomesMixin:
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
