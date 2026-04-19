from __future__ import annotations

from fastapi import APIRouter

from ...application.system_service import system_service
from ...schemas import SettingsUpdateRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["system"])


@router.get("/livez")
def livez() -> dict:
    return system_service.livez()


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


@router.get("/api/v1/runtime/health-panel")
def runtime_health_panel(uow: CurrentUoW) -> dict:
    return system_service.runtime_health_panel(uow)


@router.get("/api/v1/system/deploy-checklist")
def deploy_checklist(uow: CurrentUoW) -> dict:
    return system_service.deploy_checklist(uow)


@router.get("/api/v1/system/whatsapp-governance")
def whatsapp_governance_panel(user: CurrentUser, uow: CurrentUoW, bot_id: str | None = None) -> dict:
    return system_service.whatsapp_governance_panel(uow, user=user, bot_id=bot_id)
