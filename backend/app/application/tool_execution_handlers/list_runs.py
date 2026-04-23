from __future__ import annotations

import hashlib
from typing import Any

from fastapi import HTTPException

from ...agent_policy_runtime import evaluate_specialist_policy, get_policy_profile_for_specialist, persist_agent_policy_evaluation
from ...contracts import ok
from ...db import execute, fetch_all, fetch_one
from ...job_idempotency import begin_job_execution, get_job_execution, mark_job_completed, mark_job_failed
from ...multi_agent_runtime import build_shared_memory_context
from ...repositories import create_audit_log, get_bot
from ...security import ensure_bot_access, ensure_org_access
from ...utils import from_json, hash_value, new_id, to_json, utcnow_iso
from ..support import require_permission
from ..uow import UnitOfWork


from ..tool_execution_adapters import (
    ActionPolicy,
    BaseAdapter,
    GoogleCalendarAdapter,
    StripePaymentsAdapter,
    WaosCalendarAdapter,
    WaosCrmAdapter,
)
from ..tool_execution_policy import resolve_action_policy
from ..tool_execution_presenters import serialize_tool_execution_run



def handle(service, uow: UnitOfWork, *, organization_id: str, action: str | None, status: str | None, limit: int, user: dict) -> dict[str, Any]:
    ensure_org_access(user, organization_id)
    require_permission(user, organization_id, "operations.read")
    where = ["organization_id = ?"]
    params: list[Any] = [organization_id]
    if action:
        where.append("action = ?")
        params.append(action)
    if status:
        where.append("status = ?")
        params.append(status)
    rows = fetch_all(
        uow.conn,
        f"SELECT * FROM tool_execution_runs WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT ?",
        tuple([*params, limit]),
    )
    return ok({"items": [service._serialize_run(uow.conn, row) for row in rows], "count": len(rows)})
