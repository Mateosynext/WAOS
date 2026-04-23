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

class ToolExecutionPolicySupportMixin:
    def _policy(self, action: str) -> ActionPolicy:
        return resolve_action_policy(action)

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
