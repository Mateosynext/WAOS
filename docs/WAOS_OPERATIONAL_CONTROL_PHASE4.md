# WAOS phase 4 — control operativo por WhatsApp y agenda self-service

Esta fase agrega una base funcional para operar agenda y estado del bot desde portal cliente y WhatsApp autorizado.

## Qué quedó implementado
- números autorizados por bot:
  - `GET/POST /api/v1/client/operations/authorized-numbers`
- resumen operativo:
  - `GET /api/v1/client/operations/summary`
  - `GET /api/v1/client/operations/availability`
- comandos operativos:
  - `POST /api/v1/client/operations/commands/preview`
  - `POST /api/v1/client/operations/commands`
  - `POST /api/v1/client/operations/commands/{command_id}/confirm`
  - `POST /api/v1/client/operations/commands/{command_id}/cancel`
- interceptación de WhatsApp para números autorizados dentro de `InboundService`
- ejecución inicial de comandos:
  - bloquear horarios
  - vacaciones
  - avisar próxima cita / citas afectadas
  - pausar, apagar, reiniciar, solo humano, reactivar
  - mensaje temporal
  - schedule de cambio de estado
  - preview de impacto
  - cancelar último comando pendiente

## Tablas nuevas
- `authorized_operational_numbers`
- `operational_command_requests`
- `operational_command_impacts`
- `availability_overrides`
- `vacation_periods`
- `appointment_notification_batches`
- `appointment_notification_targets`
- `mass_reschedule_batches`
- `mass_reschedule_items`
- `bot_operational_state_history`
- `scheduled_operational_actions`
- `bot_temp_messages`
- `operational_undo_tokens`

## Limitaciones de esta fase
- parser rule-first, todavía no usa extraction asistida por LLM con JSON estricto
- scheduler queda registrado en `automation_jobs`, pero no se añadió un worker dedicado nuevo en esta fase
- reschedule masivo directo soporta estrategia simple por desplazamiento, no matching avanzado por capacidad multi-recurso
- las notificaciones quedan registradas y encoladas en mensajes/snapshots, no se implementó un despachador provider-specific nuevo en esta fase

## Frontend
- nueva sección cliente: `/client/operaciones`
- comando libre con modo simulación o ejecución
- alta rápida de número autorizado
- lista de comandos recientes con confirmar/cancelar
- lectura básica de disponibilidad del día
