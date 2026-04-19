from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ..contracts import ok
from ..repositories import get_bot
from ..security import ensure_bot_access, ensure_org_access
from ..vertical_marketplace_runtime import (
    get_marketplace_package,
    install_marketplace_package,
    list_marketplace_installs,
    list_marketplace_packages,
    publish_marketplace_package,
    upgrade_marketplace_install,
)
from .support import require_permission
from .uow import UnitOfWork


class VerticalMarketplaceService:
    def publish_package(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        org_id = None
        memberships = user.get("memberships") or []
        if memberships:
            org_id = memberships[0].get("organization_id")
            ensure_org_access(user, org_id)
            require_permission(user, org_id, "activation.manage")
        package = publish_marketplace_package(
            uow.conn,
            package_type=payload.package_type,
            package_slug=payload.package_slug or payload.title,
            title=payload.title,
            summary=payload.summary,
            version=payload.version,
            manifest=payload.manifest,
            vertical_key=payload.vertical_key,
            subvertical=payload.subvertical,
            compatibility=payload.compatibility,
            dependencies=payload.dependencies,
            checklist=payload.checklist,
            metrics_expected=payload.metrics_expected,
            monetization_model=payload.monetization_model,
            price_amount=payload.price_amount,
            currency=payload.currency,
            publisher_user_id=user.get("id"),
            publisher_org_id=org_id,
            release_notes=payload.release_notes,
            metadata=payload.metadata,
            status=payload.status,
        )
        uow.commit()
        return ok(package)

    def list_packages(self, uow: UnitOfWork, *, vertical_key: str | None, package_type: str | None, status: str | None, limit: int, user: dict) -> dict[str, Any]:
        memberships = user.get("memberships") or []
        if memberships:
            ensure_org_access(user, memberships[0].get("organization_id"))
        items = list_marketplace_packages(uow.conn, vertical_key=vertical_key, package_type=package_type, status=status, limit=limit)
        return ok({"items": items, "count": len(items)})

    def get_package(self, uow: UnitOfWork, *, package_id: str, user: dict) -> dict[str, Any]:
        memberships = user.get("memberships") or []
        if memberships:
            ensure_org_access(user, memberships[0].get("organization_id"))
        package = get_marketplace_package(uow.conn, package_id)
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        return ok(package)

    def install_package(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "activation.manage")
        bot = None
        if payload.bot_id:
            bot = get_bot(uow.conn, payload.bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            if bot["organization_id"] != payload.organization_id:
                raise HTTPException(status_code=403, detail="Bot does not belong to organization")
            ensure_bot_access(user, bot)
        try:
            install = install_marketplace_package(
                uow.conn,
                organization_id=payload.organization_id,
                bot_id=payload.bot_id,
                actor_user=user,
                package_id=payload.package_id,
                package_slug=payload.package_slug,
                version=payload.version,
                install_scope=payload.install_scope,
                metadata=payload.metadata,
            )
        except ValueError as exc:
            detail = str(exc)
            if detail == "package_not_found":
                raise HTTPException(status_code=404, detail="Package not found")
            if detail == "package_version_not_found":
                raise HTTPException(status_code=404, detail="Package version not found")
            raise HTTPException(status_code=400, detail=detail)
        uow.commit()
        return ok(install)

    def list_installs(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, package_id: str | None, limit: int, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        if bot_id:
            bot = get_bot(uow.conn, bot_id)
            if bot:
                ensure_bot_access(user, bot)
        items = list_marketplace_installs(uow.conn, organization_id=organization_id, bot_id=bot_id, package_id=package_id, limit=limit)
        return ok({"items": items, "count": len(items)})

    def upgrade_install(self, uow: UnitOfWork, *, install_id: str, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "activation.manage")
        try:
            upgraded = upgrade_marketplace_install(uow.conn, install_id=install_id, actor_user=user, target_version=payload.target_version, metadata=payload.metadata)
        except ValueError as exc:
            detail = str(exc)
            if detail in {"install_not_found", "package_not_found"}:
                raise HTTPException(status_code=404, detail=detail.replace("_", " "))
            if detail == "no_upgrade_available":
                raise HTTPException(status_code=400, detail="No upgrade available")
            if detail == "package_version_not_found":
                raise HTTPException(status_code=404, detail="Package version not found")
            raise HTTPException(status_code=400, detail=detail)
        uow.commit()
        return ok(upgraded)


vertical_marketplace_service = VerticalMarketplaceService()
