from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...application.agent_policy_service import agent_policy_service
from ...schemas import AgentPolicyEvaluationRequest, ApiEnvelope, FlexibleSchema
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["agent_policy"])


@router.get("/api/v1/agent-policy/profiles", response_model=ApiEnvelope[FlexibleSchema])
def list_policy_profiles(organization_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict[str, Any]:
    return agent_policy_service.list_profiles(uow, organization_id=organization_id, user=user)


@router.post("/api/v1/agent-policy/evaluate", response_model=ApiEnvelope[FlexibleSchema])
def evaluate_policy(payload: AgentPolicyEvaluationRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return agent_policy_service.evaluate(uow, payload=payload, user=user)
