from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402


def _host(url: str) -> str:
    return (urlparse(url).hostname or '').lower()


def _validate_ai_provider_alignment(errors: list[str], warnings: list[str]) -> None:
    if not settings.openai_api_key:
        warnings.append('OPENAI_API_KEY no está configurada; las funciones de IA caerán a modo degradado.' if __file__.endswith('preflight_check.py') else 'OPENAI_API_KEY is empty; AI features will run in degraded mode.')
        return
    try:
        settings.validate_ai_provider_alignment(require_explicit=settings.is_production)
    except ValueError as exc:
        errors.append(str(exc))


def _validate_autopilot_budget(errors: list[str]) -> None:
    if settings.openai_timeout_seconds != 30:
        errors.append('OPENAI_TIMEOUT_SECONDS debe mantenerse en 30 para el presupuesto de timeout del autopilot.' if __file__.endswith('preflight_check.py') else 'OPENAI_TIMEOUT_SECONDS must stay at 30 for the autopilot timeout budget.')
    if settings.autopilot_max_autofix_rounds > 2:
        errors.append('AUTOPILOT_MAX_AUTOFIX_ROUNDS no puede ser mayor que 2 en producción.' if __file__.endswith('preflight_check.py') else 'AUTOPILOT_MAX_AUTOFIX_ROUNDS cannot be greater than 2 in production.')


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    public_host = _host(settings.public_app_url)
    api_host = _host(settings.api_base_url)
    allowed_hosts = {item.strip().lower() for item in settings.allowed_hosts if item.strip()}
    cors_hosts = {_host(item) for item in settings.cors_allowed_origins if item.strip()}

    if settings.is_production:
        if not public_host:
            errors.append('PUBLIC_APP_URL must be set to a valid https host.')
        if not api_host:
            errors.append('API_BASE_URL must be set to a valid https host.')
        if api_host and api_host not in allowed_hosts:
            errors.append('ALLOWED_HOSTS must include the API_BASE_URL host.')
        if public_host and public_host not in cors_hosts:
            errors.append('CORS_ALLOWED_ORIGINS must include the PUBLIC_APP_URL origin.')
        _validate_ai_provider_alignment(errors, warnings)
        _validate_autopilot_budget(errors)
        if settings.auto_run_migrations is False:
            warnings.append('AUTO_RUN_MIGRATIONS is false; ensure migrations are executed before deploy.')
    else:
        warnings.append('validate_render_env running outside production mode.')

    for line in warnings:
        print(f'[warn] {line}')
    if errors:
        for line in errors:
            print(f'[error] {line}')
        return 1
    print('[ok] render env validation passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
