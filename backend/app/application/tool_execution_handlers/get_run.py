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



def handle(service, uow: UnitOfWork, *, execution_id: str, user: dict) -> dict[str, Any]:
    row = fetch_one(uow.conn, "SELECT * FROM tool_execution_runs WHERE id = ?", (execution_id,))
    if not row:
        raise HTTPException(status_code=404, detail="tool_execution_run_not_found")
    ensure_org_access(user, row["organization_id"])
    require_permission(user, row["organization_id"], "operations.read")
    return ok(service._serialize_run(uow.conn, row))
