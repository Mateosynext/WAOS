from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ..agent_policy_runtime import evaluate_specialist_policy, get_policy_profile_for_specialist, persist_agent_policy_evaluation, serialize_policy_profile
from ..contracts import ok
from ..db import fetch_one, table_exists
from ..multi_agent_runtime import build_shared_memory_context
from ..repositories import get_bot
from ..security import ensure_bot_access, ensure_org_access
from ..utils import from_json
from .support import require_permission
from .uow import UnitOfWork


class AgentPolicyService:
    def list_profiles(self, uow: UnitOfWork, *, organization_id: str, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        items = []
        for key in ["booking", "sales", "support", "collections", "recovery", "retention", "general"]:
            items.append(serialize_policy_profile(get_policy_profile_for_specialist(key)))
        return ok({"items": items, "count": len(items)})

    def evaluate(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "conversation.manage")
        bot = get_bot(uow.conn, payload.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if bot["organization_id"] != payload.organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)

        conversation = dict(payload.conversation or {})
        if payload.conversation_id and not conversation and table_exists(uow.conn, "conversations"):
            conversation = fetch_one(uow.conn, "SELECT * FROM conversations WHERE id = ?", (payload.conversation_id,)) or {}
        route = dict(payload.route or {})
        if not route:
            profile = get_policy_profile_for_specialist(payload.specialist_agent_key)
            route = {
                "specialist_agent_key": profile.specialist_agent_key,
                "specialist_agent_version": profile.version,
                "intent_family": profile.intent_family,
                "allowed_tools": list(profile.allowed_actions),
                "risk_policy": {"level": "medium"},
            }
        shared_memory = dict(payload.shared_memory or {})
        if not shared_memory:
            shared_memory = build_shared_memory_context(
                conn=uow.conn,
                organization_id=payload.organization_id,
                bot_id=payload.bot_id,
                conversation_id=payload.conversation_id,
                contact_id=payload.contact_id or conversation.get("contact_id"),
                memory={},
                recent_messages=[],
            )
        evaluation = evaluate_specialist_policy(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            conversation_id=payload.conversation_id,
            contact_id=payload.contact_id or conversation.get("contact_id"),
            route=route,
            classification=payload.classification,
            conversation=conversation,
            shared_memory=shared_memory,
            requested_action=payload.requested_action,
        )
        row = None
        if payload.persist:
            row = persist_agent_policy_evaluation(
                uow.conn,
                organization_id=payload.organization_id,
                bot_id=payload.bot_id,
                conversation_id=payload.conversation_id,
                contact_id=payload.contact_id or conversation.get("contact_id"),
                specialist_agent_key=route.get("specialist_agent_key"),
                policy_evaluation=evaluation,
                requested_action=payload.requested_action,
            )
            uow.commit()
        return ok({"evaluation": self._serialize(row) if row else evaluation, "shared_memory": shared_memory})

    def _serialize(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {
            **row,
            "decision": from_json(row.get("decision_json"), {}),
            "budget_state": from_json(row.get("budget_state_json"), {}),
            "sla_state": from_json(row.get("sla_state_json"), {}),
            "observed": from_json(row.get("observed_json"), {}),
        }


agent_policy_service = AgentPolicyService()
