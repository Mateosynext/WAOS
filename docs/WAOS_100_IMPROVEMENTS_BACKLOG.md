# WAOS 100 Improvements Backlog

Se agregó este documento al repo para convertir las 100 mejoras en backlog real y versión controlada dentro del producto. La referencia de detalle se alinea al plan entregado: activación, inbox, IA/calidad, comercial, agenda, portal, verticales, integraciones, reliability y UX.

> Nota: en este zip se implementó la fase 1 de foundations y UX operativa. El resto queda trazado para sprints posteriores sin romper la arquitectura actual.

## 10) Capa de aprendizaje por outcomes, no solo por prompts

### Problema

WAOS ya tiene experiments y reviews. Eso es valioso, pero todavía no existe un closed loop fuerte que aprenda de resultados de negocio y operación de punta a punta.

Hoy el sistema puede medir piezas aisladas.

Lo que falta es que esos resultados alimenten de forma consistente y auditable la evolución de:

- prompts
- flows
- policies
- routing
- playbooks
- templates
- timing
- tone
- next-best-action

### Señales que deben entrar al loop

- reply rate
- booking rate
- payment rate
- show rate
- refund rate
- escalation rate
- CSAT / NPS
- operator edits
- takeover frequency
- template performance
- delivery / read data
- lost reasons

### Qué debe construir el producto

1. **Outcome ledger** unificado por conversación, lead, booking, payment y operador.
2. **Attribution layer** para ligar outcomes a prompts, flows, templates, routing y acciones humanas.
3. **Learning scorecards** por componente operativo.
4. **Optimization control** para promover, degradar o bloquear configuraciones con guardrails.
5. **Auditoría completa** de por qué una configuración fue promovida, degradada o reemplazada.

### Resultado esperado

WAOS deja de optimizar solo respuestas o experimentos aislados y pasa a optimizar valor real:

- más conversación útil
- más booking efectivo
- más pago completado
- más asistencia real
- menos escalaciones tardías
- menos refunds
- menos corrección humana repetitiva

### Referencia detallada

- `docs/WAOS_OUTCOMES_CLOSED_LOOP.md`
- `docs/WAOS_OUTCOMES_CONTROL_PLANE.md`
- `backend/db/migrations/004_outcomes_closed_loop.sql`


## Added in current package
- WhatsApp anti-blocking hardening implemented in backend runtime, webhook handling and schema.
