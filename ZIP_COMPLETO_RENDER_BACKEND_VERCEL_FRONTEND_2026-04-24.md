# ZIP completo - Render backend + Vercel frontend

Este ZIP contiene el proyecto completo: `backend/`, `frontend/`, `scripts/`, documentación y configuración.

Topología correcta:
- Render: `waos-api`, `waos-worker`, `waos-postgres`
- Vercel: `frontend/`

El `render.yaml` de este ZIP NO despliega `waos-frontend` en Render. El frontend sigue dentro del ZIP porque se debe subir/desplegar en Vercel.

Cambios blindados incluidos:
- Worker como `type: worker` en Render.
- Backend API como Web Service con healthcheck `/livez`.
- Variables IA/Gemini documentadas.
- Rutas IA del frontend con diagnóstico explícito para `GET`/405 y soporte `POST`.
- Documentación actualizada en `DEPLOY.md` y `RENDER_VERCEL_IA_405_PORT_FIX_2026-04-24.md`.
