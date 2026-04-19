from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...application.tool_execution_service import tool_execution_service
from ...schemas import ToolExecutionRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["tool_execution"])


@router.post("/api/v1/tool-executions/preview")
def preview_tool_execution(payload: ToolExecutionRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return tool_execution_service.preview(uow, payload=payload, user=user)


@router.post("/api/v1/tool-executions/execute")
def execute_tool_execution(payload: ToolExecutionRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return tool_execution_service.execute(uow, payload=payload, user=user)


@router.get("/api/v1/tool-executions/runs")
def list_tool_execution_runs(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str = Query(...),
    action: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    return tool_execution_service.list_runs(
        uow,
        organization_id=organization_id,
        action=action,
        status=status,
        limit=limit,
        user=user,
    )


@router.get("/api/v1/tool-executions/runs/{execution_id}")
def read_tool_execution_run(execution_id: str, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return tool_execution_service.get_run(uow, execution_id=execution_id, user=user)
