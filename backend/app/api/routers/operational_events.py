from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...contracts import ok
from ...operational_events import list_operational_events
from ...security import ensure_org_access
from ..dependencies import CurrentUoW, CurrentUser
from ..handlers.common import _require_permission

router = APIRouter(tags=["operational_events"])


@router.get("/api/v1/operational-events")
def get_operational_events(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str = Query(...),
    correlation_id: str | None = None,
    job_id: str | None = None,
    message_id: str | None = None,
    outbox_message_id: str | None = None,
    tool_execution_id: str | None = None,
    payment_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    ensure_org_access(user, organization_id)
    _require_permission(user, organization_id, "logs.read")
    return ok({
        "events": list_operational_events(
            uow.conn,
            organization_id=organization_id,
            correlation_id=correlation_id,
            job_id=job_id,
            message_id=message_id,
            outbox_message_id=outbox_message_id,
            tool_execution_id=tool_execution_id,
            payment_id=payment_id,
            limit=limit,
        )
    })
