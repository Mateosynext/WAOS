from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...application.optimizer_service import optimizer_service
from ...schemas import OptimizerEvaluateRequest, OptimizerRunRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["optimizer"])


@router.get("/api/v1/optimizer/overview")
def optimizer_overview_route(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
) -> dict[str, Any]:
    return optimizer_service.overview(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.get("/api/v1/optimizer/proposals")
def optimizer_proposals_route(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    return optimizer_service.list_proposals(uow, organization_id=organization_id, bot_id=bot_id, status=status, user=user)


@router.post("/api/v1/optimizer/run")
def optimizer_run_route(payload: OptimizerRunRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return optimizer_service.run_cycle(uow, payload=payload, user=user)


@router.post("/api/v1/optimizer/evaluate")
def optimizer_evaluate_route(payload: OptimizerEvaluateRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return optimizer_service.evaluate_experiments(uow, payload=payload, user=user)
