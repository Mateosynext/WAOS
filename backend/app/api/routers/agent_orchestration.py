from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...application.agent_orchestration_service import agent_orchestration_service
from ...schemas import AgentRouteRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["agent_orchestration"])


@router.get("/api/v1/agent-orchestration/specialists")
def list_specialists(organization_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict[str, Any]:
    return agent_orchestration_service.list_specialists(uow, organization_id=organization_id, user=user)


@router.post("/api/v1/agent-orchestration/route")
def route_intent(payload: AgentRouteRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return agent_orchestration_service.route_preview(uow, payload=payload, user=user)


@router.get("/api/v1/agent-orchestration/conversations/{conversation_id}")
def agent_orchestration_conversation(conversation_id: str, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return agent_orchestration_service.conversation_overview(uow, conversation_id=conversation_id, user=user)
