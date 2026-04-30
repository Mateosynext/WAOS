from __future__ import annotations

import hashlib
import ipaddress
import secrets
import time
from collections import OrderedDict, deque
from typing import Awaitable, Callable

from fastapi import Request
from starlette.responses import JSONResponse, Response

from .config import settings

_HEALTH_PATHS = {"/", "/livez", "/health", "/healthz", "/readyz", "/favicon.ico"}
_PROXY_HEADERS = ("x-forwarded-for", "x-forwarded-proto", "x-forwarded-host", "x-real-ip", "cf-connecting-ip", "forwarded")
_RATE_BUCKETS: OrderedDict[str, deque[float]] = OrderedDict()
_REDIS_RATE_LIMIT_CLIENT = None


class RateLimitBackendUnavailable(RuntimeError):
    """Raised when the configured distributed rate-limit backend is unavailable."""



def _json_error(status_code: int, code: str, message: str, *, retry_after: int | None = None) -> JSONResponse:
    response = JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})
    if retry_after is not None:
        response.headers["Retry-After"] = str(max(1, int(retry_after)))
    _apply_security_headers(response)
    return response


def _remote_addr(request: Request) -> str:
    return (request.client.host if request.client else "") or "unknown"


def _ip_is_trusted_proxy(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    try:
        return any(ip in network for network in settings.trusted_proxy_networks)
    except ValueError:
        return False


def _proxy_headers_present(request: Request) -> bool:
    return any(header in request.headers for header in _PROXY_HEADERS)


def _client_ip(request: Request) -> str:
    remote = _remote_addr(request)
    if settings.trust_proxy_headers and _ip_is_trusted_proxy(remote):
        for header in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for"):
            raw = request.headers.get(header)
            if raw:
                first = raw.split(",", 1)[0].strip()
                if first:
                    return first
    return remote


def _request_is_https(request: Request) -> bool:
    if str(request.url.scheme).lower() == "https":
        return True
    remote = _remote_addr(request)
    if settings.trust_proxy_headers and _ip_is_trusted_proxy(remote):
        proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
        return proto == "https"
    return False


def _body_limit_for(path: str) -> int:
    return settings.max_webhook_body_bytes if path.startswith("/webhooks/") else settings.max_request_body_bytes


def _rate_policy_for(path: str) -> tuple[str, int, int] | None:
    if path in _HEALTH_PATHS:
        return None
    if path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/refresh"):
        return ("auth", settings.auth_rate_limit_window_seconds, settings.auth_rate_limit_max_requests)
    if path.startswith("/webhooks/"):
        return ("webhook", settings.webhook_rate_limit_window_seconds, settings.webhook_rate_limit_max_requests)
    return ("global", settings.global_rate_limit_window_seconds, settings.global_rate_limit_max_requests)


def _safe_rate_key(raw_key: str) -> str:
    # Keep PII such as IP addresses out of Redis keys and logs. The scope is
    # still represented in raw_key, but the stored key is a stable digest.
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return f"{settings.rate_limit_key_prefix}:{digest}"


def _local_bucket_for(key: str) -> deque[float]:
    bucket = _RATE_BUCKETS.get(key)
    if bucket is not None:
        _RATE_BUCKETS.move_to_end(key)
        return bucket
    max_buckets = max(1, int(settings.rate_limit_memory_max_buckets))
    eviction_batch = max(1, int(settings.rate_limit_memory_eviction_batch))
    while len(_RATE_BUCKETS) >= max_buckets:
        for _ in range(min(eviction_batch, len(_RATE_BUCKETS))):
            _RATE_BUCKETS.popitem(last=False)
        if len(_RATE_BUCKETS) < max_buckets:
            break
    bucket = deque()
    _RATE_BUCKETS.__setitem__(key, bucket)
    return bucket


def _check_in_process_rate_limit(*, key: str, window_seconds: int, max_requests: int) -> tuple[bool, int, int]:
    now = time.monotonic()
    bucket = _local_bucket_for(key)
    cutoff = now - float(window_seconds)
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= int(max_requests):
        retry_after = int(max(1, window_seconds - (now - bucket[0]))) if bucket else int(window_seconds)
        return False, retry_after, 0
    bucket.append(now)
    remaining = max(0, int(max_requests) - len(bucket))
    return True, int(window_seconds), remaining


def _get_redis_rate_limit_client():
    global _REDIS_RATE_LIMIT_CLIENT
    if _REDIS_RATE_LIMIT_CLIENT is not None:
        return _REDIS_RATE_LIMIT_CLIENT
    if not settings.rate_limit_redis_url:
        raise RateLimitBackendUnavailable("RATE_LIMIT_REDIS_URL/REDIS_URL is required for distributed rate limiting")
    try:
        import redis.asyncio as redis
    except Exception as exc:  # pragma: no cover - exercised in production packaging, not local unit tests.
        raise RateLimitBackendUnavailable("redis package is required for distributed rate limiting") from exc
    _REDIS_RATE_LIMIT_CLIENT = redis.from_url(
        settings.rate_limit_redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=float(settings.rate_limit_redis_timeout_seconds),
        socket_connect_timeout=float(settings.rate_limit_redis_timeout_seconds),
        health_check_interval=30,
    )
    return _REDIS_RATE_LIMIT_CLIENT


_REDIS_RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_requests = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local current = tonumber(redis.call('ZCARD', key))
if current >= max_requests then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local retry_after = window
  if oldest[2] then
    retry_after = math.max(1, math.ceil(window - (now - tonumber(oldest[2]))))
  end
  redis.call('EXPIRE', key, math.ceil(window))
  return {0, retry_after, 0}
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, math.ceil(window))
return {1, math.ceil(window), math.max(0, max_requests - current - 1)}
"""


async def _check_distributed_rate_limit(*, key: str, window_seconds: int, max_requests: int) -> tuple[bool, int, int]:
    client = _get_redis_rate_limit_client()
    redis_key = _safe_rate_key(key)
    now = time.time()
    member = f"{now:.6f}:{secrets.token_hex(8)}"
    try:
        allowed, retry_after, remaining = await client.eval(
            _REDIS_RATE_LIMIT_LUA,
            1,
            redis_key,
            now,
            int(window_seconds),
            int(max_requests),
            member,
        )
    except Exception as exc:  # pragma: no cover - depends on external Redis/Valkey/Upstash.
        raise RateLimitBackendUnavailable("distributed rate-limit backend unavailable") from exc
    return bool(int(allowed)), int(retry_after), int(remaining)


async def _check_rate_limit(*, key: str, window_seconds: int, max_requests: int) -> tuple[bool, int, int]:
    backend = settings.rate_limit_backend
    if backend in {"redis", "valkey", "upstash"}:
        return await _check_distributed_rate_limit(
            key=key,
            window_seconds=window_seconds,
            max_requests=max_requests,
        )
    if backend == "gateway" and not settings.rate_limit_gateway_fallback_enabled:
        return True, int(window_seconds), int(max_requests)
    return _check_in_process_rate_limit(
        key=key,
        window_seconds=window_seconds,
        max_requests=max_requests,
    )


def _hsts_value() -> str:
    value = f"max-age={int(settings.hsts_max_age_seconds)}"
    if settings.hsts_include_subdomains:
        value += "; includeSubDomains"
    if settings.hsts_preload:
        value += "; preload"
    return value


def _apply_security_headers(response: Response) -> None:
    headers = response.headers
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=()")
    headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    headers.setdefault("Cross-Origin-Embedder-Policy", "require-corp")
    headers.setdefault("Cache-Control", "no-store")
    if settings.content_security_policy:
        headers.setdefault("Content-Security-Policy", settings.content_security_policy)
    if settings.is_production:
        headers["Strict-Transport-Security"] = _hsts_value()


async def _read_limited_body(request: Request, *, limit: int) -> tuple[bytes | None, JSONResponse | None]:
    """Read the request body with an early streaming cutoff.

    Starlette request.body() buffers the full payload before callers can
    inspect its size. That is unsafe for chunked requests or clients that
    omit Content-Length. This helper consumes request.stream() incrementally
    and returns 413 as soon as accumulated bytes cross the configured limit.
    Accepted bodies remain bounded by the limit and are replayed downstream.
    """
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        if not chunk:
            continue
        total += len(chunk)
        if total > limit:
            return None, _json_error(413, "request_body_too_large", f"Request body exceeds {limit} bytes.")
        chunks.append(chunk)
    return b"".join(chunks), None


def _restore_limited_body(request: Request, body: bytes) -> None:
    """Make a middleware-consumed bounded body available to route handlers."""
    sent = False

    async def receive() -> dict[str, object]:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    request._body = body  # noqa: SLF001 - Starlette cache for downstream request.body()/stream().
    request._receive = receive  # noqa: SLF001 - replay bounded body for downstream ASGI consumers.
    request._stream_consumed = False  # noqa: SLF001 - allow downstream stream() after middleware inspection.


async def waos_security_gate(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    if not settings.security_hardening_enabled:
        return await call_next(request)
    path = request.url.path
    remote = _remote_addr(request)
    if settings.reject_untrusted_proxy_headers and _proxy_headers_present(request) and not _ip_is_trusted_proxy(remote):
        return _json_error(400, "untrusted_proxy_headers", "Proxy headers are only accepted from trusted proxy IP ranges.")
    if settings.enforce_https and path not in _HEALTH_PATHS and not _request_is_https(request):
        return _json_error(400, "https_required", "HTTPS is required for this endpoint.")
    limit = _body_limit_for(path)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            length = int(content_length)
        except ValueError:
            return _json_error(400, "invalid_content_length", "Invalid Content-Length header.")
        if length > limit:
            return _json_error(413, "request_body_too_large", f"Request body exceeds {limit} bytes.")
    if request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        body, body_error = await _read_limited_body(request, limit=limit)
        if body_error is not None:
            return body_error
        _restore_limited_body(request, body or b"")
    if settings.security_rate_limit_enabled:
        policy = _rate_policy_for(path)
        if policy:
            scope, window_seconds, max_requests = policy
            try:
                ok, retry_after, remaining = await _check_rate_limit(
                    key=f"{scope}:{_client_ip(request)}",
                    window_seconds=window_seconds,
                    max_requests=max_requests,
                )
            except RateLimitBackendUnavailable:
                return _json_error(503, "rate_limit_backend_unavailable", "Distributed rate-limit backend is unavailable.")
            if not ok:
                return _json_error(429, "rate_limit_exceeded", "Too many requests.", retry_after=retry_after)
            request.state.rate_limit_scope = scope
            request.state.rate_limit_remaining = remaining
    response = await call_next(request)
    _apply_security_headers(response)
    if getattr(request.state, "rate_limit_scope", None):
        _, window_seconds, max_requests = _rate_policy_for(path) or ("global", 0, 0)
        response.headers.setdefault("X-RateLimit-Limit", str(max_requests))
        response.headers.setdefault("X-RateLimit-Remaining", str(getattr(request.state, "rate_limit_remaining", 0)))
        response.headers.setdefault("X-RateLimit-Window", str(window_seconds))
    return response
