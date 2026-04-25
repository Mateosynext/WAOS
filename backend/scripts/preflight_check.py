from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.db import get_connection  # noqa: E402


def _is_local(value: str | None) -> bool:
    raw = (value or '').strip().lower()
    return any(token in raw for token in ['localhost', '127.0.0.1'])


def _validate_ai_provider_alignment(errors: list[str], warnings: list[str]) -> None:
    if not settings.openai_api_key:
        message = 'OPENAI_API_KEY no configurada: AI Autopilot usará solo heurístico.' if __file__.endswith('preflight_check.py') else 'OPENAI_API_KEY is empty: AI Autopilot will run heuristic-only.'
        if settings.is_production:
            errors.append(message)
        else:
            warnings.append(message)
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

    if settings.is_production:
        api_host = settings.api_base_url.split('://', 1)[-1].split('/', 1)[0].split(':', 1)[0].lower()
        public_host = settings.public_app_url.split('://', 1)[-1].split('/', 1)[0].split(':', 1)[0].lower()
        cors_hosts = {
            origin.split('://', 1)[-1].split('/', 1)[0].split(':', 1)[0].lower()
            for origin in settings.cors_allowed_origins
            if origin.strip()
        }
        allowed_hosts = {host.strip().lower() for host in settings.allowed_hosts if host.strip()}

        if settings.app_secret_is_default:
            errors.append('APP_SECRET sigue con valor por defecto.')
        if settings.encryption_key_is_default:
            errors.append('SECRET_ENCRYPTION_KEY sigue con valor por defecto.')
        if settings.run_bootstrap_seed:
            errors.append('RUN_BOOTSTRAP_SEED debe ser false en producción.')
        if not settings.secure_cookies:
            errors.append('SECURE_COOKIES debe ser true en producción.')
        if _is_local(settings.public_app_url):
            errors.append('PUBLIC_APP_URL no puede apuntar a localhost en producción.')
        if _is_local(settings.api_base_url):
            errors.append('API_BASE_URL no puede apuntar a localhost en producción.')
        if not settings.cors_allowed_origins:
            errors.append('CORS_ALLOWED_ORIGINS no puede quedar vacío en producción.')
        if not settings.allowed_hosts:
            errors.append('ALLOWED_HOSTS no puede quedar vacío en producción.')
        if api_host and api_host not in allowed_hosts:
            errors.append('ALLOWED_HOSTS debe incluir el host de API_BASE_URL.')
        if public_host and public_host not in cors_hosts:
            errors.append('CORS_ALLOWED_ORIGINS debe incluir PUBLIC_APP_URL.')
        _validate_ai_provider_alignment(errors, warnings)
        _validate_autopilot_budget(errors)
    else:
        warnings.append('Preflight en entorno no productivo: algunas validaciones estrictas se omiten.')

    try:
        with get_connection() as conn:
            conn.execute('SELECT 1')
    except Exception as exc:  # pragma: no cover
        message = f'No se pudo abrir conexión a la base de datos: {exc}'
        if settings.startup_db_required:
            errors.append(message)
        else:
            warnings.append(message)

    if warnings:
        for item in warnings:
            print(f'[warn] {item}')
    if errors:
        for item in errors:
            print(f'[error] {item}')
        return 1

    print('[ok] preflight listo')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
