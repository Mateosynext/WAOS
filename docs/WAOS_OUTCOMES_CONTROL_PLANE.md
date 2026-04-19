# WAOS Outcomes Control Plane

## Objetivo

Convertir la idea de aprendizaje por outcomes en una capacidad backend concreta, auditable y operable.

Esta capa no reemplaza experiments, reviews o analytics existentes. Los unifica en un loop cerrado con cinco piezas:

1. **event capture**
2. **attribution**
3. **scorecards**
4. **policy control**
5. **promotion / demotion / rollback**

---

## 1. Modelo operativo

El loop propuesto en backend queda así:

1. el runtime ejecuta una conversación con una configuración específica
2. se registran exposure facts de esa ejecución
3. llegan outcome events de mensajería, agenda, pagos, feedback y operación humana
4. un job de attribution liga outcomes a superficies controlables
5. se recalculan scorecards por componente
6. un policy engine decide recomendar, promover, degradar, limitar tráfico o bloquear
7. toda decisión deja audit trail y puede revertirse

---

## 2. Superficies controlables

Cada una debe ser tratada como una entidad optimizable:

- prompt version
- flow version
- playbook version
- template version
- routing rule
- timing policy
- tone family
- next-best-action policy
- escalation policy
- operator assist policy

El backend debe soportar que una conversación quede expuesta a varias de estas superficies a la vez.

Ejemplo:

- prompt `prompt_v23`
- flow `booking_flow_v8`
- template `reminder_tpl_v12`
- routing rule `premium_high_intent_human_fastlane`
- timing policy `evening_followup_mx`
- nba policy `collect_payment_before_booking`

---

## 3. Señales de outcome soportadas

### Comerciales
- reply rate
- booking rate
- payment rate
- conversion to closed won
- revenue per conversation
- lost reason distribution

### Agenda / asistencia
- show rate
- cancel rate
- reschedule rate
- no-show risk delta
- time-to-book

### Pago
- payment link opened
- payment completed
- payment failed
- refund rate
- recovery rate after failed payment

### Operación humana
- operator edits
- takeover frequency
- late takeover frequency
- escalation rate
- resolution SLA
- touches per conversation

### Experiencia
- CSAT
- NPS
- complaint / claim rate
- unblock rate after complaint

### Distribución / entrega
- delivered
- read
- read-to-reply
- template read decay
- channel failure rate

---

## 4. Componentes de datos mínimos

### A. Exposure fact

Tabla base para registrar qué configuración estuvo activa cuando el sistema actuó.

Campos clave:

- organization_id
- bot_id
- conversation_id
- contact_id
- lead_id
- message_id
- source_type (`runtime`, `template_send`, `followup_scheduler`, `human_copilot`)
- prompt_version_id
- flow_version_id
- template_version_id
- routing_rule_id
- timing_policy_id
- tone_policy_id
- nba_policy_id
- escalation_policy_id
- operator_id
- channel
- assigned_variant
- sent_at
- metadata_json

### B. Outcome event

Evento normalizado de negocio, experiencia u operación.

Campos clave:

- event_name
- event_category
- event_timestamp
- value_number
- value_text
- value_json
- source_system (`whatsapp`, `crm`, `calendar`, `payments`, `human_ops`, `feedback`)
- external_event_id
- status
- dedupe_key

### C. Attribution fact

Registro materializado que dice: este outcome se atribuye parcial o totalmente a estas superficies.

Campos clave:

- attributed_entity_type
- attributed_entity_id
- metric_name
- attribution_model
- attribution_weight
- attribution_window_hours
- outcome_event_id
- exposure_id
- contribution_value

### D. Scorecard snapshot

Agregado periódico listo para UI, auditoría y policy engine.

Campos clave:

- entity_type
- entity_id
- scorecard_window (`24h`, `7d`, `28d`)
- traffic_count
- primary_metric
- guardrail_metrics_json
- outcome_score
- confidence_score
- recommendation (`promote`, `hold`, `degrade`, `block`, `needs_review`)
- rationale_json

