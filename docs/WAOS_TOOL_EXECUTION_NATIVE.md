# WAOS Tool Execution Externa Nativa

Esta mejora convierte a WAOS de copiloto a operador digital para acciones operativas recurrentes.

## Acciones tipadas
- `book_appointment`
- `reschedule`
- `create_payment_link`
- `update_contact_stage`
- `send_receipt`

## Arquitectura
- **API unificada**: `/api/v1/tool-executions/preview`, `/execute`, `/runs`
- **Policies**: permiso por acción + confirmación obligatoria cuando aplica
- **Adapters**:
  - `waos_calendar`
  - `google_calendar`
  - `stripe_payments`
  - `waos_crm`
- **Idempotencia**: `job_idempotency_keys` evita ejecuciones duplicadas
- **Logs**: `tool_execution_runs` + `tool_execution_step_logs`

## Qué resuelve
- reservar o mover una cita sin salir del flujo
- generar links de cobro nativamente
- actualizar etapa de lead de forma operativa
- emitir comprobantes por WhatsApp

## Modelo de operación
1. Preview opcional
2. Confirmación explícita para acciones sensibles
3. Ejecución con adapter resuelto por integración
4. Persistencia del resultado, target y pasos ejecutados
5. Auditoría e idempotencia para replay seguro
