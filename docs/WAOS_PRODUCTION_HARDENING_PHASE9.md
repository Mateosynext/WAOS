# WAOS Production Hardening - Phase 9

## Objetivo
Cerrar la última milla de despliegue para Render + Vercel con validación de entorno, liveness/readiness diferenciados y eliminación de dependencias duras a URLs productivas antiguas.

## Cambios clave
- Nuevo endpoint `GET /livez` para liveness puro sin dependencia de base de datos.
- Nuevo endpoint `GET /api/v1/system/deploy-checklist` con checklist verificable de despliegue.
- `render.yaml` y `backend/render.yaml` usan `healthCheckPath: /livez`.
- El worker deja `AUTO_RUN_MIGRATIONS=false` para evitar carreras de migración al arrancar en Render.
- `frontend/app/lib/env.ts` ya no trae fallbacks hardcodeados a un dominio productivo específico.
- `frontend/scripts/validate-env.mjs` obliga envs correctos en build productivo.
- `backend/scripts/validate_render_env.py` valida coherencia entre `PUBLIC_APP_URL`, `API_BASE_URL`, `CORS_ALLOWED_ORIGINS` y `ALLOWED_HOSTS`.
- `backend/scripts/post_deploy_smoke.py` ahora valida `livez`, `healthz`, `readyz` y `deploy-checklist`.

## Decisiones de release
- Render debe usar el blueprint raíz o `backend/render.yaml`.
- Vercel debe configurarse con `Root Directory = frontend`.
- No usar fallbacks silenciosos a dominios de staging o proyectos viejos.
- `DATABASE_URL` sigue siendo obligatorio para producción.

## Checklist operativo
1. Crear base PostgreSQL en Render.
2. Configurar `PUBLIC_APP_URL` y `API_BASE_URL` reales.
3. Alinear `CORS_ALLOWED_ORIGINS` con `PUBLIC_APP_URL`.
4. Alinear `ALLOWED_HOSTS` con el host real del backend.
5. Rotar `APP_SECRET` y `SECRET_ENCRYPTION_KEY`.
6. Dejar `RUN_BOOTSTRAP_SEED=false`.
7. Ejecutar `python backend/scripts/validate_render_env.py`.
8. Ejecutar `python backend/scripts/post_deploy_smoke.py` contra el backend ya publicado.
9. En Vercel, configurar `NEXT_PUBLIC_API_BASE_URL`, `API_INTERNAL_URL` y `NEXT_PUBLIC_APP_URL`.
10. Confirmar que `npm run build` del frontend pasa sin fallbacks.


## Capa explícita de gobierno de WhatsApp

Se agregó una capa específica de policy engine para WhatsApp, separada del rate limiting genérico y conectada al worker de outbox.

### Qué gobierna ahora
- **Ventana real de 24h customer care**: el worker inspecciona el último inbound del cliente y decide si el canal permite free-form o exige template.
- **Selección automática free-form vs template**: si la ventana de 24h está cerrada y existe `template_fallback`, el runtime reescribe el envío a template automáticamente.
- **Bloqueo seguro fuera de policy**: si la ventana está cerrada y no existe template aprobado, el mensaje va a `dead_letter` con razón explícita de política.
- **Categorías y templates**: cada envío gobernado persiste `message_category`, `selected_template` y la razón operacional en `whatsapp_policy_decisions` y `outbox_messages.governance_json`.
- **Retry governance por error de Meta**: el runtime clasifica códigos de Meta (`130429`, `131048`, `190`, `131031`, etc.) en retryable vs non-retryable, con `retry_after_seconds` y efecto de salud del canal.
- **Salud del número y calidad del canal**: `whatsapp_numbers` ahora expone `quality_rating`, `quality_status`, `throughput_tier`, `provider_degraded_until`, `last_provider_error_code` y `last_provider_error_at`.
- **Visibilidad operacional**: nuevo endpoint `GET /api/v1/system/whatsapp-governance` con snapshot de números, throughput, decisiones recientes y degradación por provider.

### Resultado operacional
WAOS deja de tratar WhatsApp como un simple transporte. Ahora decide **qué puede mandar, cuándo puede mandarlo, si debe usar template, si debe reintentar, si debe frenar por degradación del provider y con qué riesgo operativo**.


## WhatsApp anti-blocking guardrails
- outbound rate limiting by verification status
- content safety validation before send
- opt-out suppression persistence
- quality-rating RED automatic pause