### E. Optimization decision log

Registro de la decisión operativa aplicada.

Campos clave:

- entity_type
- entity_id
- action (`promote`, `degrade`, `limit_traffic`, `rollback`, `block`, `recommend_only`)
- previous_state_json
- new_state_json
- decision_source (`policy_engine`, `manual_supervisor`, `auto_guardrail`)
- reason_code
- evidence_snapshot_json
- created_by
- created_at

---

## 5. API mínima propuesta

### Ingesta

#### `POST /api/v1/outcomes/events`
Registra eventos normalizados de outcome.

Payload ejemplo:

```json
{
  "organization_id": "org_123",
  "bot_id": "bot_1",
  "conversation_id": "conv_9",
  "contact_id": "contact_7",
  "event_name": "payment_completed",
  "event_category": "payment",
  "event_timestamp": "2026-04-17T18:22:00Z",
  "source_system": "payments",
  "external_event_id": "stripe_pi_123",
  "value_number": 1499,
  "value_text": "MXN",
  "value_json": {"payment_id": "pay_44"},
  "dedupe_key": "payments:stripe_pi_123:payment_completed"
}
```

#### `POST /api/v1/outcomes/exposures`
Registra exposición de conversación o mensaje a una configuración controlable.

#### `POST /api/v1/outcomes/operator-signals`
Registra edición humana, takeover, override o resolución manual.

### Consulta

#### `GET /api/v1/outcomes/scorecards`
Filtros:

- `entity_type`
- `entity_id`
- `window`
- `organization_id`
- `bot_id`
- `metric`

#### `GET /api/v1/outcomes/entities/{entity_type}/{entity_id}`
Detalle de scorecard, guardrails y evidencia.

#### `GET /api/v1/outcomes/decisions`
Histórico de promotion / demotion / rollback.

#### `GET /api/v1/outcomes/attribution`
Consulta de atribuciones por outcome, entidad y ventana.

### Control

#### `POST /api/v1/outcomes/recompute`
Recalcula scorecards para una organización o bot.

#### `POST /api/v1/outcomes/decisions/apply`
Aplica una decisión recomendada o manual.

#### `POST /api/v1/outcomes/decisions/{decision_id}/rollback`
Revierte una decisión aplicada.

---

## 6. Jobs y pipelines

### Job 1: normalize outcome events

Frecuencia: near-real-time o cada 1-5 min.

Responsabilidad:
- deduplicación
- validación de payload
- normalización por taxonomy
- fill de dimensiones estándar

### Job 2: build exposures

Frecuencia: inline en runtime + backfill nocturno.

Responsabilidad:
- capturar qué variantes tocaron una conversación
- consolidar surfaces activas por mensaje / turno / campaña

### Job 3: attribution materialization

Frecuencia: cada 15 min + batch nocturno.

Responsabilidad:
- aplicar ventanas de atribución
- calcular weights
- poblar attribution facts

### Job 4: scorecard recompute

Frecuencia: horario y cierre diario.

Responsabilidad:
- recomputar métricas
- calcular outcome_score
- evaluar confidence
- producir recommendation

### Job 5: guardrail enforcement

Frecuencia: horario o event-driven.

Responsabilidad:
- bloquear entidades si sube refund / escalation / complaint
- limitar tráfico si baja show rate o payment completion
- abrir revisión humana si baja confianza o falta muestra

### Job 6: optimization digest

Frecuencia: diaria.

Responsabilidad:
- generar resumen para supervisor
- mostrar winners, losers, anomalies, rollback candidates

---

## 7. Outcome score configurable

El backend no debe tener un único score fijo.

Debe soportar configuración por vertical, por bot o por objetivo.

Ejemplo de score para clínica estética:

