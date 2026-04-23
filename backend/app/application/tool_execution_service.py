from __future__ import annotations

from typing import Any

from .tool_execution_support import ToolExecutionSupportMixin
from .uow import UnitOfWork


class ToolExecutionService(ToolExecutionSupportMixin):
    def preview(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        from .tool_execution_handlers.preview import handle as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def execute(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        from .tool_execution_handlers.execute import handle as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def list_runs(self, uow: UnitOfWork, *, organization_id: str, action: str | None, status: str | None, limit: int, user: dict) -> dict[str, Any]:
        from .tool_execution_handlers.list_runs import handle as _handle
        return _handle(self, uow=uow, organization_id=organization_id, action=action, status=status, limit=limit, user=user)

    def get_run(self, uow: UnitOfWork, *, execution_id: str, user: dict) -> dict[str, Any]:
        from .tool_execution_handlers.get_run import handle as _handle
        return _handle(self, uow=uow, execution_id=execution_id, user=user)


tool_execution_service = ToolExecutionService()
