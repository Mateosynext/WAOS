from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...application.proactive_reasoning_service import proactive_reasoning_service
from ...schemas import ProactiveEvaluateRequest, ProactiveMaterializeRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["proactive_reasoning"])


@router.post("/api/v1/proactive-engine/evaluate")
def evaluate_proactive_engine(payload: ProactiveEvaluateRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return proactive_reasoning_service.evaluate(uow, payload=payload, user=user)


@router.get("/api/v1/proactive-engine/candidates")
def list_proactive_engine_candidates(
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    specialist_agent_key: str | None = Query(default=None),
    eligible: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict[str, Any]:
    return proactive_reasoning_service.list_candidates(
        uow,
        organization_id=organization_id,
        bot_id=bot_id,
        status=status,
        specialist_agent_key=specialist_agent_key,
        eligible=eligible,
        limit=limit,
        user=user,
    )


@router.post("/api/v1/proactive-engine/candidates/{candidate_id}/materialize")
def materialize_proactive_engine_candidate(candidate_id: str, payload: ProactiveMaterializeRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return proactive_reasoning_service.materialize(uow, candidate_id=candidate_id, payload=payload, user=user)


@router.get("/api/v1/proactive-engine/runs")
def list_proactive_engine_runs(
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict[str, Any]:
    return proactive_reasoning_service.list_runs(uow, organization_id=organization_id, bot_id=bot_id, limit=limit, user=user)
