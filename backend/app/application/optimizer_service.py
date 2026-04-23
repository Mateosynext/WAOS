from __future__ import annotations

from typing import Any

from .optimizer_support import OptimizerSupportMixin
from .uow import UnitOfWork


class OptimizerApplicationService(OptimizerSupportMixin):
    def overview(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> dict[str, Any]:
        from .optimizer_handlers.queries import overview as _handle
        return _handle(self, uow=uow, organization_id=organization_id, bot_id=bot_id, user=user)

    def list_proposals(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, status: str | None, user: dict) -> dict[str, Any]:
        from .optimizer_handlers.queries import list_proposals as _handle
        return _handle(self, uow=uow, organization_id=organization_id, bot_id=bot_id, status=status, user=user)

    def run_cycle(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        from .optimizer_handlers.commands import run_cycle as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def evaluate_experiments(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        from .optimizer_handlers.commands import evaluate_experiments as _handle
        return _handle(self, uow=uow, payload=payload, user=user)


optimizer_service = OptimizerApplicationService()
