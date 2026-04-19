from __future__ import annotations

from fastapi import APIRouter, Query

from ...application.onboarding_service import onboarding_service
from ...schemas import (
    GuidedOnboardingWizardStartRequest,
    GuidedOnboardingWizardStepUpdateRequest,
    InboxSavedViewCreateRequest,
    TenantModeUpdateRequest,
)
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["onboarding"])


@router.get("/api/v1/onboarding/summary")
def onboarding_summary(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict:
    return onboarding_service.summary(uow, user=user, organization_id=organization_id, bot_id=bot_id)


@router.post("/api/v1/onboarding/tenant-mode")
def set_tenant_mode(payload: TenantModeUpdateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.set_tenant_mode(uow, payload=payload, user=user)


@router.get("/api/v1/onboarding/wizard/verticals")
def list_guided_verticals(user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return onboarding_service.list_guided_verticals(uow, user=user)


@router.get("/api/v1/onboarding/wizard/blueprint")
def get_guided_wizard_blueprint(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    vertical_id: str | None = Query(default=None),
    subvertical: str | None = Query(default=None),
    primary_objective: str | None = Query(default=None),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict:
    return onboarding_service.wizard_blueprint(
        uow,
        organization_id=organization_id,
        bot_id=bot_id,
        vertical_id=vertical_id,
        subvertical=subvertical,
        primary_objective=primary_objective,
        user=user,
    )


@router.post("/api/v1/onboarding/wizard/start")
def start_guided_wizard(payload: GuidedOnboardingWizardStartRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.start_wizard(uow, payload=payload, user=user)


@router.get("/api/v1/onboarding/wizard/{wizard_id}")
def get_guided_wizard(wizard_id: str, user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return onboarding_service.get_wizard(uow, wizard_id=wizard_id, user=user)


@router.post("/api/v1/onboarding/wizard/{wizard_id}/steps/{step_key}")
def update_guided_wizard_step(wizard_id: str, step_key: str, payload: GuidedOnboardingWizardStepUpdateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.update_wizard_step(uow, wizard_id=wizard_id, step_key=step_key, payload=payload, user=user)


@router.post("/api/v1/onboarding/wizard/{wizard_id}/apply")
def apply_guided_wizard(wizard_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.apply_wizard(uow, wizard_id=wizard_id, user=user)


@router.get("/api/v1/inbox/saved-views")
def list_saved_views(organization_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return onboarding_service.list_saved_views(uow, organization_id=organization_id, user=user)


@router.post("/api/v1/inbox/saved-views")
def create_saved_view(payload: InboxSavedViewCreateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.create_saved_view(uow, payload=payload, user=user)
