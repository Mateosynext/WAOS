# Deploy rápido

> Este release es **PostgreSQL-only**. SQLite no forma parte del runtime de despliegue.

## Backend en Render
1. Usa `render.yaml` desde la raíz o `backend/render.yaml`.
2. Configura `DATABASE_URL`, `PUBLIC_APP_URL`, `API_BASE_URL`, `CORS_ALLOWED_ORIGINS`, `ALLOWED_HOSTS`, `APP_SECRET` y `SECRET_ENCRYPTION_KEY`.
3. El web service usa `healthCheckPath: /livez`.
4. El worker no debe correr migraciones (`AUTO_RUN_MIGRATIONS=false`).
5. Ejecuta `python backend/scripts/validate_render_env.py`.
6. Tras desplegar, ejecuta `python backend/scripts/post_deploy_smoke.py` contra la URL pública.

## Frontend en Vercel
1. Configura el proyecto con `Root Directory = frontend`.
2. Define `NEXT_PUBLIC_API_BASE_URL`, `API_INTERNAL_URL`, `NEXT_PUBLIC_APP_URL` y `API_TIMEOUT_MS`.
3. El build ya valida envs con `frontend/scripts/validate-env.mjs`.
4. Despliega con `frontend/vercel.json`.

## Go live
- Revisa `RELEASE_HANDOFF.md` primero.
- Revisa `docs/WAOS_GO_LIVE_CHECKLIST_RENDER_VERCEL.md`.
- Revisa `docs/WAOS_PRODUCTION_HARDENING_PHASE9.md`.
- Ejecuta `bash scripts/release_candidate_smoke.sh` antes de subir.


## Legal público y consentimientos
- El centro legal ya viaja embebido dentro de frontend; no depende de `docs/` en Vercel.
- Render expone `GET /api/public/legal/docs`, `GET /api/public/legal/docs/{slug}`, `GET /api/public/legal/subprocessors`, `POST /api/public/legal/consents/cookies` y `POST /api/public/legal/privacy-requests`.
- Si editas `docs/legal/public`, ejecuta `python scripts/sync_legal_assets.py` antes de desplegar para sincronizar frontend y backend.
