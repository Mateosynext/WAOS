from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from .config import settings
from .apm import apm_overview
from .request_context import get_request_context

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
except Exception:  # pragma: no cover - optional dependency in local envs
    sentry_sdk = None
    FastApiIntegration = None

LOGGER_NAME = "waos"


def _json_default(value: Any) -> str:
    return str(value)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, str):
            try:
                payload = json.loads(record.msg)
            except Exception:
                payload = {"message": record.getMessage()}
        elif isinstance(record.msg, dict):
            payload = dict(record.msg)
        else:
            payload = {"message": record.getMessage()}
        payload.setdefault("timestamp", datetime.now(UTC).isoformat())
        payload.setdefault("level", record.levelname.lower())
        payload.setdefault("logger", record.name)
        payload.setdefault("service", settings.otel_service_name)
        payload.setdefault("environment", settings.app_env)
        payload.setdefault("version", settings.app_version)
        payload.setdefault("apm", apm_overview())
        context = get_request_context()
        if context is not None:
            for key, value in context.as_dict().items():
                payload.setdefault(key, value)
        for key in ("request_id", "correlation_id", "trace_id", "span_id", "organization_id", "bot_id", "user_id"):
            value = getattr(record, key, None)
            if value not in (None, ""):
                payload.setdefault(key, value)
        return json.dumps(payload, ensure_ascii=False, default=_json_default)



def _base_payload(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    context = get_request_context()
    enriched = {
        "event": event,
        **payload,
    }
    if context is not None:
        for key, value in context.as_dict().items():
            enriched.setdefault(key, value)
    return enriched



def setup_observability() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.propagate = False
    if settings.sentry_dsn and sentry_sdk and FastApiIntegration:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            release=settings.app_version,
            traces_sample_rate=0.05 if settings.is_production else 1.0,
            integrations=[FastApiIntegration()],
        )
    log_event('observability_initialized', apm=apm_overview(), sentry=bool(settings.sentry_dsn))



def log_event(event: str, **payload: Any) -> None:
    logging.getLogger(LOGGER_NAME).info(_base_payload(event, payload))



def log_security_event(event: str, **payload: Any) -> None:
    logging.getLogger(LOGGER_NAME).warning(_base_payload(event, {"stream": "security", **payload}))



def log_business_event(event: str, **payload: Any) -> None:
    logging.getLogger(LOGGER_NAME).info(_base_payload(event, {"stream": "business", **payload}))



def capture_exception(exc: Exception, **payload: Any) -> None:
    logging.getLogger(LOGGER_NAME).error(_base_payload("exception", {"error": str(exc), **payload}))
    if sentry_sdk:
        with sentry_sdk.push_scope() as scope:
            for key, value in _base_payload("exception", payload).items():
                if value is not None:
                    scope.set_tag(key, value)
            sentry_sdk.capture_exception(exc)



def capture_message(message: str, level: str = "error", **payload: Any) -> None:
    normalized_level = getattr(logging, level.upper(), logging.ERROR)
    logging.getLogger(LOGGER_NAME).log(normalized_level, _base_payload("frontend_error", {"message": message, **payload}))
    if sentry_sdk:
        with sentry_sdk.push_scope() as scope:
            for key, value in _base_payload("frontend_error", payload).items():
                if value is not None:
                    scope.set_tag(key, value)
            sentry_sdk.capture_message(message, level=level)
