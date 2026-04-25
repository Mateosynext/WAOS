# Deploy limpio: backend en Render, frontend en Vercel

Este paquete esta preparado para separar plataformas:

- `backend/` -> **Render**
- `frontend/` -> **Vercel**

No despliegues el frontend en Render si ya lo tienes en Vercel. El `render.yaml` de este paquete crea solo backend, worker y base de datos.

## Backend en Render

Usa el `render.yaml` desde la raiz del repo. Debe crear o actualizar:

- `waos-api` -> Render Web Service Python
- `waos-worker` -> Render Background Worker Python
- `waos-postgres` -> Render Postgres

### Archivos clave

- `render.yaml`
- `backend/render.yaml`
- `backend/.env.render.example`
- `backend/scripts/validate_render_env.py`
- `backend/scripts/post_deploy_smoke.py`

### Variables minimas en `waos-api`

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

`DATABASE_URL`, `APP_SECRET` y `SECRET_ENCRYPTION_KEY` quedan gestionados por el blueprint cuando usas `render.yaml`.

## Frontend en Vercel

Crea o actualiza el proyecto de Vercel con:

- Root Directory: `frontend`
- Install Command: `npm ci`
- Build Command: `npm run build`

### Archivos clave

- `frontend/vercel.json`
- `frontend/.env.production.example`
- `frontend/.vercelignore`
- `frontend/scripts/validate-env.mjs`

### Variables minimas en Vercel

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

## Verificacion del flujo IA

1. Abre Render -> `waos-api` -> Logs.
2. En Vercel abre tu app y presiona el boton de IA.
3. En logs de Render deberia aparecer una de estas rutas:

```txt
POST /api/v1/onboarding/wizard/ai-prefill
POST /api/v1/onboarding/wizard/ai-autopilot
```

Si solo ves `GET /livez 200`, eso solo confirma que el API esta vivo; no prueba que el frontend este llamando al backend.

Si no aparece ningun `POST` de IA en Render, revisa las variables de Vercel: `API_INTERNAL_URL`, `API_BASE_URL` y `NEXT_PUBLIC_API_BASE_URL`.
