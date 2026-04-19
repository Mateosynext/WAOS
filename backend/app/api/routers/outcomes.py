from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...application.outcomes_service import outcomes_service
from ...schemas import (
    OutcomeDecisionApplyRequest,
    OutcomeDecisionRollbackRequest,
    OutcomeEventRequest,
    OutcomeExposureRequest,
    OutcomeOperatorSignalRequest,
    OutcomeRecomputeRequest,
)
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["outcomes"])


@router.post("/api/v1/outcomes/exposures")
def record_outcome_exposure_route(payload: OutcomeExposureRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return outcomes_service.record_exposure(uow, payload=payload, user=user)


@router.post("/api/v1/outcomes/events")
def record_outcome_event_route(payload: OutcomeEventRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return outcomes_service.record_event(uow, payload=payload, user=user)


@router.post("/api/v1/outcomes/operator-signals")
def record_operator_signal_route(payload: OutcomeOperatorSignalRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return outcomes_service.record_operator_signal(uow, payload=payload, user=user)


@router.get("/api/v1/outcomes/scorecards")
def list_outcome_scorecards_route(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    scorecard_window: str = Query(default="28d"),
) -> dict[str, Any]:
    return outcomes_service.scorecards(
        uow,
        organization_id=organization_id,
        bot_id=bot_id,
        entity_type=entity_type,
        entity_id=entity_id,
        scorecard_window=scorecard_window,
        user=user,
    )


@router.get("/api/v1/outcomes/entities/{entity_type}/{entity_id}")
def outcome_entity_detail_route(entity_type: str, entity_id: str, user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...)) -> dict[str, Any]:
    return outcomes_service.entity_detail(uow, organization_id=organization_id, entity_type=entity_type, entity_id=entity_id, user=user)


@router.get("/api/v1/outcomes/decisions")
def list_outcome_decisions_route(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str = Query(...),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    return outcomes_service.list_decisions(uow, organization_id=organization_id, entity_type=entity_type, entity_id=entity_id, status=status, user=user)


@router.get("/api/v1/outcomes/attribution")
def list_outcome_attribution_route(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    outcome_event_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    return outcomes_service.attribution(
        uow,
        organization_id=organization_id,
        bot_id=bot_id,
        entity_type=entity_type,
        entity_id=entity_id,
        outcome_event_id=outcome_event_id,
        limit=limit,
        user=user,
    )


@router.post("/api/v1/outcomes/recompute")
def recompute_outcomes_route(payload: OutcomeRecomputeRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return outcomes_service.recompute(uow, payload=payload, user=user)


@router.post("/api/v1/outcomes/decisions/apply")
def apply_outcome_decision_route(payload: OutcomeDecisionApplyRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return outcomes_service.apply_decision(uow, payload=payload, user=user)


@router.post("/api/v1/outcomes/decisions/{decision_id}/rollback")
def rollback_outcome_decision_route(decision_id: str, payload: OutcomeDecisionRollbackRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return outcomes_service.rollback_decision(uow, decision_id=decision_id, payload=payload, user=user)
