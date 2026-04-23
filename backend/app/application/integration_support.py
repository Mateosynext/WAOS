from __future__ import annotations

from fastapi import HTTPException

from ..db import fetch_one
from ..repositories import get_bot
from ..security import ensure_bot_access, ensure_org_access
from .support import require_permission
from .uow import UnitOfWork


class IntegrationSupportMixin:
    def _get_integration(self, uow: UnitOfWork, integration_id: str) -> dict:
        row = fetch_one(uow.conn, "SELECT * FROM integration_connections WHERE id = ?", (integration_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Integration not found")
        return row

    def _ensure_integration_access(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> None:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "integration.manage")
        if bot_id:
            bot = get_bot(uow.conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            if bot["organization_id"] != organization_id:
                raise HTTPException(status_code=403, detail="Bot does not belong to organization")
            ensure_bot_access(user, bot)
