# WAOS Multi-agent Intent Orchestration

## Objetivo
Separar el runtime generalista en especialistas por intención para subir precisión, aislar reglas de riesgo y medir performance por objetivo operacional.

## Qué quedó implementado
- `intent_router_v1` que enruta cada conversación a un agente especialista.
- agentes especialistas: `booking`, `sales`, `support`, `collections`, `recovery`, `retention` y `general`.
- memoria compartida `shared_memory_v1` con contexto de:
  - `contact_memory`
  - citas recientes
  - pagos recientes
  - estado de lead
  - outcomes recientes
  - ejecuciones operativas recientes
- `specialist_supervisor_v1` que revisa riesgo, puede forzar handoff y deja trazabilidad de escalamiento.
- persistencia de routing en `agent_routing_runs`.
- exposures de outcomes con dimensiones nuevas:
  - `specialist_agent_key`
  - `specialist_agent_version`
  - `specialist_prompt_id`
  - `intent_family`
  - `agent_routing_run_id`
- scorecards de outcomes por `specialist_agent` usando la misma capa de closed loop.

## Superficies nuevas
- `POST /api/v1/agent-orchestration/route`
- `GET /api/v1/agent-orchestration/specialists`
- `GET /api/v1/agent-orchestration/conversations/{conversation_id}`

## Runtime integrado
La orquestación agentic existente ahora agrega:
- `specialist_route`
- `shared_memory`
- `supervisor`
- plan enriquecido con `specialist`
- decisión final supervisada y trazable

## Tablas nuevas
- `agent_routing_runs`

## Migración
- `backend/db/migrations/007_multi_agent_intent_router.sql`
- `2026-04-17-phase17-multi-agent-intent-router-v1`

## Archivos clave
- `backend/app/multi_agent_runtime.py`
- `backend/app/application/agent_orchestration_service.py`
- `backend/app/api/routers/agent_orchestration.py`
- `backend/app/schemas/agent_orchestration.py`
- `backend/app/agent_runtime.py`
- `backend/app/ai.py`
- `backend/app/application/outcomes_service.py`

## Resultado
WAOS ya no decide como un solo agente generalista. Ahora enruta por intención, opera con especialistas separados, comparte memoria entre ellos, aplica supervisión explícita y puede medir outcomes por agente para iterar cada objetivo sin romper los demás.
