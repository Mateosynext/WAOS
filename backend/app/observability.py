from __future__ import annotations
import json, logging
from typing import Any
from .config import settings
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
except Exception:
    sentry_sdk = None
    FastApiIntegration = None

def setup_observability() -> None:
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(message)s")
    if settings.sentry_dsn and sentry_sdk and FastApiIntegration:
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.app_env, release=settings.app_version, traces_sample_rate=0.05 if settings.is_production else 1.0, integrations=[FastApiIntegration()])

def log_event(event: str, **payload: Any) -> None:
    logging.getLogger("waos").info(json.dumps({"event": event, **payload}, ensure_ascii=False, default=str))

def capture_exception(exc: Exception, **payload: Any) -> None:
    logging.getLogger("waos").error(json.dumps({"event": "exception", "error": str(exc), **payload}, ensure_ascii=False, default=str))
    if sentry_sdk:
        with sentry_sdk.push_scope() as scope:
            for key, value in payload.items():
                scope.set_tag(key, value)
            sentry_sdk.capture_exception(exc)

def capture_message(message: str, level: str = "error", **payload: Any) -> None:
    logging.getLogger("waos").log(getattr(logging, level.upper(), logging.ERROR), json.dumps({"event": "frontend_error", "message": message, **payload}, ensure_ascii=False, default=str))
    if sentry_sdk:
        with sentry_sdk.push_scope() as scope:
            for key, value in payload.items():
                scope.set_tag(key, value)
            sentry_sdk.capture_message(message, level=level)
