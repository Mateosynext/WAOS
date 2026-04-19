from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from .db import get_connection
from .errors import AppError, ForbiddenError, error_body
from .platform import get_security_policy
from .utils import new_id
from .request_context import extract_bot_id as _extract_bot_id
from .request_context import extract_org_id as _extract_org_id
from .request_context import extract_request_user_id as _extract_request_user_id


def extract_org_id(request: Request) -> str | None:
    return _extract_org_id(request)



def extract_bot_id(request: Request) -> str | None:
    return _extract_bot_id(request)



def extract_request_user_id(request: Request) -> str | None:
    return _extract_request_user_id(request)



def _error_response(request: Request, error) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or getattr(request.state, "request_id", None) or new_id("req")
    correlation_id = request.headers.get("x-correlation-id") or getattr(request.state, "correlation_id", None) or request_id
    payload = error_body(error, request=request)
    payload["request_id"] = payload.get("request_id") or request_id
    payload["correlation_id"] = payload.get("correlation_id") or correlation_id
    response = JSONResponse(status_code=error.status_code, content=payload)
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Correlation-Id"] = correlation_id
    return response


async def organization_origin_policy(request: Request, call_next):
    try:
        organization_id = extract_org_id(request)
    except ValueError as exc:
        return _error_response(request, AppError(str(exc), status_code=400, code="scope_conflict", category="validation"))
    origin = request.headers.get("origin")
    if origin and organization_id:
        with get_connection() as conn:
            policy = get_security_policy(conn, organization_id=organization_id)
        allowed = policy.get("allowed_origins") or []
        if allowed and origin not in allowed:
            return _error_response(request, ForbiddenError("Origin not allowed for organization", code="origin_not_allowed"))
        response = await call_next(request)
        if allowed and origin in allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        return response
    return await call_next(request)
