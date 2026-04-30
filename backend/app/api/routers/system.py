from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...application.system_service import system_service
from ...schemas import FlexibleSchema, SettingsUpdateRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["system"])


def _require_super_admin(user: dict) -> None:
    if str(user.get("global_role") or "").strip() != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admin can access system runtime endpoints")



@router.get("/livez", response_model=FlexibleSchema)
def livez() -> dict:
    return system_service.livez()


@router.get("/healthz", response_model=FlexibleSchema)
def healthz(uow: CurrentUoW) -> dict:
    return system_service.healthz(uow)


@router.get("/readyz", response_model=FlexibleSchema)
def readyz(uow: CurrentUoW):
    return system_service.readyz(uow)


@router.get("/ops/health", response_model=FlexibleSchema)
def ops_health(user: CurrentUser, uow: CurrentUoW) -> dict:
    _require_super_admin(user)
    return system_service.runtime_health_panel(uow)


@router.get("/api/v1/system/status", response_model=FlexibleSchema)
def system_status(user: CurrentUser, uow: CurrentUoW) -> dict:
    _require_super_admin(user)
    return system_service.system_status_payload(uow)


@router.get("/api/v1/settings/global", response_model=FlexibleSchema)
def get_global_settings(user: CurrentUser) -> dict:
    return system_service.get_global_settings(user=user)


@router.post("/api/v1/settings/global", response_model=FlexibleSchema)
def update_global_settings(payload: SettingsUpdateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return system_service.update_global_settings(uow, payload=payload, user=user)


@router.get("/api/v1/runtime/health-panel", response_model=FlexibleSchema)
def runtime_health_panel(user: CurrentUser, uow: CurrentUoW) -> dict:
    _require_super_admin(user)
    return system_service.runtime_health_panel(uow)


@router.get("/api/v1/system/deploy-checklist", response_model=FlexibleSchema)
def deploy_checklist(user: CurrentUser, uow: CurrentUoW) -> dict:
    _require_super_admin(user)
    return system_service.deploy_checklist(uow)


@router.get("/api/v1/system/whatsapp-governance", response_model=FlexibleSchema)
def whatsapp_governance_panel(user: CurrentUser, uow: CurrentUoW, bot_id: str | None = None) -> dict:
    _require_super_admin(user)
    return system_service.whatsapp_governance_panel(uow, user=user, bot_id=bot_id)
