from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path
from typing import Any, Mapping

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .request_context import get_request_context


@dataclass(slots=True)
class AppError(Exception):
    message: str
    status_code: int = 400
    code: str = "bad_request"
    retryable: bool = False
    details: Mapping[str, Any] | list[Any] | None = None
    headers: Mapping[str, str] | None = None
    category: str = "request"
    expose_detail: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class ValidationAppError(AppError):
    def __init__(self, message: str = "Validation failed", *, details: Mapping[str, Any] | list[Any] | None = None):
        super().__init__(message=message, status_code=422, code="validation_error", details=details, category="validation")


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized", *, code: str = "unauthorized"):
        super().__init__(message=message, status_code=401, code=code, category="auth")


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden", *, code: str = "forbidden"):
        super().__init__(message=message, status_code=403, code=code, category="authorization")


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", *, code: str = "not_found"):
        super().__init__(message=message, status_code=404, code=code, category="not_found")


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", *, code: str = "conflict", details: Mapping[str, Any] | None = None):
        super().__init__(message=message, status_code=409, code=code, category="conflict", details=details)


class RateLimitedError(AppError):
    def __init__(self, message: str = "Too many requests", *, details: Mapping[str, Any] | None = None):
        super().__init__(message=message, status_code=429, code="rate_limited", retryable=True, category="throttle", details=details)


class TenantIsolationError(ForbiddenError):
    def __init__(self, message: str = "No access to organization"):
        super().__init__(message=message, code="tenant_forbidden")


class ProviderError(AppError):
    def __init__(self, message: str = "Provider request failed", *, code: str = "provider_error", retryable: bool = False, details: Mapping[str, Any] | None = None):
        super().__init__(message=message, status_code=502, code=code, retryable=retryable, category="provider", details=details)


class StepUpRequiredError(AppError):
    def __init__(self, message: str = "Step-up authentication required"):
        super().__init__(message=message, status_code=403, code="step_up_required", category="authorization")


class InternalServerAppError(AppError):
    def __init__(self, message: str = "Internal server error"):
        super().__init__(message=message, status_code=500, code="internal_error", retryable=True, category="internal", expose_detail=False)


MAX_ERROR_STRING_LENGTH = 4000
MAX_ERROR_COLLECTION_ITEMS = 200
MAX_ERROR_DEPTH = 8


def _request_metadata(request: Request | None) -> dict[str, str | None]:
    request_id = getattr(request.state, "request_id", None) if request else None
    correlation_id = getattr(request.state, "correlation_id", None) if request else None
    context = get_request_context()
    if context is not None:
        request_id = request_id or context.request_id
        correlation_id = correlation_id or context.correlation_id
    return {"request_id": request_id, "correlation_id": correlation_id}


def _bounded_string(value: Any, *, limit: int = MAX_ERROR_STRING_LENGTH) -> str:
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}...[truncated]"


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    """Return a JSON-serializable representation for every error payload.

    Pydantic validation errors can contain raw Python exceptions inside
    ``ctx.error``. Starlette's JSONResponse cannot encode those objects, so
    every public error response must pass through this small allow-list.
    """
    if depth > MAX_ERROR_DEPTH:
        return "[truncated_depth]"
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if value == value and value not in {float("inf"), float("-inf")} else str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _json_safe(value.value, depth=depth + 1)
    if isinstance(value, BaseException):
        return _bounded_string(value)
    if isinstance(value, bytes):
        return _bounded_string(value.decode("utf-8", errors="replace"))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item, depth=depth + 1) for key, item in list(value.items())[:MAX_ERROR_COLLECTION_ITEMS]}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:MAX_ERROR_COLLECTION_ITEMS]]
    try:
        json.dumps(value, allow_nan=False)
        return value
    except (TypeError, ValueError):
        return _bounded_string(value)


def app_error_from_http_exception(exc: HTTPException) -> AppError:
    detail = _json_safe(exc.detail)
    if isinstance(detail, dict):
        return AppError(
            message=str(detail.get("message") or detail.get("detail") or "Request failed"),
            status_code=exc.status_code,
            code=str(detail.get("code") or "request_error"),
            details=detail,
            headers=exc.headers,
            category="request" if exc.status_code < 500 else "internal",
        )
    return AppError(
        message=str(detail or "Request failed"),
        status_code=exc.status_code,
        code="request_error" if exc.status_code < 500 else "internal_error",
        headers=exc.headers,
        category="request" if exc.status_code < 500 else "internal",
    )


def app_error_from_validation(exc: RequestValidationError) -> ValidationAppError:
    return ValidationAppError(details={"errors": _json_safe(exc.errors())})


def error_body(error: AppError, *, request: Request | None = None) -> dict[str, Any]:
    metadata = _request_metadata(request)
    message = _bounded_string(error.message if error.expose_detail or error.status_code < 500 else "Internal server error")
    payload: dict[str, Any] = {
        "ok": False,
        "error": {
            "code": error.code,
            "message": message,
            "retryable": error.retryable,
            "category": error.category,
        },
        "detail": message,
        "message": message,
        **metadata,
    }
    if error.details is not None and error.details != {}:
        payload["error"]["details"] = _json_safe(error.details)
    if error.extra:
        payload["error"].update(_json_safe(error.extra))
    return payload


def error_response(error: AppError, *, request: Request | None = None) -> JSONResponse:
    content = _json_safe(error_body(error, request=request))
    try:
        return JSONResponse(status_code=error.status_code, content=content, headers=dict(error.headers or {}))
    except Exception:
        # Last line of defense: never let error rendering become the 500.
        fallback_message = "Internal server error" if error.status_code >= 500 else _bounded_string(error.message)
        return JSONResponse(
            status_code=error.status_code,
            content={
                "ok": False,
                "error": {"code": error.code, "message": fallback_message, "retryable": error.retryable, "category": error.category},
                "detail": fallback_message,
                "message": fallback_message,
                **_request_metadata(request),
            },
            headers=dict(error.headers or {}),
        )
