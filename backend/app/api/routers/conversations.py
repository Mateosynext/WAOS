from __future__ import annotations

from fastapi import APIRouter, Query

from ...application.conversation_service import ConversationService
from ...config import settings
from ...schemas import (
    ApiEnvelope,
    ConversationAssignRequest,
    ConversationAutoAssignData,
    ConversationDecisionSupportData,
    ConversationDetailResponse,
    ConversationListItemResponse,
    ConversationMessageMutationResponse,
    ConversationMessageRequest,
    ConversationReactivationData,
    ConversationWorkQueuesData,
    ConversationOwnershipData,
    FlexibleSchema,
    InboxAutoAssignRequest,
    LeadMemoryResponse,
    LeadMemoryUpdateRequest,
    StructuredInternalNoteRequest,
    TakeoverRequest,
)
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter()
conversations_router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])
inbox_router = APIRouter(prefix="/api/v1/inbox", tags=["conversations"])
leads_router = APIRouter(prefix="/api/v1/leads", tags=["conversations"])
supervisor_router = APIRouter(prefix="/api/v1/supervisor", tags=["conversations"])
qa_router = APIRouter(prefix="/api/v1/qa", tags=["conversations"])
service = ConversationService()


@conversations_router.get("", response_model=list[ConversationListItemResponse])
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


@conversations_router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(conversation_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.get(uow, user=user, conversation_id=conversation_id)


@conversations_router.get("/{conversation_id}/decision-support", response_model=ApiEnvelope[ConversationDecisionSupportData])
def get_conversation_decision_support(conversation_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.decision_support(uow, user=user, conversation_id=conversation_id)


@inbox_router.get("/queues", response_model=ApiEnvelope[ConversationWorkQueuesData])
def inbox_work_queues(organization_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.list_work_queues(uow, user=user, organization_id=organization_id)


@inbox_router.get("/ownership", response_model=ApiEnvelope[ConversationOwnershipData])
def inbox_ownership(organization_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.ownership_summary(uow, user=user, organization_id=organization_id)


@inbox_router.post("/auto-assign", response_model=ApiEnvelope[ConversationAutoAssignData])
def inbox_auto_assign(payload: InboxAutoAssignRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.auto_assign(uow, user=user, payload=payload)


@conversations_router.post("/{conversation_id}/assign", response_model=FlexibleSchema)
def assign_conversation(conversation_id: str, payload: ConversationAssignRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.assign(uow, user=user, conversation_id=conversation_id, payload=payload)


@conversations_router.post("/{conversation_id}/messages", response_model=ConversationMessageMutationResponse)
def send_or_note(conversation_id: str, payload: ConversationMessageRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.add_message_or_note(uow, user=user, conversation_id=conversation_id, payload=payload)


@conversations_router.post("/{conversation_id}/takeover", response_model=FlexibleSchema)
def takeover(conversation_id: str, payload: TakeoverRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.takeover(uow, user=user, conversation_id=conversation_id, freeze_minutes=payload.freeze_minutes)


@conversations_router.post("/{conversation_id}/reactivate-ai", response_model=ApiEnvelope[ConversationReactivationData])
def reactivate_ai(conversation_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.reactivate_ai(uow, user=user, conversation_id=conversation_id)


@leads_router.get("", response_model=list[LeadMemoryResponse])
def list_leads(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> list[dict]:
    return service.list_leads(uow, user=user, organization_id=organization_id, bot_id=bot_id)


@leads_router.patch("/{contact_id}/memory", response_model=LeadMemoryResponse)
def update_lead_memory(contact_id: str, payload: LeadMemoryUpdateRequest, bot_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.update_lead_memory(uow, user=user, contact_id=contact_id, bot_id=bot_id, payload=payload)


@conversations_router.post("/{conversation_id}/internal-notes/structured", response_model=ApiEnvelope[FlexibleSchema])
def add_structured_internal_note(conversation_id: str, payload: StructuredInternalNoteRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.add_structured_internal_note(uow, user=user, conversation_id=conversation_id, payload=payload)


@conversations_router.get("/{conversation_id}/takeover-brief", response_model=ApiEnvelope[FlexibleSchema])
def get_takeover_brief(conversation_id: str, brief_type: str = Query(default="takeover"), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.takeover_brief(uow, user=user, conversation_id=conversation_id, brief_type=brief_type)


@supervisor_router.get("/console", response_model=ApiEnvelope[FlexibleSchema])
def supervisor_console(organization_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.supervisor_console(uow, user=user, organization_id=organization_id)


@qa_router.get("/overview", response_model=ApiEnvelope[FlexibleSchema])
def qa_overview(organization_id: str = Query(...), bot_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.qa_overview(uow, user=user, organization_id=organization_id, bot_id=bot_id)


router.include_router(conversations_router)
router.include_router(inbox_router)
router.include_router(leads_router)
router.include_router(supervisor_router)
router.include_router(qa_router)
