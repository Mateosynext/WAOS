from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api import api_router
from .runtime_settings import read_global_settings
from .config import settings
from .db import close_connection_pool, get_connection, init_db
from .errors import AppError, InternalServerAppError, app_error_from_http_exception, app_error_from_validation, error_response
from .http_runtime import extract_bot_id, extract_org_id, extract_request_user_id, organization_origin_policy
from .observability import capture_exception, log_event, setup_observability
from .repositories import ensure_seed_data
from .request_context import RequestContext, bind_request_context, reset_request_context
from .utils import new_id
from .world_class import finish_trace_span, start_trace_span

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"



def _validate_startup_security() -> None:
    settings.validate_runtime()
    if not settings.strict_security_startup:
        return
    if settings.is_production and settings.app_secret_is_default:
        raise RuntimeError("APP_SECRET must be rotated before production startup")
    if settings.is_production and settings.encryption_key_is_default:
        raise RuntimeError("SECRET_ENCRYPTION_KEY must be rotated before production startup")
    if len(settings.app_secret.strip()) < settings.minimum_secret_length:
        raise RuntimeError("APP_SECRET is too short for hardened startup")
    if len(settings.secret_encryption_key.strip()) < settings.minimum_secret_length:
        raise RuntimeError("SECRET_ENCRYPTION_KEY is too short for hardened startup")
    if settings.is_production and settings.meta_verify_token_is_default:
        raise RuntimeError("META_VERIFY_TOKEN must be rotated before production startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_startup_security()
    init_db()
    if settings.run_bootstrap_seed:
        with get_connection() as conn:
            ensure_seed_data(conn)
    read_global_settings()
    yield
    close_connection_pool()


app = FastAPI(
    title="WAOS API",
    version=settings.app_version,
    description="WAOS v13.1 API production-ready: PostgreSQL, Business Hub, catalog, media, promotions, Bot Studio, launch readiness and enriched customer experience.",
    lifespan=lifespan,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.app_env.strip().lower() not in {"test", "testing"}:
    app.add_middleware(GZipMiddleware, minimum_size=settings.gzip_minimum_size)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

setup_observability()


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError):
    return error_response(exc, request=request)


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    return error_response(app_error_from_http_exception(exc), request=request)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    return error_response(app_error_from_validation(exc), request=request)


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception):
    return error_response(InternalServerAppError(), request=request)


@app.middleware("http")
async def waos_runtime_headers(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or new_id("req")
    correlation_id = request.headers.get("x-correlation-id") or request_id
    trace_id = request.headers.get("x-trace-id") or request.headers.get("traceparent") or correlation_id
    parent_span_id = request.headers.get("x-parent-span-id")
    span_id = request.headers.get("x-span-id") or new_id("span")
    started_at = time.perf_counter()
    try:
        org_id = extract_org_id(request)
        bot_id = extract_bot_id(request)
        user_id = extract_request_user_id(request)
    except ValueError as exc:
        error = AppError(str(exc), status_code=400, code="scope_conflict", category="validation")
        response = error_response(error, request=request)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Correlation-Id"] = correlation_id
        return response
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id
    request.state.organization_id = org_id
    request.state.bot_id = bot_id
    request.state.user_id = user_id
    request.state.trace_id = trace_id
    request.state.parent_span_id = parent_span_id
    request.state.span_id = span_id
    context_token = bind_request_context(
        RequestContext(
            request_id=request_id,
            correlation_id=correlation_id,
            organization_id=org_id,
            bot_id=bot_id,
            user_id=user_id,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            method=request.method,
            path=request.url.path,
            remote_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )
    response = None
    with get_connection() as conn:
        start_trace_span(
            conn,
            trace_id=str(trace_id),
            span_id=str(span_id),
            parent_span_id=parent_span_id,
            name=f"http:{request.method}:{request.url.path}",
            organization_id=org_id,
            bot_id=bot_id,
            request_id=request_id,
            correlation_id=correlation_id,
            attributes={"method": request.method, "path": request.url.path},
        )
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        with get_connection() as conn:
            finish_trace_span(conn, trace_id=str(trace_id), span_id=str(span_id), status='error', attributes={"duration_ms": elapsed_ms})
        capture_exception(
            exc,
            request_id=request_id,
            organization_id=org_id,
            bot_id=bot_id,
            user_id=user_id,
            path=request.url.path,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            method=request.method,
            duration_ms=elapsed_ms,
            correlation_id=correlation_id,
        )
        raise
    finally:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        with get_connection() as conn:
            finish_trace_span(conn, trace_id=str(trace_id), span_id=str(span_id), status='ok' if response is not None and response.status_code < 500 else 'error', attributes={"duration_ms": elapsed_ms, "status_code": getattr(response, 'status_code', None)})
        if response is not None:
            response.headers["X-Request-Id"] = request_id
            response.headers["X-Correlation-Id"] = correlation_id
            response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
            response.headers["X-Trace-Id"] = str(trace_id)
            response.headers["X-Span-Id"] = str(span_id)
            response.headers["X-WAOS-Version"] = settings.app_version
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
            response.headers["Cache-Control"] = response.headers.get("Cache-Control") or "no-store"
            if settings.is_production:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            log_event(
                "http_request",
                request_id=request_id,
                organization_id=org_id,
                bot_id=bot_id,
                user_id=user_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=elapsed_ms,
                correlation_id=correlation_id,
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                transaction_mode=getattr(request.state, "transaction_mode", None),
            )
        reset_request_context(context_token)


app.middleware("http")(organization_origin_policy)
app.include_router(api_router)
