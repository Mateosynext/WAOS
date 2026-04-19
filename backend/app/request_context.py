from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from fastapi import Request

ORG_HEADER_ALIASES = ("x-waos-org-id", "x-organization-id", "x-org-id")
BOT_HEADER_ALIASES = ("x-waos-bot-id", "x-bot-id")
USER_HEADER_ALIASES = ("x-user-id", "x-waos-user-id")
SESSION_HEADER_ALIASES = ("x-session-id",)


@dataclass(slots=True)
class RequestContext:
    request_id: str | None = None
    correlation_id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    method: str | None = None
    path: str | None = None
    remote_ip: str | None = None
    user_agent: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value not in {None, ""}}


_current_request_context: ContextVar[RequestContext | None] = ContextVar("waos_request_context", default=None)


def bind_request_context(context: RequestContext) -> Token:
    return _current_request_context.set(context)


def reset_request_context(token: Token | None) -> None:
    if token is not None:
        _current_request_context.reset(token)


def get_request_context() -> RequestContext | None:
    return _current_request_context.get()


def _non_empty(values: Iterable[str | None]) -> list[str]:
    seen: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if normalized and normalized not in seen:
            seen.append(normalized)
    return seen


def _extract_candidates(request: Request, *, param_names: tuple[str, ...], header_aliases: tuple[str, ...]) -> list[str]:
    path_values = [request.path_params.get(name) for name in param_names]
    query_values = [request.query_params.get(name) for name in param_names]
    header_values = [request.headers.get(name) for name in header_aliases]
    return _non_empty([*path_values, *query_values, *header_values])


def _extract_scoped_value(request: Request, *, label: str, param_names: tuple[str, ...], header_aliases: tuple[str, ...]) -> str | None:
    candidates = _extract_candidates(request, param_names=param_names, header_aliases=header_aliases)
    if len(candidates) > 1:
        raise ValueError(f"Conflicting {label} values in request scope")
    return candidates[0] if candidates else None


def extract_org_id(request: Request) -> str | None:
    return _extract_scoped_value(
        request,
        label="organization",
        param_names=("organization_id",),
        header_aliases=ORG_HEADER_ALIASES,
    )


def extract_bot_id(request: Request) -> str | None:
    return _extract_scoped_value(
        request,
        label="bot",
        param_names=("bot_id",),
        header_aliases=BOT_HEADER_ALIASES,
    )


def extract_request_user_id(request: Request) -> str | None:
    candidates = _extract_candidates(request, param_names=("user_id",), header_aliases=USER_HEADER_ALIASES)
    if len(candidates) > 1:
        raise ValueError("Conflicting user values in request scope")
    if candidates:
        return candidates[0]
    return getattr(request.state, "user_id", None)


def extract_session_id(request: Request) -> str | None:
    candidates = _extract_candidates(request, param_names=("session_id",), header_aliases=SESSION_HEADER_ALIASES)
    if len(candidates) > 1:
        raise ValueError("Conflicting session values in request scope")
    if candidates:
        return candidates[0]
    return getattr(request.state, "session_id", None)


def build_request_context(request: Request) -> RequestContext:
    return RequestContext(
        request_id=request.headers.get("x-request-id") or getattr(request.state, "request_id", None),
        correlation_id=request.headers.get("x-correlation-id") or getattr(request.state, "correlation_id", None),
        organization_id=extract_org_id(request),
        bot_id=extract_bot_id(request),
        user_id=extract_request_user_id(request),
        session_id=extract_session_id(request),
        trace_id=request.headers.get("x-trace-id") or request.headers.get("traceparent") or getattr(request.state, "trace_id", None),
        span_id=request.headers.get("x-span-id") or getattr(request.state, "span_id", None),
        parent_span_id=request.headers.get("x-parent-span-id") or getattr(request.state, "parent_span_id", None),
        method=request.method,
        path=request.url.path,
        remote_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
