# Render + Vercel IA / 405 / Port Fix - 2026-04-24

Este paquete esta ajustado para tu topologia real:

- Backend/API en **Render**
- Worker en **Render Background Worker**
- Base de datos en **Render Postgres**
- Frontend en **Vercel**

## Que se corrigio

1. **Render ya no despliega `waos-frontend`**
   - `render.yaml` y `backend/render.yaml` solo contienen `waos-api`, `waos-worker` y `waos-postgres`.
   - Esto evita crear un frontend duplicado en Render cuando el frontend oficial vive en Vercel.

2. **Worker queda como Background Worker**
   - El error `Port scan timeout reached, no open ports detected` es normal si un worker se crea como Web Service.
   - En este blueprint, `waos-worker` es `type: worker`, no `type: web`.

3. **API sigue blindada para Render**
   - `waos-api` corre como Web Service Python.
   - Healthcheck: `/livez`.
   - Start command: `bash scripts/bootstrap.sh`.

4. **Endpoints IA con diagnostico explicito**
   - `/api/onboarding/wizard/ai-prefill`
   - `/api/onboarding/wizard/ai-autopilot`
   - Si alguien abre esas rutas con `GET`, responden con JSON explicando que el metodo valido es `POST`.

## Variables de Render: `waos-api`

```env
PUBLIC_APP_URL=https://TU-FRONTEND.vercel.app
API_BASE_URL=https://TU-API.onrender.com
CORS_ALLOWED_ORIGINS=https://TU-FRONTEND.vercel.app
ALLOWED_HOSTS=TU-API.onrender.com
OPENAI_API_KEY=TU_GEMINI_API_KEY
OPENAI_MODEL=gemini-2.0-flash
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
META_VERIFY_TOKEN=un-token-largo-random
```

## Variables de Vercel: frontend

```env
NEXT_PUBLIC_APP_URL=https://TU-FRONTEND.vercel.app
NEXT_PUBLIC_API_BASE_URL=https://TU-API.onrender.com
API_INTERNAL_URL=https://TU-API.onrender.com
API_BASE_URL=https://TU-API.onrender.com
API_TIMEOUT_MS=30000
API_RETRIES=2
SECURE_COOKIES=true
WAOS_ALLOW_ENV_FALLBACK=false
```

## Verificacion rapida

En Render -> `waos-api` -> Logs, presiona el boton de IA en Vercel y busca:

```txt
POST /api/v1/onboarding/wizard/ai-prefill
POST /api/v1/onboarding/wizard/ai-autopilot
```

Si no aparece ningun `POST`, la request no esta llegando desde Vercel al backend. Revisa `API_INTERNAL_URL`, `API_BASE_URL`, `NEXT_PUBLIC_API_BASE_URL` y `CORS_ALLOWED_ORIGINS`.

Si aparece `GET /livez 200`, eso solo confirma que Render esta monitoreando el API correctamente.
