# Nota corregida: frontend en Vercel, backend en Render

La version correcta para tu deploy es:

- `waos-api` -> Render Web Service
- `waos-worker` -> Render Background Worker
- `waos-postgres` -> Render Postgres
- `frontend` -> Vercel

No despliegues `waos-frontend` en Render si tu frontend oficial esta en Vercel.

Consulta `RENDER_VERCEL_IA_405_PORT_FIX_2026-04-24.md` para la guia actualizada.
