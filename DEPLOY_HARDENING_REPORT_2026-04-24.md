# WAOS Deploy Hardening Report — 2026-04-24

## Resultado

Los 5 arreglos críticos quedaron blindados con validaciones de arranque, guardias de CI y pruebas específicas para evitar regresiones antes de deploy.

## Blindajes agregados

### 1. Modelo/proveedor IA alineado y fail-fast

- `render.yaml` y `backend/render.yaml` conservan:
  - `OPENAI_MODEL=gemini-2.0-flash`
  - `OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`
  - `OPENAI_API_KEY` como secreto `sync: false`.
- `backend/app/config.py` ahora valida en runtime que:
  - si el base URL apunta a Gemini, el modelo debe iniciar con `gemini-`;
  - si el base URL apunta a OpenAI, no puede usarse un modelo Gemini;
  - `OPENAI_MODEL` y `OPENAI_BASE_URL` deben ser explícitos en producción;
  - `OPENAI_TIMEOUT_SECONDS` debe quedar entre 5 y 60;
  - `AUTOPILOT_MAX_AUTOFIX_ROUNDS` no puede pasar de 2.
- `backend/scripts/preflight_check.py` y `backend/scripts/validate_render_env.py` reutilizan esta validación.

### 2. Timeout/autopilot protegido

- `AUTOPILOT_MAX_AUTOFIX_ROUNDS=2` queda definido en Render.
- El schema de autopilot limita `max_autofix_rounds` a `le=2`.
- El handler también clampa cualquier valor pedido por el cliente contra `settings.autopilot_max_autofix_rounds`.
- La llamada al proveedor IA usa `settings.openai_timeout_seconds` en vez de un literal disperso.
- `GUNICORN_TIMEOUT_SECONDS=120` queda definido en Render y en `bootstrap.sh`.
- `bootstrap.sh` usa `--timeout ${GUNICORN_TIMEOUT_SECONDS}` para evitar drift entre YAML y comando real.

### 3. Memoria/plan Render protegido

- `waos-api` queda en `plan: standard`.
- `waos-worker` queda en `plan: starter`.
- `WEB_CONCURRENCY` queda en `1` en Render y como default de `bootstrap.sh` para evitar OOM con el standard inicial.
- `deploy_guard.py` falla si alguien cambia esos planes o sube concurrencia sin actualizar el presupuesto.

### 4. Build gate protegido

- Se agregó `scripts/deploy-verify.sh` para correr una verificación local completa antes de deploy:
  - deploy guard;
  - compile Python crítico;
  - tests de hardening;
  - frontend env validation;
  - cleanup stale Bot Studio;
  - `npm ci`;
  - `npm run typecheck`;
  - `npm run build`.
- Se agregó `.github/workflows/deploy-guard.yml` para bloquear PR/push si se rompe el guard o el build frontend.

### 5. Migraciones con orden determinístico

- Se mantiene `005b_whatsapp_anti_blocking_guardrails.sql`.
- `backend/scripts/run_migrations.py` ahora usa `migration_sort_key()` y `list_migrations()` para ordenar por número + sufijo.
- El runner falla si detecta nombres de migración inválidos o prefijos duplicados.
- `deploy_guard.py` falla si reaparece `005_whatsapp_anti_blocking_guardrails.sql`.

## Archivos principales modificados/agregados

- `render.yaml`
- `backend/render.yaml`
- `backend/scripts/bootstrap.sh`
- `backend/scripts/deploy_guard.py` nuevo
- `backend/scripts/run_migrations.py`
- `backend/scripts/run_ci_checks.sh`
- `backend/scripts/preflight_check.py`
- `backend/scripts/validate_render_env.py`
- `backend/app/config.py`
- `backend/app/vertical_onboarding_ai_prefill.py`
- `backend/app/schemas/onboarding.py`
- `backend/app/application/onboarding_handlers/commands.py`
- `backend/tests/test_deploy_hardening_guardrails.py` nuevo
- `scripts/deploy-verify.sh` nuevo
- `.github/workflows/deploy-guard.yml` nuevo

## Validaciones ejecutadas en este sandbox

Pasaron correctamente:

```bash
/usr/bin/python3 backend/scripts/deploy_guard.py
PYTHONPATH=. /usr/bin/python3 -m unittest backend.tests.test_deploy_hardening_guardrails -v
/usr/bin/python3 -m py_compile backend/app/config.py backend/app/vertical_onboarding_ai_prefill.py backend/app/schemas/onboarding.py backend/app/application/onboarding_handlers/commands.py backend/scripts/deploy_guard.py backend/scripts/preflight_check.py backend/scripts/validate_render_env.py backend/scripts/run_migrations.py
APP_ENV=production ... /usr/bin/python3 scripts/validate_render_env.py
node frontend/scripts/validate-env.mjs
node frontend/scripts/clean-stale-botstudio.mjs
```

No se pudo completar en este sandbox:

```bash
cd frontend
npm ci
npm run typecheck
npm run build
```

Motivo: `npm ci` se quedó en timeout en el sandbox y no creó `node_modules`. El proyecto queda preparado para que esos comandos corran en tu máquina, Vercel Preview o GitHub Actions con red normal.

## Comando recomendado antes de deploy real

```bash
./scripts/deploy-verify.sh
```

Luego configura en Render la Google AI API key en `OPENAI_API_KEY` y ejecuta el deploy.
