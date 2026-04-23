from __future__ import annotations

from fastapi import HTTPException

from .tool_execution_adapters import DEFAULT_ACTION_POLICIES, ActionPolicy


def resolve_action_policy(action: str) -> ActionPolicy:
    policy = DEFAULT_ACTION_POLICIES.get(action)
    if not policy:
        raise HTTPException(status_code=400, detail="unsupported_tool_action")
    return policy
