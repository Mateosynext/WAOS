from __future__ import annotations

from fastapi import APIRouter, Query

from ...config import settings
from ...application.conversation_service import ConversationService
from ...schemas import ConversationMessageRequest, LeadMemoryUpdateRequest, TakeoverRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["conversations"])
service = ConversationService()


@router.get("/api/v1/conversations")
def list_conversations(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=settings.default_page_size),
    offset: int = Query(default=0),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> list[dict]:
    return service.list(uow, user=user, organization_id=organization_id, bot_id=bot_id, status=status, limit=limit, offset=offset)


@router.get("/api/v1/conversations/{conversation_id}")
def get_conversation(conversation_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.get(uow, user=user, conversation_id=conversation_id)


@router.post("/api/v1/conversations/{conversation_id}/messages")
def send_or_note(conversation_id: str, payload: ConversationMessageRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.add_message_or_note(uow, user=user, conversation_id=conversation_id, payload=payload)


@router.post("/api/v1/conversations/{conversation_id}/takeover")
def takeover(conversation_id: str, payload: TakeoverRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.takeover(uow, user=user, conversation_id=conversation_id, freeze_minutes=payload.freeze_minutes)


@router.post("/api/v1/conversations/{conversation_id}/reactivate-ai")
def reactivate_ai(conversation_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.reactivate_ai(uow, user=user, conversation_id=conversation_id)


@router.get("/api/v1/leads")
def list_leads(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> list[dict]:
    return service.list_leads(uow, user=user, organization_id=organization_id, bot_id=bot_id)


@router.patch("/api/v1/leads/{contact_id}/memory")
def update_lead_memory(contact_id: str, payload: LeadMemoryUpdateRequest, bot_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.update_lead_memory(uow, user=user, contact_id=contact_id, bot_id=bot_id, payload=payload)
