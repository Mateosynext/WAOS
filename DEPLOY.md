# Deploy rápido

> Este release es **PostgreSQL-only**. SQLite no forma parte del runtime de despliegue. Si ves SQLite en tests o scripts internos, no aplica al entorno objetivo.

## Backend
1. Copia `backend/.env.example` a tu configuración de entorno.
2. Configura `DATABASE_URL` con PostgreSQL **antes** de correr migraciones o bootstrap.
3. Mantén `RUN_BOOTSTRAP_SEED=false` salvo bootstrap controlado.
4. Ejecuta migraciones con `backend/scripts/run_migrations.py` o `backend/scripts/migrate.sh`.
5. Valida con `backend/scripts/preflight_check.py` y `backend/scripts/post_deploy_smoke.py`.

## Frontend
1. Configura `frontend/.env.production.example` en tu plataforma.
2. Asegura que `NEXT_PUBLIC_API_BASE_URL` apunte al backend productivo.
3. Despliega con la configuración incluida en `frontend/vercel.json`.
