from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402


def _host(url: str) -> str:
    return (urlparse(url).hostname or '').lower()


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
        if not settings.openai_api_key:
            warnings.append('OPENAI_API_KEY is empty; AI features will run in degraded mode.')
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
