from __future__ import annotations

from fastapi import HTTPException

from ...contracts import ok
from ...repositories import get_bot
from ...security import ensure_bot_access, ensure_org_access
from ...vertical_onboarding_runtime import (
    build_guided_onboarding_blueprint,
    list_guided_onboarding_verticals,
    reconcile_guided_onboarding_wizard_integrity,
    refresh_guided_onboarding_validation_snapshot,
)
from ..support import require_permission
from ..uow import UnitOfWork


def list_guided_verticals(service, uow: UnitOfWork, *, user: dict) -> dict:
    memberships = user.get("memberships") or []
    organization_id = memberships[0]["organization_id"] if memberships else None
    if organization_id:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
    items = list_guided_onboarding_verticals()
    return ok({"items": items, "count": len(items)})


def wizard_blueprint(service, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, vertical_id: str | None, subvertical: str | None, primary_objective: str | None, user: dict) -> dict:
    org, bot = service._resolve_scope(uow, user=user, organization_id=organization_id, bot_id=bot_id)
    require_permission(user, org["id"], "operations.read")
    blueprint = build_guided_onboarding_blueprint(
        vertical_id=vertical_id or ((bot or {}).get("vertical")) or org.get("vertical"),
        subvertical=subvertical,
        business_name=((bot or {}).get("business_name")) or org.get("name") or "",
        bot_name=((bot or {}).get("name")) or "",
        tone="",
        language=((bot or {}).get("language")) or "es",
        timezone=((bot or {}).get("timezone")) or org.get("timezone") or "America/Mexico_City",
        primary_objective=primary_objective or "agendar",
        bot_id=(bot or {}).get("id"),
    )
    return ok(blueprint)


def get_wizard(service, uow: UnitOfWork, *, wizard_id: str, user: dict) -> dict:
    wizard = service._get_accessible_wizard(uow.conn, wizard_id=wizard_id, user=user, permission="operations.read")
    diagnostics = (wizard.get("diagnostics") or {}) if isinstance(wizard.get("diagnostics"), dict) else {}
    if diagnostics.get("integrity_mismatch"):
        try:
            if uow.mode == "write":
                wizard = reconcile_guided_onboarding_wizard_integrity(uow.conn, wizard_id=wizard_id, source="get_wizard")
                uow.commit()
            else:
                with UnitOfWork(mode="write") as write_uow:
                    wizard = reconcile_guided_onboarding_wizard_integrity(write_uow.conn, wizard_id=wizard_id, source="get_wizard")
                    write_uow.commit()
        except ValueError:
            pass
    recompute_state = (wizard.get("recompute_state") or {}) if isinstance(wizard.get("recompute_state"), dict) else {}
    should_refresh_snapshot = bool(
        wizard.get("validation_snapshot")
        or wizard.get("applied_at")
        or ((wizard.get("answers") or {}).get("dry_run_validation"))
        or recompute_state.get("validation_snapshot_pending")
        or (wizard.get("bot_id") and wizard.get("status") == "applied")
    )
    if should_refresh_snapshot:
        try:
            if uow.mode == "write":
                wizard = refresh_guided_onboarding_validation_snapshot(uow.conn, wizard_id=wizard_id, source="refresh")
                uow.commit()
            else:
                with UnitOfWork(mode="write") as write_uow:
                    wizard = refresh_guided_onboarding_validation_snapshot(write_uow.conn, wizard_id=wizard_id, source="refresh")
                    write_uow.commit()
        except ValueError:
            pass
    return ok(wizard)


def summary(service, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None) -> dict:
    org, bot = service._resolve_scope(uow, user=user, organization_id=organization_id, bot_id=bot_id)
    require_permission(user, org["id"], "operations.read")
    return ok(service._compute_summary(uow, organization_id=org["id"], bot_id=(bot or {}).get("id")))


def list_saved_views(service, uow: UnitOfWork, *, organization_id: str, user: dict) -> dict:
    ensure_org_access(user, organization_id)
    require_permission(user, organization_id, "conversation.manage")
    return ok(service._load_saved_views(uow.conn, organization_id=organization_id, user_id=user["id"]))
