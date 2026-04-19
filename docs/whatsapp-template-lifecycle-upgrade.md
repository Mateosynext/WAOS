# WhatsApp Template Lifecycle Upgrade

## Qué se agregó

Se incorporó una capa real de lifecycle management para templates de WhatsApp, cubriendo:

- registry local de templates y versiones
- sync/publicación hacia Meta
- tracking de estados remotos y aprobación/rechazo
- versionado por template
- validación de idioma y categoría
- linting previo a publicación
- cobertura de variables y assets
- analytics por template y versión
- fallback automático cuando un template falla en provider o no está aprobado
- integración con governance y worker runtime

## Componentes principales

### Persistencia
Nuevas tablas:

- `whatsapp_templates`
- `whatsapp_template_versions`
- `whatsapp_template_sync_runs`
- `whatsapp_template_failovers`

### Dominio
Nuevo módulo:

- `backend/app/domains/whatsapp_templates.py`

Responsabilidades principales:

- crear templates y versiones
- linting estructural y de assets
- validación runtime de variables/componentes
- sync y polling de estado contra Meta
- analytics por template/version
- resolución de template aprobado/fallback
- recuperación automática ante errores tipo `template_invalid`

### API
Nuevas rutas:

- `POST /api/v1/whatsapp/templates/lint`
- `GET /api/v1/whatsapp/templates`
- `POST /api/v1/whatsapp/templates`
- `GET /api/v1/whatsapp/templates/{template_id}`
- `POST /api/v1/whatsapp/templates/{template_id}/versions`
- `POST /api/v1/whatsapp/templates/{template_id}/sync`
- `POST /api/v1/whatsapp/templates/{template_id}/sync-status`
- `GET /api/v1/whatsapp/templates/{template_id}/sync-status`
- `POST /api/v1/whatsapp/templates/{template_id}/approval`
- `GET /api/v1/whatsapp/templates/{template_id}/analytics`

### Runtime
Integraciones nuevas:

- `whatsapp_governance.py`
  - valida templates registrados
  - selecciona versión aprobada
  - activa fallback cuando corresponde
  - conserva passthrough para templates legacy no gestionados, evitando romper flujos existentes

- `worker.py`
  - detecta errores provider `template_invalid`
  - reescribe payload para retry con fallback automático
  - persiste eventos de failover

## Cobertura validada

Se agregaron pruebas enfocadas en:

- lifecycle completo con create/version/sync/status/approval/analytics
- fallback automático cuando el template pedido no está aprobado
- fallback automático cuando Meta rechaza el template en envío
- regresión del runtime normal del canal WhatsApp

Suites verificadas:

- `backend/tests/test_whatsapp_template_lifecycle.py`
- `backend/tests/test_whatsapp_channel_runtime.py`

## Nota de compatibilidad

Se mantuvo compatibilidad con templates legacy no registrados en el registry local para no quebrar envíos existentes. El enforcement fuerte aplica cuando el template ya está gestionado por esta nueva capa o cuando el runtime puede resolver un fallback administrado.
