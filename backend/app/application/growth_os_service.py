from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ..contracts import ok
from ..utils import from_json
from ..growth_os_runtime import growth_os_overview, list_growth_os_runs, run_growth_os_cycle
from ..repositories import get_bot
from ..security import ensure_bot_access, ensure_org_access
from .support import require_permission
from .uow import UnitOfWork


class GrowthOsService:
    def overview(self, uow: UnitOfWork, *, organization_id: str, bot_id: str, scorecard_window: str, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        bot = get_bot(uow.conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if bot["organization_id"] != organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)
        bot_config = from_json(bot.get("config_draft_json"), {})
        return ok(growth_os_overview(uow.conn, organization_id=organization_id, bot_id=bot_id, scorecard_window=scorecard_window, bot_config=bot_config))

    def run(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "conversation.manage")
        bot = get_bot(uow.conn, payload.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if bot["organization_id"] != payload.organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)
        result = run_growth_os_cycle(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            goals=payload.goals,
            mode=payload.mode,
            limit=payload.limit,
            max_targets=payload.max_targets,
            auto_execute=payload.auto_execute,
            include_suppressed=payload.include_suppressed,
            scorecard_window=payload.scorecard_window,
            metadata=payload.metadata,
        )
        uow.commit()
        return ok(result)

    def list_runs(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, limit: int, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        items = list_growth_os_runs(uow.conn, organization_id=organization_id, bot_id=bot_id, limit=limit)
        return ok({"items": items, "count": len(items)})


growth_os_service = GrowthOsService()
