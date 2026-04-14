from __future__ import annotations

from fastapi import APIRouter, Query

from ...config import settings
from ...application.organization_service import OrganizationService
from ...schemas import OrganizationCreateRequest, OrganizationUpdateRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])
service = OrganizationService()


@router.get("")
def list_organizations(
    organization_id: str | None = Query(default=None),
    limit: int = Query(default=settings.default_page_size),
    offset: int = Query(default=0),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> list[dict]:
    return service.list(uow, user=user, organization_id=organization_id, limit=limit, offset=offset)


@router.post("")
def create_organization(payload: OrganizationCreateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.create(uow, user=user, payload=payload)


@router.patch("/{organization_id}")
def update_organization(organization_id: str, payload: OrganizationUpdateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.update(uow, user=user, organization_id=organization_id, payload=payload)
