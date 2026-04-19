# WAOS Go-Live Checklist - Render + Vercel

## Render backend
- [ ] `DATABASE_URL` configurada y apuntando a PostgreSQL
- [ ] `APP_ENV=production`
- [ ] `PUBLIC_APP_URL` con dominio final del frontend
- [ ] `API_BASE_URL` con dominio final del backend
- [ ] `CORS_ALLOWED_ORIGINS` incluye el frontend final
- [ ] `ALLOWED_HOSTS` incluye el backend final
- [ ] `APP_SECRET` rotado
- [ ] `SECRET_ENCRYPTION_KEY` rotado
- [ ] `META_VERIFY_TOKEN` rotado si hay WhatsApp/Meta
- [ ] `AUTO_RUN_MIGRATIONS=true` solo en web service
- [ ] worker con `AUTO_RUN_MIGRATIONS=false`
- [ ] `python backend/scripts/validate_render_env.py` pasó
- [ ] `python backend/scripts/post_deploy_smoke.py` pasó

## Vercel frontend
- [ ] Root Directory = `frontend`
- [ ] `NEXT_PUBLIC_API_BASE_URL` configurada
- [ ] `API_INTERNAL_URL` configurada
- [ ] `NEXT_PUBLIC_APP_URL` configurada
- [ ] `npm run build` pasa
- [ ] login carga
- [ ] inbox carga
- [ ] portal cliente carga
- [ ] agenda carga

## Operación
- [ ] bot principal responde
- [ ] health panel operativo
- [ ] control operativo WhatsApp responde con número autorizado
- [ ] vertical y subvertical correctas por tenant principal
- [ ] alertas operativas visibles
