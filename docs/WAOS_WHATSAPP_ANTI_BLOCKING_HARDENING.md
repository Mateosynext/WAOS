# WAOS WhatsApp Anti-Blocking Hardening

Este upgrade implementa controles concretos para reducir riesgo de bloqueo, degradación de quality rating y abuso operacional en Meta / WhatsApp Cloud API.

## Implementado

### 1. Defensive outbound rate limiting
- evaluación previa al send en `backend/app/whatsapp_governance.py`
- límites dependientes de verificación del negocio en `backend/app/whatsapp_safety.py`
- controles incluidos:
  - per-second
  - per-day
  - per-contact burst en ventana de 5 minutos
- resultado:
  - `retry` con `retry_after_seconds` cuando el envío debe frenarse
  - snapshot en `governance_json` para auditoría

### 2. 24h customer care window enforcement
- la lógica existente se mantiene y ahora queda combinada con los nuevos guardrails
- fuera de ventana:
  - texto libre se bloquea
  - se exige template aprobado o fallback aprobado

### 3. Content safety pre-send
- validación previa a enviar en `validate_message_content(...)`
- detecta:
  - shorteners sospechosos
  - clickbait explícito
  - urgencia agresiva / spam emojis
  - MLM / pirámides
  - restricciones verticales sensibles, por ejemplo dental / prescripción
- resultado:
  - `dead_letter` si el contenido debe bloquearse
  - `retry/review` si requiere revisión operativa

### 4. Opt-out persistente y suppression list
- nueva tabla `whatsapp_opt_outs`
- detección de keywords como:
  - STOP
  - baja
  - cancelar
  - no más
- cuando entra opt-out:
  - se registra la supresión
  - se congela la automatización en la conversación
  - se manda confirmación de baja
  - se evita ejecutar el pipeline de AI
- cuando existe supresión activa:
  - los envíos outbound quedan en `dead_letter`

### 5. Business verification-aware limits
- el sistema distingue números verificados vs no verificados desde `business_profile`
- impacto actual:
  - límites más estrictos para no verificados
  - exposición en governance snapshot
- esto deja preparado el terreno para sincronización automática contra Graph API si se desea endurecer onboarding

### 6. Quality rating red auto-pause
- nuevo webhook:
  - `POST /webhooks/whatsapp/{number_id}/quality`
- si Meta reporta `RED`:
  - `whatsapp_numbers.quality_rating = RED`
  - `quality_status = blocked`
  - `bots.ai_paused = 1`
  - conversaciones abiertas pasan a takeover / freeze

## Archivos principales
- `backend/app/whatsapp_safety.py`
- `backend/app/whatsapp_governance.py`
- `backend/app/application/inbound_service.py`
- `backend/app/api/handlers/webhooks.py`
- `backend/app/api/routers/webhooks.py`
- `backend/app/migrations.py`
- `backend/db/migrations/005_whatsapp_anti_blocking_guardrails.sql`

## Qué queda recomendado como siguiente capa
- sync real con Graph API para verificación y account health
- circuit breaker por número además del provider global
- dashboard de quality / opt-out / spam flags por bot
- export acelerado de conversaciones y playbook de migración entre números
- library de templates por vertical con coverage mínimo obligatorio
