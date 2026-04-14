from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .config import settings
from .db import close_connection_pool, get_connection, init_db
from .http_runtime import extract_bot_id, extract_org_id, extract_request_user_id, organization_origin_policy
from .observability import capture_exception, log_event, setup_observability
from .repositories import ensure_seed_data
from .api.handlers.support import _read_global_settings
from .utils import new_id

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"


def _validate_startup_security() -> None:
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_startup_security()
    init_db()
    if settings.run_bootstrap_seed:
        with get_connection() as conn:
            ensure_seed_data(conn)
    _read_global_settings()
    yield
    close_connection_pool()


app = FastAPI(
    title="WAOS API",
    version=settings.app_version,
    description="WAOS v13.1 API production-ready: PostgreSQL, Business Hub, catalog, media, promotions, Bot Studio, launch readiness and enriched customer experience.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=settings.gzip_minimum_size,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

setup_observability()


@app.middleware("http")
async def waos_runtime_headers(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or new_id("req")
    started_at = time.perf_counter()
    org_id = extract_org_id(request)
    bot_id = extract_bot_id(request)
    user_id = extract_request_user_id(request)
    request.state.request_id = request_id
    request.state.organization_id = org_id
    request.state.bot_id = bot_id
    request.state.user_id = user_id
    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        capture_exception(
            exc,
            request_id=request_id,
            organization_id=org_id,
            bot_id=bot_id,
            user_id=user_id,
            path=request.url.path,
            method=request.method,
            duration_ms=elapsed_ms,
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    response.headers["X-WAOS-Version"] = settings.app_version
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
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
    )
    return response


app.middleware("http")(organization_origin_policy)
app.include_router(api_router)
