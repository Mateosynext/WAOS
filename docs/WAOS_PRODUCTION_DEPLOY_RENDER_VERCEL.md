# WAOS Production Deploy: Render + Vercel

## Backend en Render
- Usa `render.yaml` desde la raíz del repo.
- El web service arranca con `bash backend/scripts/bootstrap.sh` vía `rootDir: backend`.
- El worker arranca con `bash backend/scripts/worker_bootstrap.sh`.
- Define en Render: `PUBLIC_APP_URL`, `API_BASE_URL`, `CORS_ALLOWED_ORIGINS`, `ALLOWED_HOSTS`, `OPENAI_API_KEY`, `META_VERIFY_TOKEN`, `SENTRY_DSN`.
- Mantén `RUN_BOOTSTRAP_SEED=false`.

## Frontend en Vercel
- Usa `frontend/vercel.json`.
- Define en Vercel: `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_URL`, `API_BASE_URL`, `API_INTERNAL_URL`.
- Ejecuta `npm run build` dentro de `frontend/`.

## Go-live checklist
1. Base PostgreSQL creada y enlazada en Render.
2. Migraciones automáticas activas.
3. Secrets de OpenAI, Meta y App Secret definidos.
4. Vercel apuntando al backend productivo real.
5. CORS y hosts cerrados al dominio final.
6. `SECURE_COOKIES=true` en ambos lados.
7. `AUTO_RUN_MIGRATIONS=true` solo en el backend productivo principal.
8. Worker activo para comandos operativos, schedules y replay.

## Verificación recomendada
- `python -m compileall backend/app backend/worker.py`
- `PYTHONPATH=. pytest -q backend/tests/test_vertical_10x_phase7.py backend/tests/test_operational_control_phase6.py backend/tests/test_activation_foundations.py`
- `python scripts/release_scan.py .`
