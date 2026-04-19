from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...application.growth_os_service import growth_os_service
from ...schemas import GrowthOsRunRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["growth_os"])


@router.get("/api/v1/growth-os/overview")
def growth_os_overview_route(
    organization_id: str = Query(...),
    bot_id: str = Query(...),
    scorecard_window: str = Query(default="28d"),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict[str, Any]:
    return growth_os_service.overview(uow, organization_id=organization_id, bot_id=bot_id, scorecard_window=scorecard_window, user=user)


@router.post("/api/v1/growth-os/run")
def growth_os_run_route(payload: GrowthOsRunRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return growth_os_service.run(uow, payload=payload, user=user)


@router.get("/api/v1/growth-os/runs")
def growth_os_runs_route(
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict[str, Any]:
    return growth_os_service.list_runs(uow, organization_id=organization_id, bot_id=bot_id, limit=limit, user=user)
