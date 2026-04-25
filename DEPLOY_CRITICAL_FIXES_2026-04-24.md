# Deploy critical fixes — 2026-04-24

Se resolvieron los 5 bloqueos críticos antes de producción.

## 1. IA Gemini / OpenAI-compatible alineada

Archivos actualizados:
- `render.yaml`
- `backend/render.yaml`
- `backend/.env.example`
- `backend/.env.render.example`
- `backend/scripts/preflight_check.py`
- `backend/scripts/validate_render_env.py`

Configuración efectiva:

```yaml
OPENAI_MODEL: gemini-2.0-flash
OPENAI_BASE_URL: https://generativelanguage.googleapis.com/v1beta/openai/
OPENAI_API_KEY: sync:false en Render, para cargar tu Google AI API key como secreto
```

Mejora adicional: el preflight de backend y el validador de Render ahora detectan mismatch de proveedor/modelo para evitar fallback silencioso cuando `OPENAI_API_KEY` está configurada.

## 2. Timeout / autopilot autofix

Archivos actualizados:
- `backend/app/vertical_onboarding_ai_prefill.py`
- `backend/app/application/onboarding_handlers/commands.py`
- `backend/app/schemas/onboarding.py`
- `frontend/app/lib/data/wizard.ts`
- `frontend/app/api/onboarding/wizard/ai-autopilot/route.ts`
- `frontend/features/bot-studio/services/wizardApi.ts`
- `backend/scripts/bootstrap.sh`

Cambios:
- Default de `max_autofix_rounds` bajado de `3` a `2` en backend y frontend.
- Gunicorn `--timeout` subido de `90` a `120`.

## 3. Plan de Render

Archivos actualizados:
- `render.yaml`
- `backend/render.yaml`

Cambios:
- API `waos-api`: `plan: standard`
- Worker `waos-worker`: se mantiene en `plan: starter`

## 4. Build completo de Next.js

Validaciones ejecutadas en este entorno:

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL=https://api.example.com \
API_INTERNAL_URL=https://api.example.com \
NEXT_PUBLIC_APP_URL=https://app.example.com \
NODE_ENV=production \
node ./scripts/validate-env.mjs

node ./scripts/clean-stale-botstudio.mjs
```

Resultado:
- `[env:ok] frontend env validation passed`
- `[cleanup:ok] stale Bot Studio files are absent`

Pendiente fuera de este sandbox:
- `npm ci`, `npm run typecheck` y `npm run build` no pudieron completarse aquí porque la instalación de dependencias por `npm ci` quedó bloqueada/timeout sin crear `node_modules`.
- En tu máquina o Vercel Preview, corre el build completo con las variables reales de producción.

## 5. Migración 005 duplicada

Archivo renombrado:
- `backend/db/migrations/005_whatsapp_anti_blocking_guardrails.sql`
- a `backend/db/migrations/005b_whatsapp_anti_blocking_guardrails.sql`

Se preserva el orden actual esperado:
1. `005_tool_execution_native.sql`
2. `005b_whatsapp_anti_blocking_guardrails.sql`
3. `006_tool_execution_outcomes_flywheel.sql`

También se actualizó la referencia en `README.md`.

## Validaciones adicionales ejecutadas

```bash
python -S -m py_compile \
  backend/app/vertical_onboarding_ai_prefill.py \
  backend/app/application/onboarding_handlers/commands.py \
  backend/app/schemas/onboarding.py \
  backend/app/config.py \
  backend/scripts/preflight_check.py \
  backend/scripts/validate_render_env.py
```

Resultado:
- `[OK] py_compile modified backend files`

Checks manuales:
- Ya no aparece `gemini-3-flash-preview` en los archivos de deploy/env tocados.
- Ya no aparece `--timeout 90` en `bootstrap.sh`.
- El archivo antiguo de migración `005_whatsapp_anti_blocking_guardrails.sql` ya no existe.
