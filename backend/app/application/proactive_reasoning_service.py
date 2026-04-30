from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ..contracts import ok
from ..job_idempotency import begin_job_execution, mark_job_completed
from ..proactive_reasoning_runtime import evaluate_proactive_candidates, list_proactive_candidates, list_proactive_runs, materialize_proactive_candidate
from ..repositories import get_bot
from ..security import ensure_bot_access, ensure_org_access
from ..utils import from_json, hash_value, parse_iso, to_json
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
        if payload.schedule_for and not parse_iso(str(payload.schedule_for)):
            raise HTTPException(status_code=400, detail="invalid_schedule_for")
        if target.get("bot_id"):
            bot = get_bot(uow.conn, target["bot_id"])
            if bot:
                ensure_bot_access(user, bot)
        materialize_payload = {"candidate_id": candidate_id, "schedule_for": payload.schedule_for, "record_exposure": payload.record_exposure}
        request_key = str((payload.metadata or {}).get("idempotency_key") or hash_value(to_json(materialize_payload)))
        job_key = f"proactive:materialize:{payload.organization_id}:{candidate_id}:{request_key}"
        claim = begin_job_execution(uow.conn, job_type="proactive:materialize", dedupe_key=job_key, payload=materialize_payload)
        if claim.get("_payload_mismatch"):
            raise HTTPException(status_code=409, detail="proactive_materialize_idempotency_key_payload_mismatch")
        if claim.get("_already_existing") and claim.get("status") == "running":
            raise HTTPException(status_code=409, detail="proactive_materialize_already_running")
        if claim.get("status") == "completed":
            return ok({**from_json(claim.get("result_json"), {}), "idempotent": True})
        result = materialize_proactive_candidate(
            uow.conn,
            candidate_id=candidate_id,
            actor_user_id=user.get("id"),
            schedule_for=payload.schedule_for,
            record_exposure=payload.record_exposure,
            metadata={**payload.metadata, "idempotency_key": request_key},
        )
        mark_job_completed(uow.conn, dedupe_key=job_key, result=result)
        uow.commit()
        return ok(result)

    def list_runs(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, limit: int, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        items = list_proactive_runs(uow.conn, organization_id=organization_id, bot_id=bot_id, limit=limit)
        return ok({"items": items, "count": len(items)})


proactive_reasoning_service = ProactiveReasoningService()
