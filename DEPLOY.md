# Deploy limpio: backend en Render, frontend en Vercel

Este paquete ya viene preparado para separar plataformas:
- `backend/` para **Render**
- `frontend/` para **Vercel**

## Backend en Render
Usa preferentemente `render.yaml` desde la raíz. El archivo ya apunta a `backend/` con `rootDir: backend`.

### Archivos clave
- `render.yaml`
- `backend/render.yaml`
- `backend/.env.render.example`
- `backend/scripts/validate_render_env.py`
- `backend/scripts/post_deploy_smoke.py`

### Variables mínimas
- `DATABASE_URL`
- `PUBLIC_APP_URL`
- `API_BASE_URL`
- `CORS_ALLOWED_ORIGINS`
- `ALLOWED_HOSTS`
- `APP_SECRET`
- `SECRET_ENCRYPTION_KEY`

## Frontend en Vercel
Crea un proyecto nuevo con `Root Directory = frontend`.

### Archivos clave
- `frontend/vercel.json`
- `frontend/.env.vercel.example`
- `frontend/.vercelignore`
- `frontend/scripts/validate-env.mjs`

### Build esperado
- Install: `npm ci`
- Build: `npm run build`

El paquete ya incluye `vercel-build` como alias de compatibilidad.
