# WAOS Agentic Runtime Upgrade

Esta mejora transforma el cerebro lineal `classify -> decide -> generate` en una ejecución más cercana a un agente operacional serio.

## Qué quedó implementado

1. **understanding**
   - se conserva la clasificación híbrida OpenAI + heurística + talento
   - la salida sigue trazando `classifier_source` y fallback chain

2. **grounding**
   - se arma contexto verificable desde business knowledge, memory vectors, knowledge embeddings y conversation checkpoints
   - cada turno deja `coverage` por tipo de claim (pricing, schedule, location, faq, payment, support)

3. **planning**
   - nuevo planner por objetivos con `tool_orchestration` explícita por intención
   - define `response_contract`, `verification_checks`, `risk_flags` y política de memoria

4. **action selection**
   - la decisión sigue siendo policy-aware, pero ahora hereda plan, riesgo y necesidad de verificación

5. **message rendering**
   - la generación recibe `execution_plan` y `grounded_context` como insumos explícitos

6. **verifier before send**
   - si detecta claims operativos sin soporte real (precio, horario, ubicación), reescribe a una respuesta segura en vez de enviar algo potencialmente inventado

7. **memory curator**
   - destila hechos durables por turno para que la persistencia posterior sea más intencional

8. **post-send evaluation**
   - calcula `quality_score`, groundedness y verification status para trazabilidad y future learning loops

## Archivos principales tocados

- `backend/app/agent_runtime.py`
- `backend/app/runtime_pipeline.py`
- `backend/app/ai.py`
- `backend/app/architecture.py`
- `backend/tests/test_agent_runtime_orchestration.py`

## Qué problema resuelve frente al feedback

Antes: el runtime estaba optimizado para clasificar, decidir y generar.

Ahora: existe una capa orquestadora explícita que separa:

- understanding
- planning
- grounding
- action selection
- message rendering
- safety / policy-aware verification
- memory curation
- post-send evaluation

## Limitaciones honestas

Esto ya deja al ZIP bastante más agentic, pero todavía no convierte el sistema en un agente fully autonomous con:

- tool execution externa real sobre calendarios / CRMs / payment providers en cada intención
- verifier semántico basado en modelo dedicado
- optimization control automático con promotion/demotion de variantes bajo guardrails
- ranking multi-candidato / self-play / debate before send

La base para eso ya quedó mucho más limpia y extensible.

## Próximo salto recomendado

La siguiente ventaja estructural para WAOS no es solo mejorar prompts, sino cerrar el aprendizaje por outcomes reales.

Eso implica unir experiments, reviews, operator edits, takeover behavior, template analytics, CRM outcomes, agenda outcomes y payment outcomes dentro de un loop auditable que pueda ajustar prompts, flows, routing, policies, templates, timing, tone y next-best-action.

Documento de referencia:

- `docs/WAOS_OUTCOMES_CLOSED_LOOP.md`
- `docs/WAOS_OUTCOMES_CONTROL_PLANE.md`
- `backend/db/migrations/004_outcomes_closed_loop.sql`
