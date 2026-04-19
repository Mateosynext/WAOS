from __future__ import annotations

import os
from typing import Any

from .config import settings


def _clean(value: str | None) -> str:
    return str(value or "").strip()


def resolve_apm_targets() -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    if settings.otel_export_endpoint:
        targets.append(
            {
                "provider": "otlp",
                "endpoint": settings.otel_export_endpoint,
                "headers": {},
                "enabled": bool(settings.otel_export_enabled),
                "service": settings.otel_service_name,
            }
        )

    datadog_endpoint = _clean(os.getenv("DATADOG_OTLP_ENDPOINT"))
    datadog_api_key = _clean(os.getenv("DATADOG_API_KEY"))
    if datadog_endpoint:
        targets.append(
            {
                "provider": "datadog",
                "endpoint": datadog_endpoint,
                "headers": {"DD-API-KEY": datadog_api_key} if datadog_api_key else {},
                "enabled": bool(settings.otel_export_enabled and datadog_api_key),
                "service": _clean(os.getenv("DATADOG_SERVICE")) or settings.otel_service_name,
                "environment": _clean(os.getenv("DATADOG_ENV")) or settings.app_env,
            }
        )

    new_relic_endpoint = _clean(os.getenv("NEW_RELIC_OTLP_ENDPOINT"))
    new_relic_license = _clean(os.getenv("NEW_RELIC_LICENSE_KEY"))
    if new_relic_endpoint:
        targets.append(
            {
                "provider": "new_relic",
                "endpoint": new_relic_endpoint,
                "headers": {"api-key": new_relic_license} if new_relic_license else {},
                "enabled": bool(settings.otel_export_enabled and new_relic_license),
                "service": _clean(os.getenv("NEW_RELIC_APP_NAME")) or settings.otel_service_name,
                "environment": settings.app_env,
            }
        )
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for target in targets:
        key = (str(target.get("provider") or ""), str(target.get("endpoint") or ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(target)
    return deduped



def default_export_target() -> dict[str, Any] | None:
    targets = resolve_apm_targets()
    for target in targets:
        if target.get("endpoint"):
            return target
    return None



def apm_overview() -> dict[str, Any]:
    targets = resolve_apm_targets()
    return {
        "enabled": any(bool(target.get("enabled")) for target in targets),
        "providers": [
            {
                "provider": target.get("provider"),
                "endpoint": target.get("endpoint"),
                "enabled": bool(target.get("enabled")),
                "service": target.get("service"),
                "environment": target.get("environment") or settings.app_env,
                "has_auth": bool(target.get("headers")),
            }
            for target in targets
        ],
    }
