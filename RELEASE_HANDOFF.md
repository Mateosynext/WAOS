# WAOS Release Handoff - Vercel + Render

Este archivo es la ruta única de despliegue para este release candidate.

## Qué desplegar
- **Frontend:** `frontend/` en Vercel
- **Backend API:** `backend/` en Render web service
- **Worker:** `backend/` en Render worker
- **Base de datos:** PostgreSQL administrado por Render


## Higiene obligatoria del paquete
- no subir `backend/.waos-local.db` ni ninguna otra SQLite local
- no subir `frontend/tsconfig.tsbuildinfo`
- no subir PDFs generados en `backend/app/artifacts/reports/`
- el directorio de reportes debe viajar vacío con `.gitkeep`

## Orden recomendado
1. Crear o verificar la base PostgreSQL en Render.
2. Configurar variables del backend web.
3. Configurar variables del worker.
4. Desplegar backend web en Render.
5. Esperar migraciones y validar `/livez`, `/healthz`, `/readyz`.
6. Desplegar worker en Render.
7. Configurar variables del frontend en Vercel.
8. Desplegar frontend en Vercel.
9. Ejecutar smoke tests públicos y funcionales.
10. Hacer revisión final legal y de operación.

## Render: backend web
Usar `render.yaml` desde la raíz.

Variables mínimas obligatorias:
- `DATABASE_URL`
- `APP_ENV=production`
- `APP_SECRET`
- `SECRET_ENCRYPTION_KEY`
- `PUBLIC_APP_URL`
- `API_BASE_URL`
- `CORS_ALLOWED_ORIGINS`
- `ALLOWED_HOSTS`
- `AUTO_RUN_MIGRATIONS=true`
- `SECURE_COOKIES=true`

Variables recomendadas:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `META_VERIFY_TOKEN`
- `SENTRY_DSN`
- `TRUST_PROXY_HEADERS=false`
- `DEFAULT_TIMEZONE=America/Mexico_City`

## Render: worker
Clonar configuración de entorno del backend salvo:
- `AUTO_RUN_MIGRATIONS=false`
- `WORKER_MODE=loop`
- `WORKER_POLL_SECONDS=5`
- `WORKER_BATCH_SIZE=50`

## Vercel: frontend
- Root Directory: `frontend`
- Framework: Next.js

Variables mínimas obligatorias:
- `NEXT_PUBLIC_API_BASE_URL`
- `API_INTERNAL_URL`
- `NEXT_PUBLIC_APP_URL`

Variables recomendadas:
- `API_BASE_URL`
- `API_TIMEOUT_MS=12000`
- `API_RETRIES=1`
- `SECURE_COOKIES=true`

## Smoke tests mínimos post-deploy
Backend:
```bash
curl -fsS https://api.example.com/livez
curl -fsS https://api.example.com/healthz
curl -fsS https://api.example.com/readyz
curl -fsS https://api.example.com/api/v1/system/deploy-checklist
curl -fsS https://api.example.com/api/public/legal/docs
curl -fsS https://api.example.com/api/public/legal/subprocessors
```

Frontend:
- `/login`
- `/legal`
- `/policies`
- inbox
- agenda
- portal cliente

## Verificación local antes de subir
```bash
bash scripts/release_candidate_smoke.sh
python scripts/release_gate.py dist/waos_runtime_<version>-clean-release.zip --profile runtime
```

## Documento detallado
La guía paso a paso, con matriz de variables y criterios go/no-go, está en:
- `docs/WAOS_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/WAOS_RELEASE_VALIDATION_RC.md`


## WhatsApp anti-blocking hardening
- defensive rate limiting for outbound sends
- pre-send content guardrails
- persistent opt-out suppression list
- quality red auto-pause webhook
