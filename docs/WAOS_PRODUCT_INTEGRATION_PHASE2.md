# WAOS Product Integration - Phase 2

Este documento resume los cambios implementados en la fase 2 sobre el zip `waos-updated-phase1.zip`.

## Alcance implementado

### 1) Inbox y operación humana
- Colas de trabajo por rol derivadas (`sales`, `support`, `appointments`, `billing`) desde señales reales de la conversación.
- SLA visual calculado por conversación con:
  - `sla_status`
  - `sla_due_at`
  - `sla_target_minutes`
  - `sla_overdue_minutes`
- Endpoint de decision support por conversación con:
  - `next_best_action`
  - `priority_score`
  - `confidence_score`
  - explicación resumida de decisión
  - flags de riesgo
- Persistencia de snapshots de explicación en `bot_decision_explanations`.

### 2) CRM y conversión comercial
- Resumen de pipeline comercial nativo vía `GET /api/v1/crm/pipeline-summary`.
- Resumen de funnel vía `GET /api/v1/crm/funnel-summary`.
- Historial de cambios de etapa en `lead_stage_history` al modificar un lead.
- Integración visible del pipeline en `frontend/app/business-hub/page.tsx`.

### 3) Integraciones y ecosistema
- Centro de integraciones vía `GET /api/v1/integrations/center` con:
  - resumen por estado
  - sync runs recientes
  - receipts fallidos
  - retry hotspots
  - dependency map
- Replay seguro de webhook fallido vía `POST /api/v1/integrations/webhooks/{receipt_id}/replay`.
- En esta fase el replay es **dry-run** y queda auditado/persistido en `integration_replay_requests`.

### 4) Frontend
- Inbox:
  - resumen de colas
  - badges de SLA
  - chips de cola de trabajo
  - panel de decision support
- Integrations:
  - control tower inicial
  - tabla de retry hotspots
  - tabla de receipts fallidos con acción de replay dry-run
- Business Hub:
  - cards de pipeline weighted
  - stages
  - lost reasons
  - recent stage changes

## Nuevas estructuras de datos
- `work_queue_definitions`
- `bot_decision_explanations`
- `lead_stage_history`
- `integration_replay_requests`

## Endpoints agregados
- `GET /api/v1/inbox/queues`
- `GET /api/v1/conversations/{conversation_id}/decision-support`
- `GET /api/v1/crm/pipeline-summary`
- `GET /api/v1/crm/funnel-summary`
- `GET /api/v1/integrations/center`
- `POST /api/v1/integrations/webhooks/{receipt_id}/replay`

## Validación realizada
- `pytest -q backend/tests/test_activation_foundations.py` ✅

## Limitaciones intencionales de esta fase
- El replay de webhooks se deja en modo `dry_run=true` por defecto para no introducir side effects no controlados.
- Las colas de trabajo todavía son derivadas, no un sistema completo de ownership persistente.
- El decision support es explainable y útil, pero aún no es un motor de policy/risk hard-blocking.
- El pipeline comercial entra como summary operativo; el board CRM completo y stages verticales siguen para fase posterior.

## Siguiente fase sugerida
1. Ownership persistente y auto-assignment real en inbox.
2. Simulador de conversaciones + diff/versionado más fuerte del bot.
3. Pipeline board completo por vertical.
4. Integration replay no dry-run con idempotencia reforzada.
5. Capacity model y scheduling avanzado.
