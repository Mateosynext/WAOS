from __future__ import annotations

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


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if settings.is_production:
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
    else:
        warnings.append('Preflight en entorno no productivo: algunas validaciones estrictas se omiten.')

    try:
        with get_connection() as conn:
            conn.execute('SELECT 1')
    except Exception as exc:  # pragma: no cover
        errors.append(f'No se pudo abrir conexión a la base de datos: {exc}')

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
