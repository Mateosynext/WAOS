from __future__ import annotations

from fastapi import APIRouter, Query

from ...config import settings
from ...application.conversation_service import ConversationService
from ...schemas import ConversationMessageRequest, LeadMemoryUpdateRequest, TakeoverRequest, ConversationAssignRequest, InboxAutoAssignRequest, StructuredInternalNoteRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["conversations"])
service = ConversationService()


@router.get("/api/v1/conversations")
def list_conversations(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    limit: int = Query(default=settings.default_page_size),
    offset: int = Query(default=0),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> list[dict]:
    return service.list(uow, user=user, organization_id=organization_id, bot_id=bot_id, status=status, sort=sort, limit=limit, offset=offset)


@router.get("/api/v1/conversations/{conversation_id}")
def get_conversation(conversation_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.get(uow, user=user, conversation_id=conversation_id)


@router.get("/api/v1/conversations/{conversation_id}/decision-support")
def get_conversation_decision_support(conversation_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.decision_support(uow, user=user, conversation_id=conversation_id)


@router.get("/api/v1/inbox/queues")
def inbox_work_queues(organization_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.list_work_queues(uow, user=user, organization_id=organization_id)


@router.get("/api/v1/inbox/ownership")
def inbox_ownership(organization_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.ownership_summary(uow, user=user, organization_id=organization_id)


@router.post("/api/v1/inbox/auto-assign")
def inbox_auto_assign(payload: InboxAutoAssignRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.auto_assign(uow, user=user, payload=payload)


@router.post("/api/v1/conversations/{conversation_id}/assign")
def assign_conversation(conversation_id: str, payload: ConversationAssignRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.assign(uow, user=user, conversation_id=conversation_id, payload=payload)


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


@router.post("/api/v1/conversations/{conversation_id}/internal-notes/structured")
def add_structured_internal_note(conversation_id: str, payload: StructuredInternalNoteRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.add_structured_internal_note(uow, user=user, conversation_id=conversation_id, payload=payload)


@router.get("/api/v1/conversations/{conversation_id}/takeover-brief")
def get_takeover_brief(conversation_id: str, brief_type: str = Query(default="takeover"), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.takeover_brief(uow, user=user, conversation_id=conversation_id, brief_type=brief_type)


@router.get("/api/v1/supervisor/console")
def supervisor_console(organization_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.supervisor_console(uow, user=user, organization_id=organization_id)


@router.get("/api/v1/qa/overview")
def qa_overview(organization_id: str = Query(...), bot_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.qa_overview(uow, user=user, organization_id=organization_id, bot_id=bot_id)
