# WAOS Agent Policy Engine

## Objetivo

Convertir la orquestación multi-agente en un runtime gobernado por especialista, con **policy profiles**, **budgets operativos**, **SLAs por intención** y **enforcement** conectados al router, a las tool actions y al closed loop.

Sin esta capa, cada specialist enruta mejor pero todavía opera con reglas blandas. Con esta capa, cada agent tiene límites explícitos, tiempos objetivo y criterios auditables para bloquear, advertir o escalar.

## Qué agrega

### 1. Policy profiles por specialist

Cada especialista ahora resuelve un profile nativo:

- `booking` → `booking_ops`
- `sales` → `sales_ops`
- `support` → `support_ops`
- `collections` → `collections_ops`
- `recovery` → `recovery_ops`
- `retention` → `retention_ops`
- `general` → `general_ops`

Cada profile define:

- `allowed_actions`
- `hard_limits`
- `soft_limits`
- `sla_targets`
- `escalation_rules`

Implementación principal:

- `backend/app/agent_policy_runtime.py`

## 2. Budgets operativos

El engine evalúa límites reales antes de permitir o bloquear acciones.

Ejemplos:

- `max_payment_links_per_contact_24h`
- `max_reschedules_per_contact_7d`
- `max_stage_updates_per_contact_24h`
- `max_receipts_per_payment_24h`
- `max_reactivation_actions_per_contact_7d`
- `max_retention_interventions_per_contact_7d`
- `max_routes_per_conversation_1h`
- `max_calendar_mutations_per_contact_24h`

La evaluación devuelve checks con estado:

- `ok`
- `warning`
- `blocked`

## 3. SLAs por intención

Cada specialist ahora opera con objetivos temporales explícitos:

- `first_response_seconds`
- `action_confirmation_seconds`
- `human_handoff_minutes`

El engine clasifica el estado SLA como:

- `healthy`
- `at_risk`
- `breached`
- `unknown`

La evaluación usa el contexto real de conversación y memoria compartida para calcular el anchor y el aging efectivo.

## 4. Enforcement real sobre el runtime

### Agent orchestration

`route_preview()` ahora:

- evalúa policy por specialist
- persiste `agent_policy_evaluations`
- adjunta la policy al route run
- propaga la policy al supervisor
- puede marcar `needs_review` o `handoff` cuando el enforcement o el SLA lo requieren

### Tool execution

`preview()` y `execute()` ahora:

- resuelven el specialist y su profile
- evalúan budgets + SLA + acción solicitada
- bloquean acciones no permitidas para ese specialist
- bloquean acciones cuando un budget duro ya se agotó
- dejan traza persistente del evaluation usado en el preview o execute

Ejemplo:

- un route `booking` no puede ejecutar `create_payment_link`
- un specialist `collections` sí puede, pero se bloquea si supera `max_payment_links_per_contact_24h`

## 5. Persistencia y trazabilidad

Nueva tabla:

- `agent_policy_evaluations`

Campos de policy ahora viven también en runtime tables:

- `agent_routing_runs.policy_profile_key`
- `agent_routing_runs.policy_profile_version`
- `agent_routing_runs.policy_evaluation_id`
- `agent_routing_runs.policy_json`
- `tool_execution_runs.policy_profile_key`
- `tool_execution_runs.policy_profile_version`
- `tool_execution_runs.policy_evaluation_id`
- `tool_execution_runs.policy_json`
- `outcome_exposures.policy_profile_key`
- `outcome_exposures.policy_profile_version`
- `outcome_exposures.policy_evaluation_id`

Migración:

- `backend/db/migrations/008_agent_policy_engine.sql`

## 6. Closed loop y scorecards

La capa de outcomes ahora puede atribuir también por:

- `policy_profile`

Eso habilita scorecards automáticos por profile además de:

- specialist agent
- prompt version
- flow
- template
- funnel stage
- vertical
- tool action / adapter / provider

Ejemplo de lectura operativa:

- `collections_ops` genera más revenue, pero entra en warning por budget con demasiada frecuencia
- `booking_ops` cumple SLA, pero fuerza handoff demasiado pronto
- `retention_ops` baja churn sin exceder límites de intervención

## API nueva

### Listar profiles

`GET /api/v1/agent-policy/profiles?organization_id=...`

### Evaluar policy

`POST /api/v1/agent-policy/evaluate`

Payload base:

```json
{
  "organization_id": "org_activation",
  "bot_id": "bot_activation",
  "specialist_agent_key": "collections",
  "conversation_id": "conv_policy_budget",
  "contact_id": "ct_policy_budget",
  "requested_action": "create_payment_link",
  "persist": true
}
```

## Archivos clave

- `backend/app/agent_policy_runtime.py`
- `backend/app/application/agent_policy_service.py`
- `backend/app/api/routers/agent_policy.py`
- `backend/app/schemas/agent_policy.py`
- `backend/app/application/agent_orchestration_service.py`
- `backend/app/application/tool_execution_service.py`
- `backend/app/application/outcomes_service.py`
- `backend/app/multi_agent_runtime.py`
- `backend/app/migrations.py`
- `backend/db/migrations/008_agent_policy_engine.sql`
- `backend/tests/test_agent_policy_engine.py`

## Resultado

WAOS ya no solo enruta a un agente correcto; ahora también **gobierna qué puede hacer, cuántas veces puede hacerlo, en cuánto tiempo debe responder y cuándo debe escalar**.

Eso convierte la orquestación multi-agente en un sistema operativo real con límites explícitos, enforcement y aprendizaje medible por profile.
