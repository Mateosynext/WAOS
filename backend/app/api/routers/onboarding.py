from __future__ import annotations

from fastapi import APIRouter, Query

from ...application.onboarding_service import onboarding_service
from ...schemas import (
    ApiEnvelope,
    GuidedOnboardingAiAutofixRequest,
    GuidedOnboardingAiAutopilotRequest,
    GuidedOnboardingAiPrefillRequest,
    GuidedOnboardingWizardStartRequest,
    GuidedOnboardingWizardStepUpdateRequest,
    InboxSavedViewCreateRequest,
    OnboardingPayloadResponse,
    OnboardingSummaryData,
    TenantModeUpdateRequest,
)
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter()
onboarding_router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])
inbox_router = APIRouter(prefix="/api/v1/inbox", tags=["onboarding"])


@onboarding_router.get("/summary", response_model=ApiEnvelope[OnboardingSummaryData])
def onboarding_summary(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict:
    return onboarding_service.summary(uow, user=user, organization_id=organization_id, bot_id=bot_id)


@onboarding_router.post("/tenant-mode", response_model=ApiEnvelope[OnboardingPayloadResponse])
def set_tenant_mode(payload: TenantModeUpdateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.set_tenant_mode(uow, payload=payload, user=user)


@onboarding_router.get("/wizard/verticals", response_model=ApiEnvelope[OnboardingPayloadResponse])
def list_guided_verticals(user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return onboarding_service.list_guided_verticals(uow, user=user)


@onboarding_router.get("/wizard/blueprint", response_model=ApiEnvelope[OnboardingPayloadResponse])
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


@onboarding_router.post("/wizard/ai-prefill", response_model=ApiEnvelope[OnboardingPayloadResponse])
def generate_guided_wizard_ai_prefill(payload: GuidedOnboardingAiPrefillRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.ai_prefill_wizard(uow, payload=payload, user=user)


@onboarding_router.post("/wizard/ai-autopilot", response_model=ApiEnvelope[OnboardingPayloadResponse])
def run_guided_wizard_ai_autopilot(payload: GuidedOnboardingAiAutopilotRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.ai_autopilot_wizard(uow, payload=payload, user=user)


@onboarding_router.post("/wizard/start", response_model=ApiEnvelope[OnboardingPayloadResponse])
def start_guided_wizard(payload: GuidedOnboardingWizardStartRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.start_wizard(uow, payload=payload, user=user)


@onboarding_router.get("/wizard/{wizard_id}", response_model=ApiEnvelope[OnboardingPayloadResponse])
def get_guided_wizard(wizard_id: str, user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return onboarding_service.get_wizard(uow, wizard_id=wizard_id, user=user)


@onboarding_router.post("/wizard/{wizard_id}/steps/{step_key}", response_model=ApiEnvelope[OnboardingPayloadResponse])
def update_guided_wizard_step(wizard_id: str, step_key: str, payload: GuidedOnboardingWizardStepUpdateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.update_wizard_step(uow, wizard_id=wizard_id, step_key=step_key, payload=payload, user=user)


@onboarding_router.post("/wizard/{wizard_id}/dry-run", response_model=ApiEnvelope[OnboardingPayloadResponse])
def dry_run_guided_wizard(wizard_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.dry_run_wizard(uow, wizard_id=wizard_id, user=user)


@onboarding_router.post("/wizard/{wizard_id}/ai-autofix", response_model=ApiEnvelope[OnboardingPayloadResponse])
def autofix_guided_wizard_with_ai(wizard_id: str, payload: GuidedOnboardingAiAutofixRequest | None = None, user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return onboarding_service.ai_autofix_wizard(uow, wizard_id=wizard_id, payload=payload or GuidedOnboardingAiAutofixRequest(), user=user)


@onboarding_router.post("/wizard/{wizard_id}/apply", response_model=ApiEnvelope[OnboardingPayloadResponse])
def apply_guided_wizard(wizard_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.apply_wizard(uow, wizard_id=wizard_id, user=user)


@inbox_router.get("/saved-views", response_model=ApiEnvelope[OnboardingPayloadResponse])
def list_saved_views(organization_id: str = Query(...), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return onboarding_service.list_saved_views(uow, organization_id=organization_id, user=user)


@inbox_router.post("/saved-views", response_model=ApiEnvelope[OnboardingPayloadResponse])
def create_saved_view(payload: InboxSavedViewCreateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return onboarding_service.create_saved_view(uow, payload=payload, user=user)


router.include_router(onboarding_router)
router.include_router(inbox_router)