```json
{
  "primary_objective": "booked_and_showed",
  "weights": {
    "reply_rate": 0.10,
    "booking_rate": 0.25,
    "show_rate": 0.25,
    "payment_rate": 0.15,
    "csat": 0.10,
    "refund_rate": -0.05,
    "late_takeover_rate": -0.05,
    "operator_edit_rate": -0.05
  }
}
```

Ejemplo de score para cobranza / recovery:

```json
{
  "primary_objective": "payment_recovered",
  "weights": {
    "payment_link_open_rate": 0.15,
    "payment_rate": 0.40,
    "refund_rate": -0.10,
    "complaint_rate": -0.10,
    "operator_touch_rate": -0.10,
    "promise_to_pay_kept_rate": 0.15
  }
}
```

---

## 8. Guardrails obligatorios

Nunca promover solo por uplift de métrica primaria.

Toda promoción debe pasar guardrails como:

- no incrementar refund rate por encima de umbral
- no incrementar complaint / escalation rate por encima de umbral
- no degradar show rate más allá del límite
- no reducir confianza estadística debajo del mínimo
- no promover con muestra insuficiente
- no promover si depende de demasiada corrección humana

Estados propuestos:

- `candidate`
- `limited_rollout`
- `stable`
- `watchlist`
- `degraded`
- `blocked`
- `rollback_required`

---

## 9. Scorecards iniciales a construir

### Prompt scorecard
- conversations
- replies
- bookings
- payments
- operator edits per 100 sends
- takeovers per 100 conversations
- outcome_score

### Flow scorecard
- step completion
- booking completion
- drop-off by step
- reschedule rate
- show rate downstream
- lost reasons downstream

### Template scorecard
- delivered
- read
- reply
- booking
- payment
- complaint rate
- opt-out / negative sentiment

### Routing scorecard
- time to first good response
- late takeover rate
- escalation rate
- csat
- revenue / resolution outcome

### Operator assist scorecard
- suggestion acceptance rate
- edit distance
- resolved without supervisor
- avg handling time delta

---

## 10. Secuencia de implementación recomendada

### Fase A: foundation
- crear tablas de `exposures`, `outcome_events`, `attribution_facts`, `scorecard_snapshots`, `optimization_decisions`
- exponer API de ingesta y lectura
- conectar runtime para registrar exposures

### Fase B: first attribution
- reply, booking, payment, show, refund, takeover, operator edit
- ventanas simples por vertical
- scorecards 7d y 28d

### Fase C: policy engine
- recommendations automáticas
- limited rollout
- rollback manual
- digest diario para supervisor

### Fase D: optimization control
- promotion / demotion automática con guardrails
- next-best-action policy tuning
- timing policy tuning
- routing policy tuning

---

## 11. Qué sí cambia en producto cuando esto exista

- experiments dejan de medirse solo por CTR o reply y pasan a medirse por valor real
- templates pueden subir o bajar por pago, show y reclamo, no solo por delivery
- routing aprende dónde conviene humano temprano
- prompts dejan de optimizarse por sensación y pasan a tener scorecards comparables
- human ops deja evidencia estructurada que se vuelve aprendizaje del sistema

---

## 12. Riesgos a evitar

- optimizar métricas proxy sin mirar outcomes finales
- mezclar atribución con causalidad sin guardrails
- promover cambios con muestras pequeñas
- confundir éxito del operador con éxito de la configuración AI
- no separar verticales con economics distintos
- perder auditabilidad de por qué se promovió algo

---

## 13. Entregables backend concretos mínimos

Para considerar esta capacidad realmente arrancada, el ZIP debería soportar como mínimo:

1. migración SQL con tablas base de closed loop
2. contrato API de ingesta y consulta
3. runtime hook para guardar exposures
4. worker job para normalización y scorecards
5. UI de scorecards por prompt / flow / template / routing
6. log de decisiones con rollback

Ese es el punto en el que WAOS deja de tener piezas sueltas y empieza a operar como un sistema que **aprende de outcomes reales**.
