from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ..agent_policy_runtime import evaluate_specialist_policy, get_policy_profile_for_specialist, persist_agent_policy_evaluation, serialize_policy_profile
from ..agent_runtime import build_grounded_context, plan_runtime_execution
from ..contracts import ok
from ..db import execute, fetch_all, fetch_one, table_exists
from ..multi_agent_runtime import (
    SPECIALIST_AGENTS,
    apply_specialist_plan,
    build_shared_memory_context,
    persist_agent_route_run,
    record_specialist_exposure,
    route_intent_to_specialist,
    supervise_specialist_route,
)
from ..repositories import create_audit_log, get_bot
from ..runtime_pipeline import understand_message
from ..security import ensure_bot_access, ensure_org_access
from ..utils import from_json
from .support import require_permission
from .uow import UnitOfWork


class AgentOrchestrationService:
    def list_specialists(self, uow: UnitOfWork, *, organization_id: str, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "conversation.manage")
        return ok({
            "router_version": "intent_router_v1",
            "supervisor_version": "specialist_supervisor_v1",
            "items": [
                {
                    "key": item.key,
                    "version": item.version,
                    "prompt_base_id": item.prompt_base_id,
                    "objective": item.objective,
                    "tone": item.tone,
                    "allowed_tools": list(item.allowed_tools),
                    "risk_level": item.risk_level,
                    "success_metrics": list(item.success_metrics),
                    "escalation_criteria": list(item.escalation_criteria),
                    "funnel_stage": item.funnel_stage,
                    "policy": serialize_policy_profile(get_policy_profile_for_specialist(item.key)),
                }
                for item in SPECIALIST_AGENTS.values()
            ],
        })

    def route_preview(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "conversation.manage")
        bot = get_bot(uow.conn, payload.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if bot["organization_id"] != payload.organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)

        conversation = {"human_takeover": 0, "status": "open"}
        if payload.conversation_id:
            conversation = fetch_one(uow.conn, "SELECT * FROM conversations WHERE id = ?", (payload.conversation_id,)) or conversation
            if conversation.get("organization_id") and conversation["organization_id"] != payload.organization_id:
                raise HTTPException(status_code=403, detail="Conversation does not belong to organization")

        memory = dict(payload.memory or {})
        if payload.contact_id and not memory:
            mem = fetch_one(uow.conn, "SELECT * FROM contact_memory WHERE contact_id = ? AND bot_id = ?", (payload.contact_id, payload.bot_id))
            if mem:
                memory = {
                    "lead_stage": mem.get("lead_stage"),
                    "lead_score": mem.get("lead_score"),
                    "summary": mem.get("summary"),
                    **from_json(mem.get("memory_json"), {}),
                }

        bot_config = dict(payload.bot_config or {})
        if not bot_config:
            bot_config = {
                "identity": {"business_name": bot.get("business_name") or bot.get("name"), "language": bot.get("language") or "es"},
                "objective": {"primary": "multi_agent_orchestration"},
                "business_knowledge": {},
                "rules": {},
                "handoff": {"sensitive_keywords": ["humano", "asesor"]},
            }

        classification = dict(payload.classification or {})
        if not classification:
            understanding = understand_message(
                payload.text,
                memory,
                bot_config,
                conn=uow.conn,
                organization_id=payload.organization_id,
                bot_id=payload.bot_id,
                conversation_id=payload.conversation_id,
            )
            classification = understanding["classification"]
        grounded = build_grounded_context(
            text=payload.text,
            memory=memory,
            bot_config=bot_config,
            conn=uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            contact_id=payload.contact_id or conversation.get("contact_id"),
            conversation_id=payload.conversation_id,
        )
        route = route_intent_to_specialist(
            text=payload.text,
            classification=classification,
            memory=memory,
            conversation=conversation,
            bot_config=bot_config,
        )
        shared_memory = build_shared_memory_context(
            conn=uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            conversation_id=payload.conversation_id,
            contact_id=payload.contact_id or conversation.get("contact_id"),
            memory=memory,
            recent_messages=payload.recent_messages,
        )
        policy_evaluation = evaluate_specialist_policy(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            conversation_id=payload.conversation_id,
            contact_id=payload.contact_id or conversation.get("contact_id"),
            route=route,
            classification=classification,
            conversation=conversation,
            shared_memory=shared_memory,
        )
        plan = plan_runtime_execution(
            text=payload.text,
            conversation=conversation,
            bot=bot,
            classification=classification,
            memory=memory,
            bot_config=bot_config,
            grounded_context=grounded,
        )
        plan = apply_specialist_plan(plan, route, shared_memory, policy_evaluation=policy_evaluation)
        supervisor = supervise_specialist_route(
            route=route,
            classification=classification,
            conversation=conversation,
            shared_memory=shared_memory,
            execution_plan=plan,
            policy_evaluation=policy_evaluation,
        )

        route_row = None
        exposure = None
        policy_row = None
        if payload.persist:
            route_row = persist_agent_route_run(
                uow.conn,
                organization_id=payload.organization_id,
                bot_id=payload.bot_id,
                conversation_id=payload.conversation_id,
                contact_id=payload.contact_id or conversation.get("contact_id"),
                message_id=payload.message_id,
                text=payload.text,
                classification=classification,
                route=route,
                shared_memory=shared_memory,
                execution_plan=plan,
                supervisor=supervisor,
                policy_evaluation=policy_evaluation,
            )
            policy_row = persist_agent_policy_evaluation(
                uow.conn,
                organization_id=payload.organization_id,
                bot_id=payload.bot_id,
                conversation_id=payload.conversation_id,
                contact_id=payload.contact_id or conversation.get("contact_id"),
                specialist_agent_key=route.get("specialist_agent_key"),
                policy_evaluation=policy_evaluation,
                agent_routing_run_id=(route_row or {}).get("id"),
            )
            if route_row and policy_row:
                execute(uow.conn, "UPDATE agent_routing_runs SET policy_evaluation_id = ?, updated_at = ? WHERE id = ?", (policy_row.get("id"), policy_row.get("created_at"), route_row.get("id")))
        if payload.record_exposure:
            exposure = record_specialist_exposure(
                uow.conn,
                organization_id=payload.organization_id,
                bot_id=payload.bot_id,
                conversation_id=payload.conversation_id,
                contact_id=payload.contact_id or conversation.get("contact_id"),
                message_id=payload.message_id,
                route=route,
                flow_id=route.get("specialist_agent_key"),
                prompt_run_id=(route_row or {}).get("id"),
                metadata={"agent_routing_run_id": (route_row or {}).get("id")},
                policy_evaluation=policy_evaluation,
                policy_evaluation_id=(policy_row or {}).get("id"),
            )

        create_audit_log(
            uow.conn,
            organization_id=payload.organization_id,
            actor_user_id=user["id"],
            actor_type="user",
            entity_type="agent_orchestration",
            entity_id=(route_row or {}).get("id") or route.get("specialist_agent_key"),
            action="agent.route.previewed",
            metadata={
                "bot_id": payload.bot_id,
                "specialist_agent": route.get("specialist_agent_key"),
                "intent_detected": classification.get("intent"),
                "record_exposure": payload.record_exposure,
                "policy_profile_key": policy_evaluation.get("policy_profile_key"),
                "policy_enforcement": (policy_evaluation.get("decision") or {}).get("enforcement"),
            },
        )
        uow.commit()
        return ok({
            "classification": classification,
            "route": route,
            "shared_memory": shared_memory,
            "grounded_context": grounded,
            "plan": plan,
            "supervisor": supervisor,
            "route_run": self._serialize_route(route_row),
            "policy": self._serialize_policy(policy_row) if policy_row else policy_evaluation,
            "exposure": exposure,
        })

    def conversation_overview(self, uow: UnitOfWork, *, conversation_id: str, user: dict) -> dict[str, Any]:
        conversation = fetch_one(uow.conn, "SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        ensure_org_access(user, conversation["organization_id"])
        require_permission(user, conversation["organization_id"], "conversation.manage")
        rows = fetch_all(
            uow.conn,
            "SELECT * FROM agent_routing_runs WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 20",
            (conversation_id,),
        ) if table_exists(uow.conn, "agent_routing_runs") else []
        latest = rows[0] if rows else None
        scorecards = fetch_all(
            uow.conn,
            "SELECT * FROM outcome_scorecard_snapshots WHERE organization_id = ? AND entity_type IN ('specialist_agent', 'policy_profile') AND scorecard_window = '28d' ORDER BY computed_at DESC LIMIT 40",
            (conversation["organization_id"],),
        ) if table_exists(uow.conn, "outcome_scorecard_snapshots") else []
        specialist_key = (latest or {}).get("specialist_agent_key")
        policy_profile_key = (latest or {}).get("policy_profile_key")
        latest_scorecard = None
        latest_policy_scorecard = None
        for item in scorecards:
            if item.get("entity_type") == "specialist_agent" and item.get("entity_id") == specialist_key and latest_scorecard is None:
                latest_scorecard = item
            if item.get("entity_type") == "policy_profile" and item.get("entity_id") == policy_profile_key and latest_policy_scorecard is None:
                latest_policy_scorecard = item
        return ok({
            "conversation_id": conversation_id,
            "latest_route": self._serialize_route(latest),
            "history": [self._serialize_route(item) for item in rows],
            "latest_scorecard": self._serialize_scorecard(latest_scorecard),
            "latest_policy_scorecard": self._serialize_scorecard(latest_policy_scorecard),
        })

    def _serialize_route(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {
            **row,
            "allowed_tools": from_json(row.get("allowed_tools_json"), []),
            "risk_policy": from_json(row.get("risk_policy_json"), {}),
            "success_metrics": from_json(row.get("success_metrics_json"), []),
            "route_reason": from_json(row.get("route_reason_json"), []),
            "shared_memory": from_json(row.get("shared_memory_json"), {}),
            "plan": from_json(row.get("plan_json"), {}),
            "supervisor": from_json(row.get("supervisor_json"), {}),
            "policy": from_json(row.get("policy_json"), {}),
        }

    def _serialize_scorecard(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {
            **row,
            "metrics": from_json(row.get("metrics_json"), {}),
            "guardrails": from_json(row.get("guardrails_json"), {}),
            "rationale": from_json(row.get("rationale_json"), {}),
        }

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


agent_orchestration_service = AgentOrchestrationService()
