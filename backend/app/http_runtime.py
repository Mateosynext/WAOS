from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from .db import get_connection
from .platform import get_security_policy


def extract_org_id(request: Request) -> str | None:
    return (
        request.path_params.get("organization_id")
        or request.query_params.get("organization_id")
        or request.headers.get("x-organization-id")
    )


def extract_bot_id(request: Request) -> str | None:
    return (
        request.path_params.get("bot_id")
        or request.query_params.get("bot_id")
        or request.headers.get("x-bot-id")
    )


def extract_request_user_id(request: Request) -> str | None:
    return request.headers.get("x-user-id") or getattr(request.state, "user_id", None)


async def organization_origin_policy(request: Request, call_next):
    origin = request.headers.get("origin")
    organization_id = extract_org_id(request)
    if origin and organization_id:
        with get_connection() as conn:
            policy = get_security_policy(conn, organization_id=organization_id)
        allowed = policy.get("allowed_origins") or []
        if allowed and origin not in allowed:
            return JSONResponse(status_code=403, content={"detail": "Origin not allowed for organization"})
        response = await call_next(request)
        if allowed and origin in allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        return response
    return await call_next(request)
