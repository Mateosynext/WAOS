from __future__ import annotations

from fastapi import APIRouter, Query

from ...config import settings
from ...application.bot_service import BotService
from ...schemas import BotCreateRequest, BotUpdateRequest, CloneBotRequest, PublishRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["bots"])
service = BotService()


@router.get("/api/v1/bots")
def list_bots(
    organization_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=settings.default_page_size),
    offset: int = Query(default=0),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> list[dict]:
    return service.list(uow, user=user, organization_id=organization_id, status=status, limit=limit, offset=offset)


@router.post("/api/v1/bots")
def create_bot(payload: BotCreateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.create(uow, user=user, payload=payload)


@router.get("/api/v1/bots/{bot_id}")
def get_bot(bot_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.get(uow, user=user, bot_id=bot_id)


@router.patch("/api/v1/bots/{bot_id}")
def update_bot(bot_id: str, payload: BotUpdateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.update(uow, user=user, bot_id=bot_id, payload=payload)


@router.post("/api/v1/bots/{bot_id}/publish")
def publish_bot(bot_id: str, payload: PublishRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.publish(uow, user=user, bot_id=bot_id, payload=payload)


@router.get("/api/v1/bots/{bot_id}/versions")
def get_versions(bot_id: str, user: CurrentUser, uow: CurrentUoW) -> list[dict]:
    return service.versions(uow, user=user, bot_id=bot_id)


@router.post("/api/v1/bots/{bot_id}/rollback/{version_id}")
def rollback_bot(bot_id: str, version_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.rollback(uow, user=user, bot_id=bot_id, version_id=version_id)


@router.post("/api/v1/bots/{bot_id}/pause")
def pause_bot(bot_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.pause(uow, user=user, bot_id=bot_id)


@router.post("/api/v1/bots/{bot_id}/resume")
def resume_bot(bot_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.resume(uow, user=user, bot_id=bot_id)


@router.post("/api/v1/bots/{bot_id}/clone")
def clone_bot(bot_id: str, payload: CloneBotRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.clone(uow, user=user, bot_id=bot_id, payload=payload)


@router.delete("/api/v1/bots/{bot_id}")
def delete_bot(bot_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.delete(uow, user=user, bot_id=bot_id)
