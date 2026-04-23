from __future__ import annotations

from fastapi import APIRouter, Query

from ...application.organization_service import OrganizationService
from ...config import settings
from ...schemas import OrganizationCreateRequest, OrganizationResponse, OrganizationUpdateRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])
service = OrganizationService()


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(
    organization_id: str | None = Query(default=None),
    limit: int = Query(default=settings.default_page_size),
    offset: int = Query(default=0),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> list[dict]:
    return service.list(uow, user=user, organization_id=organization_id, limit=limit, offset=offset)


@router.post("", response_model=OrganizationResponse)
def create_organization(payload: OrganizationCreateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.create(uow, user=user, payload=payload)


@router.patch("/{organization_id}", response_model=OrganizationResponse)
def update_organization(organization_id: str, payload: OrganizationUpdateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.update(uow, user=user, organization_id=organization_id, payload=payload)
