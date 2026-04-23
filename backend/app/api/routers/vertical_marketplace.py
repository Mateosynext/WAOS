from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...application.vertical_marketplace_service import vertical_marketplace_service
from ...schemas import ApiEnvelope, FlexibleSchema, MarketplaceInstallRequest, MarketplacePackagePublishRequest, MarketplaceUpgradeRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["vertical_marketplace"])


@router.post("/api/v1/vertical-marketplace/packages", response_model=ApiEnvelope[FlexibleSchema])
def publish_vertical_marketplace_package(payload: MarketplacePackagePublishRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return vertical_marketplace_service.publish_package(uow, payload=payload, user=user)


@router.get("/api/v1/vertical-marketplace/packages", response_model=ApiEnvelope[FlexibleSchema])
def list_vertical_marketplace_packages(
    vertical_key: str | None = Query(default=None),
    package_type: str | None = Query(default=None),
    status: str | None = Query(default="published"),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict[str, Any]:
    return vertical_marketplace_service.list_packages(uow, vertical_key=vertical_key, package_type=package_type, status=status, limit=limit, user=user)


@router.get("/api/v1/vertical-marketplace/packages/{package_id}", response_model=ApiEnvelope[FlexibleSchema])
def get_vertical_marketplace_package(package_id: str, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return vertical_marketplace_service.get_package(uow, package_id=package_id, user=user)


@router.post("/api/v1/vertical-marketplace/install", response_model=ApiEnvelope[FlexibleSchema])
def install_vertical_marketplace_package(payload: MarketplaceInstallRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return vertical_marketplace_service.install_package(uow, payload=payload, user=user)


@router.get("/api/v1/vertical-marketplace/installs", response_model=ApiEnvelope[FlexibleSchema])
def list_vertical_marketplace_installs(
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
    package_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict[str, Any]:
    return vertical_marketplace_service.list_installs(uow, organization_id=organization_id, bot_id=bot_id, package_id=package_id, limit=limit, user=user)


@router.post("/api/v1/vertical-marketplace/installs/{install_id}/upgrade", response_model=ApiEnvelope[FlexibleSchema])
def upgrade_vertical_marketplace_install(install_id: str, payload: MarketplaceUpgradeRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return vertical_marketplace_service.upgrade_install(uow, install_id=install_id, payload=payload, user=user)
