# WAOS Release Candidate Handoff

## Objetivo
Dejar este release listo para despliegue en:
- **Vercel** para `frontend/`
- **Render** para `backend/` (web + worker)
- **PostgreSQL** como base única de runtime

Este documento consolida deploy, variables, smoke tests, rollback básico y criterios de salida.

## Arquitectura final de deploy
- **Frontend público:** Vercel con `Root Directory = frontend`
- **Backend API:** Render web service con `rootDir: backend`
- **Worker:** Render worker con `rootDir: backend`
- **DB:** PostgreSQL
- **Centro legal:** servido desde frontend embebido y backend público
- **Consentimientos:** persistidos en backend con auditoría

## Matriz de variables

### Render web
| Variable | Requerida | Ejemplo | Notas |
|---|---:|---|---|
| `DATABASE_URL` | Sí | `postgresql://...` | PostgreSQL solamente |
| `APP_ENV` | Sí | `production` | Debe quedar en producción |
| `APP_SECRET` | Sí | generado | Rotar y guardar |
| `SECRET_ENCRYPTION_KEY` | Sí | generado | Rotar y guardar |
| `PUBLIC_APP_URL` | Sí | `https://app.example.com` | Dominio final del frontend |
| `API_BASE_URL` | Sí | `https://api.example.com` | Dominio final del backend |
| `CORS_ALLOWED_ORIGINS` | Sí | `https://app.example.com` | Puede ser CSV |
| `ALLOWED_HOSTS` | Sí | `api.example.com` | Host del backend |
| `AUTO_RUN_MIGRATIONS` | Sí | `true` | Solo en web |
| `SECURE_COOKIES` | Sí | `true` | Producción |
| `TRUST_PROXY_HEADERS` | Recomendada | `false` | Mantener salvo necesidad inversa |
| `OPENAI_API_KEY` | Recomendada | secreto | Degrada si falta |
| `OPENAI_MODEL` | Recomendada | `gemini-3-flash-preview` | Valor actual del release |
| `OPENAI_BASE_URL` | Recomendada | `https://generativelanguage.googleapis.com/v1beta/openai/` | Valor actual del release |
| `META_VERIFY_TOKEN` | Recomendada | secreto | Si aplica WhatsApp/Meta |
| `SENTRY_DSN` | Recomendada | secreto | Observabilidad |
| `DEFAULT_TIMEZONE` | Recomendada | `America/Mexico_City` | Alineado con operación |
| `LOG_LEVEL` | Recomendada | `INFO` | Producción |

### Render worker
Mismas variables base del web, más:

| Variable | Requerida | Valor |
|---|---:|---|
| `AUTO_RUN_MIGRATIONS` | Sí | `false` |
| `WORKER_MODE` | Sí | `loop` |
| `WORKER_POLL_SECONDS` | Sí | `5` |
| `WORKER_BATCH_SIZE` | Sí | `50` |

### Vercel frontend
| Variable | Requerida | Ejemplo | Notas |
|---|---:|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Sí | `https://api.example.com` | Usada en cliente |
| `API_INTERNAL_URL` | Sí | `https://api.example.com` | Usada del lado servidor |
| `NEXT_PUBLIC_APP_URL` | Sí | `https://app.example.com` | URL pública del frontend |
| `API_BASE_URL` | Recomendada | `https://api.example.com` | Ayuda a coherencia interna |
| `API_TIMEOUT_MS` | Recomendada | `12000` | Valor actual |
| `API_RETRIES` | Recomendada | `1` | Valor actual |
| `SECURE_COOKIES` | Recomendada | `true` | Producción |

## Orden exacto de despliegue

### 1) Render: base de datos
- Crear la base `waos-postgres` o conectar una existente.
- Verificar que `DATABASE_URL` apunte a PostgreSQL.

### 2) Render: backend web
- Usar `render.yaml` desde la raíz.
- Confirmar `healthCheckPath: /livez`.
- Confirmar `AUTO_RUN_MIGRATIONS=true`.
- Ejecutar validación de entorno:

```bash
python backend/scripts/validate_render_env.py
```

### 3) Render: worker
- Desplegar después del backend web.
- Confirmar `AUTO_RUN_MIGRATIONS=false`.
- Confirmar que comparte `APP_SECRET` y `SECRET_ENCRYPTION_KEY` con el web.

### 4) Vercel: frontend
- Importar repo.
- Definir `Root Directory = frontend`.
- Cargar las variables del frontend.
- El build valida envs automáticamente.

## Smoke tests obligatorios post-deploy

### Backend público
```bash
curl -fsS https://api.example.com/livez
curl -fsS https://api.example.com/healthz
curl -fsS https://api.example.com/readyz
curl -fsS https://api.example.com/api/v1/system/deploy-checklist
curl -fsS https://api.example.com/api/public/legal/docs
curl -fsS https://api.example.com/api/public/legal/subprocessors
```

### Smoke autenticado opcional
```bash
BASE_URL=https://api.example.com \
SMOKE_EMAIL=admin@example.com \
SMOKE_PASSWORD='***' \
python backend/scripts/post_deploy_smoke.py
```

### Frontend manual
Revisar visualmente:
- `/login`
- `/legal`
- `/policies`
- inbox
- agenda
- portal cliente
- banner de cookies

## Criterios go / no-go

### Go
- `/livez` responde 200
- `/healthz` responde 200
- `/api/v1/system/deploy-checklist` responde `ok` o `degraded`
- `/api/public/legal/docs` responde 200
- frontend compila con envs productivos
- login y rutas críticas cargan
- worker inicia sin intentar migrar

### No-go
- `DATABASE_URL` no es PostgreSQL
- `ALLOWED_HOSTS` no incluye el host del backend
- `CORS_ALLOWED_ORIGINS` no incluye el frontend
- `AUTO_RUN_MIGRATIONS` activo en worker
- frontend depende de rutas o archivos fuera de `frontend/`
- centro legal o consentimientos fallan públicamente

## Rollback rápido
- Mantener el deployment previo en Vercel y Render como referencia inmediata.
- Si falla el frontend, redeploy del build anterior y conservar backend estable.
- Si falla el backend, revertir a la versión previa de Render y verificar migraciones aplicadas.
- No revertir DB sin plan explícito si ya hubo escrituras de producción.

## Preflight local recomendado
```bash
bash scripts/release_candidate_smoke.sh
```

Ese script valida:
- compilación Python básica
- coherencia mínima de envs backend
- coherencia mínima de envs frontend
- presencia de rutas críticas frontend

## Archivos fuente de apoyo
- `DEPLOY.md`
- `docs/WAOS_GO_LIVE_CHECKLIST_RENDER_VERCEL.md`
- `docs/WAOS_PRODUCTION_DEPLOY_RENDER_VERCEL.md`
- `backend/.env.example`
- `frontend/.env.production.example`
- `docs/WAOS_RELEASE_VALIDATION_RC.md`
