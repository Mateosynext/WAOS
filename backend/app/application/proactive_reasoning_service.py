from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ..contracts import ok
from ..proactive_reasoning_runtime import evaluate_proactive_candidates, list_proactive_candidates, list_proactive_runs, materialize_proactive_candidate
from ..repositories import get_bot
from ..security import ensure_bot_access, ensure_org_access
from .support import require_permission
from .uow import UnitOfWork


class ProactiveReasoningService:
    def evaluate(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "conversation.manage")
        bot = get_bot(uow.conn, payload.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if bot["organization_id"] != payload.organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)
        result = evaluate_proactive_candidates(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            contact_ids=payload.contact_ids,
            conversation_ids=payload.conversation_ids,
            as_of=payload.as_of,
            persist=payload.persist,
            include_suppressed=payload.include_suppressed,
            limit=payload.limit,
            metadata=payload.metadata,
        )
        uow.commit()
        return ok(result)

    def list_candidates(
        self,
        uow: UnitOfWork,
        *,
        organization_id: str,
        bot_id: str | None,
        status: str | None,
        specialist_agent_key: str | None,
        eligible: bool | None,
        limit: int,
        user: dict,
    ) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        items = list_proactive_candidates(
            uow.conn,
            organization_id=organization_id,
            bot_id=bot_id,
            status=status,
            specialist_agent_key=specialist_agent_key,
            eligible=eligible,
            limit=limit,
        )
        return ok({"items": items, "count": len(items)})

    def materialize(self, uow: UnitOfWork, *, candidate_id: str, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "conversation.manage")
        candidate = list_proactive_candidates(uow.conn, organization_id=payload.organization_id, limit=500)
        target = next((item for item in candidate if item["id"] == candidate_id), None)
        if not target:
            raise HTTPException(status_code=404, detail="Candidate not found")
        if target.get("bot_id"):
            bot = get_bot(uow.conn, target["bot_id"])
            if bot:
                ensure_bot_access(user, bot)
        result = materialize_proactive_candidate(
            uow.conn,
            candidate_id=candidate_id,
            actor_user_id=user.get("id"),
            schedule_for=payload.schedule_for,
            record_exposure=payload.record_exposure,
            metadata=payload.metadata,
        )
        uow.commit()
        return ok(result)

    def list_runs(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, limit: int, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        items = list_proactive_runs(uow.conn, organization_id=organization_id, bot_id=bot_id, limit=limit)
        return ok({"items": items, "count": len(items)})


proactive_reasoning_service = ProactiveReasoningService()
