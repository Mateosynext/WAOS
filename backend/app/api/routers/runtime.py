from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from ...application.runtime_service import runtime_service
from ...schemas import DeadLetterRequeueRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["runtime"])


@router.get("/api/v1/runtime/overview")
def runtime_operations_overview(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
) -> dict[str, Any]:
    return runtime_service.runtime_overview(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.get("/api/v1/bots/{bot_id}/health")
def get_bot_health(bot_id: str, user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...)) -> dict[str, Any]:
    return runtime_service.bot_health(uow, bot_id=bot_id, organization_id=organization_id, user=user)


@router.get("/api/v1/integrations/health")
def get_integrations_health(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), bot_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.integrations_health(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.get("/api/v1/observability/overview")
def observability_overview(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
) -> dict[str, Any]:
    return runtime_service.observability_overview(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.post("/api/v1/observability/frontend-errors")
def frontend_errors(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    return runtime_service.frontend_errors(payload=payload, request=request)


@router.get("/api/v1/runtime/queue")
def runtime_queue(user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.runtime_queue(uow, organization_id=organization_id, user=user)


@router.get("/api/v1/runtime/scheduler")
def runtime_scheduler(user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.runtime_scheduler(uow, organization_id=organization_id, user=user)


@router.get("/api/v1/runtime/callbacks")
def get_runtime_callbacks(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), bot_id: str | None = Query(default=None)) -> list[dict[str, Any]]:
    return runtime_service.runtime_callbacks(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.get("/api/v1/operations/dead-letters")
def list_dead_letters(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), kind: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.list_dead_letters(uow, organization_id=organization_id, kind=kind, user=user)


@router.post("/api/v1/operations/dead-letters/{kind}/{item_id}/requeue")
def requeue_dead_letter(kind: str, item_id: str, payload: DeadLetterRequeueRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return runtime_service.requeue_dead_letter(uow, kind=kind, item_id=item_id, payload=payload, user=user)
