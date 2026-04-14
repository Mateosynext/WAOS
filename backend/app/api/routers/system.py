from __future__ import annotations

from fastapi import APIRouter

from ...application.system_service import system_service
from ...schemas import SettingsUpdateRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["system"])


@router.get("/healthz")
def healthz(uow: CurrentUoW) -> dict:
    return system_service.healthz(uow)


@router.get("/readyz")
def readyz(uow: CurrentUoW):
    return system_service.readyz(uow)


@router.get("/api/v1/system/status")
def system_status(uow: CurrentUoW) -> dict:
    return system_service.system_status_payload(uow)


@router.get("/api/v1/settings/global")
def get_global_settings(user: CurrentUser) -> dict:
    return system_service.get_global_settings(user=user)


@router.post("/api/v1/settings/global")
def update_global_settings(payload: SettingsUpdateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return system_service.update_global_settings(uow, payload=payload, user=user)
