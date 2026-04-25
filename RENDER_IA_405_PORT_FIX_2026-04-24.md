# Render IA / 405 / Port Binding Fix - 2026-04-24

Este paquete deja el deploy mas blindado para el flujo de IA del wizard.

## Que se corrigio

1. **Frontend Next en Render con `$PORT`**
   - `frontend/package.json` ahora usa `next start -H 0.0.0.0 -p ${PORT:-3000}`.
   - Esto evita que Render marque `Port scan timeout reached, no open ports detected` cuando el frontend se corre como Web Service.

2. **Blueprint Render incluye frontend como Web Service**
   - `render.yaml` y `backend/render.yaml` ahora incluyen `waos-frontend` como `type: web`, no como Static Site.
   - Las rutas internas de Next (`/api/onboarding/wizard/...`) requieren servidor Next; no funcionan bien como sitio estatico.

3. **Endpoints IA con diagnostico explicito**
   - `/api/onboarding/wizard/ai-prefill` y `/api/onboarding/wizard/ai-autopilot` ahora responden con JSON claro si alguien los abre con `GET`.
   - El metodo valido para ejecutar IA sigue siendo `POST`.

## Como desplegar

### Render Blueprint recomendado

Usa el `render.yaml` de la raiz. Debe crear o actualizar:

- `waos-api` -> Web Service Python
- `waos-worker` -> Background Worker Python
- `waos-frontend` -> Web Service Node/Next
- `waos-postgres` -> Postgres

### Variables obligatorias

En `waos-api`:

```env
PUBLIC_APP_URL=https://TU-FRONTEND.onrender.com
API_BASE_URL=https://TU-API.onrender.com
CORS_ALLOWED_ORIGINS=https://TU-FRONTEND.onrender.com
ALLOWED_HOSTS=TU-API.onrender.com
OPENAI_API_KEY=TU_GEMINI_API_KEY
OPENAI_MODEL=gemini-2.0-flash
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
META_VERIFY_TOKEN=un-token-largo-random
```

En `waos-frontend`:

```env
NEXT_PUBLIC_APP_URL=https://TU-FRONTEND.onrender.com
NEXT_PUBLIC_API_BASE_URL=https://TU-API.onrender.com
API_INTERNAL_URL=https://TU-API.onrender.com
API_BASE_URL=https://TU-API.onrender.com
```

## Verificacion rapida

Abre logs de `waos-api`, presiona el boton de IA y busca una de estas lineas:

```txt
POST /api/v1/onboarding/wizard/ai-prefill
POST /api/v1/onboarding/wizard/ai-autopilot
```

Si no aparece nada en `waos-api`, el problema esta en el frontend o en variables `API_INTERNAL_URL` / `API_BASE_URL`.

Si aparece `GET /livez 200`, eso solo confirma que el healthcheck del API esta vivo; no prueba el flujo de IA.

## Importante

- `waos-worker` debe ser **Background Worker**, no Web Service.
- `waos-frontend` debe ser **Web Service**, no Static Site.
- El error `Method Not Allowed` al abrir la URL directo en el navegador es normal porque esa accion requiere `POST`.
