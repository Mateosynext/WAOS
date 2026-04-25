from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

from ..security import ensure_org_access
from .persistence import get_run, require_run

TERMINAL_STATUSES = {"completed", "completed_partial", "failed", "cancelled", "paused_cost_limit"}
SAFE_CONFIRMATION_STATUSES = {"confirmed", "not_applicable", "escalate_to_human", "blocked_response", "range_confirmed", "deferred_safe"}
RUN_ID_RE = re.compile(r"^[A-Za-z0-9:_-]{8,160}$")


def validate_run_id(run_id: str) -> str:
    value = str(run_id or "").strip()
    if not value or not RUN_ID_RE.match(value):
        raise HTTPException(status_code=422, detail={"code": "invalid_run_id", "message": "Invalid workflow run id"})
    return value


def require_authorized_run(conn, run_id: str, user: dict) -> dict[str, Any]:
    run_id = validate_run_id(run_id)
    try:
        run = require_run(conn, run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"code": "workflow_not_found", "message": "Workflow run not found"})
    ensure_org_access(user, str(run.get("organization_id") or ""))
    return run


def get_authorized_run(conn, run_id: str, user: dict) -> dict[str, Any] | None:
    run_id = validate_run_id(run_id)
    run = get_run(conn, run_id)
    if not run:
        return None
    ensure_org_access(user, str(run.get("organization_id") or ""))
    return run


def require_not_terminal(run: dict[str, Any], *, action: str) -> None:
    if run.get("status") in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={"code": "workflow_terminal", "message": f"Cannot {action}; workflow is already {run.get('status')}"},
        )


def require_finished_before_launch(run: dict[str, Any]) -> None:
    status = run.get("status")
    if status not in {"completed", "completed_partial"}:
        raise HTTPException(
            status_code=409,
            detail={"code": "workflow_not_finished", "message": "Launch actions require a completed or completed_partial workflow"},
        )


def pending_human_confirmations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if str(item.get("status") or "pending") not in SAFE_CONFIRMATION_STATUSES]


def redact_for_client(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated_depth]"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            k = str(key)
            lk = k.lower()
            if any(token in lk for token in ("secret", "token", "api_key", "apikey", "password", "system_message", "raw_provider_response")):
                out[k] = "[redacted]"
            else:
                out[k] = redact_for_client(item, depth + 1)
        return out
    if isinstance(value, list):
        if len(value) > 250:
            return [redact_for_client(item, depth + 1) for item in value[:250]] + ["[truncated_list]"]
        return [redact_for_client(item, depth + 1) for item in value]
    if isinstance(value, str) and len(value) > 20000:
        return value[:20000] + "...[truncated]"
    return value
