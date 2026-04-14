from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from ...application.integration_service import integration_service
from ...config import settings
from ...performance import clamp_limit, clamp_offset
from ...schemas import (
    GoogleCalendarConfigRequest,
    WhatsAppIntegrationConfigRequest,
    IntegrationUpsertRequest,
    MetaEmbeddedSignupCompleteRequest,
    RateLimitPolicyRequest,
    SecretCreateRequest,
    StripeIntegrationConfigRequest,
)
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["integrations"])


@router.get("/api/v1/integrations")
def list_integrations(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    limit: int = Query(default=settings.default_page_size),
    offset: int = Query(default=0),
) -> list[dict]:
    return integration_service.list_integrations(uow, organization_id=organization_id, bot_id=bot_id, limit=limit, offset=offset, user=user, clamp_limit=clamp_limit, clamp_offset=clamp_offset)


@router.post("/api/v1/integrations")
def upsert_integration_route(payload: IntegrationUpsertRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.upsert_integration(uow, payload=payload, user=user)


@router.post("/api/v1/integrations/whatsapp/configure")
def configure_whatsapp(payload: WhatsAppIntegrationConfigRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.configure_whatsapp(uow, payload=payload, user=user)


@router.post("/api/v1/integrations/google-calendar/configure")
def configure_google_calendar(payload: GoogleCalendarConfigRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.configure_google_calendar(uow, payload=payload, user=user)


@router.post("/api/v1/integrations/stripe/configure")
def configure_stripe(payload: StripeIntegrationConfigRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.configure_stripe(uow, payload=payload, user=user)


@router.post("/api/v1/integrations/{integration_id}/test")
def test_integration(integration_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.test_integration(uow, integration_id=integration_id, user=user)


@router.get("/api/v1/secrets")
def list_secrets(user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None)) -> list[dict]:
    return integration_service.list_secrets(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.post("/api/v1/secrets")
def create_secret_route(payload: SecretCreateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.create_secret(uow, payload=payload, user=user)


@router.post("/api/v1/secrets/{secret_id}/rotate")
def rotate_secret(secret_id: str, payload: SecretCreateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.rotate_secret(uow, secret_id=secret_id, payload=payload, user=user)


@router.get("/api/v1/rate-limits")
def get_rate_limits(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), bot_id: str | None = Query(default=None)) -> list[dict]:
    return integration_service.get_rate_limits(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.post("/api/v1/rate-limits")
def upsert_rate_limit_route(payload: RateLimitPolicyRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.upsert_rate_limit(uow, payload=payload, user=user)


@router.get("/api/v1/integrations/sync-runs")
def integration_sync_runs(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), integration_id: str | None = Query(default=None)) -> list[dict]:
    return integration_service.integration_sync_runs(uow, organization_id=organization_id, integration_id=integration_id, user=user)


@router.get("/api/v1/integrations/events")
def integration_events(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), integration_id: str | None = Query(default=None)) -> list[dict]:
    return integration_service.integration_events(uow, organization_id=organization_id, integration_id=integration_id, user=user)


@router.get("/api/v1/integrations/observability")
def integration_observability(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), integration_id: str | None = Query(default=None)) -> dict:
    return integration_service.integration_observability(uow, organization_id=organization_id, integration_id=integration_id, user=user)


@router.post("/api/v1/integrations/{integration_id}/sync")
def trigger_integration_sync(integration_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.trigger_integration_sync(uow, integration_id=integration_id, user=user)


@router.get("/api/v1/integrations/{integration_id}/availability")
def integration_availability(integration_id: str, user: CurrentUser, uow: CurrentUoW, time_min: str = Query(...), time_max: str = Query(...)) -> dict:
    return integration_service.integration_availability(uow, integration_id=integration_id, time_min=time_min, time_max=time_max, user=user)


@router.post("/api/v1/integrations/{integration_id}/meta/embedded-signup/start")
def start_meta_signup(integration_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.start_meta_signup(uow, integration_id=integration_id, user=user)


@router.post("/api/v1/integrations/{integration_id}/meta/embedded-signup/complete")
def complete_meta_signup(integration_id: str, payload: MetaEmbeddedSignupCompleteRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.complete_meta_signup(uow, integration_id=integration_id, payload=payload, user=user)


@router.post("/api/v1/integrations/{integration_id}/oauth/google/start")
def start_google_oauth(integration_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return integration_service.start_google_oauth(uow, integration_id=integration_id, user=user)


@router.get("/api/v1/integrations/oauth/google/callback")
def finish_google_oauth(state: str, code: str, uow: CurrentUoW):
    result = integration_service.finish_google_oauth(uow, state=state, code=code)
    target = (result.get("config") or {}).get("frontend_redirect_uri") or f"{settings.public_app_url.rstrip('/')}/integrations?section=configuracion"
    separator = '&' if '?' in target else '?'
    query = urlencode({"google_oauth": "connected", "integration_id": result.get("integration_id") or ""})
    return RedirectResponse(url=f"{target}{separator}{query}", status_code=302)


@router.get("/api/v1/integrations/{integration_id}/oauth/google/calendars")
def google_calendars(integration_id: str, user: CurrentUser, uow: CurrentUoW) -> list[dict]:
    return integration_service.list_google_calendars(uow, integration_id=integration_id, user=user)
