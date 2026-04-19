# WAOS Proactive Reasoning Engine

## Objetivo
Pasar de un runtime que espera el siguiente mensaje a un runtime que detecta señales del negocio y decide a quién contactar, cuándo, con qué objetivo y con qué mensaje.

## Qué agrega esta capa
- Señales proactivas persistidas en `proactive_signal_events`.
- Candidatos priorizados en `proactive_contact_candidates`.
- Materialización de playbooks en `proactive_playbook_runs`.
- Integración con outcomes vía `outcome_exposures` con `source_type=proactive_playbook`.
- Reuso del policy engine por specialist para respetar acciones permitidas y límites de frecuencia.

## Señales modeladas en esta versión
- `appointment_upcoming`
- `payment_failed`
- `payment_pending`
- `no_response_hot_lead`
- `repeat_purchase_window`
- `churn_risk`

## Playbooks proactivos incluidos
- `playbook_upcoming_appointment_confirmation`
- `playbook_payment_retry_recovery`
- `playbook_pending_payment_followup`
- `playbook_hot_lead_reactivation`
- `playbook_repeat_purchase_window`
- `playbook_churn_prevention`

Cada playbook define:
- `objective`
- `specialist_agent_key`
- `recommended_action`
- `timing_policy_id`
- `nba_policy_id`
- `base_score`
- `cooldown_hours`
- `max_runs_7d`

## Cómo razona
1. Lee señales reales desde citas, pagos, conversaciones, CRM, memory y outcomes.
2. Construye facts por contacto.
3. Evalúa elegibilidad con policy y frecuencia.
4. Asigna score, prioridad, mensaje sugerido y siguiente acción.
5. Materializa el playbook y registra una exposure para closed loop.

## Política proactiva
La elegibilidad se suprime cuando:
- hay `human_takeover`
- la IA está pausada
- la acción recomendada no está permitida para el specialist
- ya hubo una intervención del mismo objetivo en 24h
- el contacto ya agotó el cap de 7 días del playbook

## Endpoints
- `POST /api/v1/proactive-engine/evaluate`
- `GET /api/v1/proactive-engine/candidates`
- `POST /api/v1/proactive-engine/candidates/{candidate_id}/materialize`
- `GET /api/v1/proactive-engine/runs`

## Closed loop
Cuando se materializa un playbook:
- se crea un `proactive_playbook_run`
- opcionalmente se registra una `outcome_exposure`
- los eventos posteriores (`payment_completed`, `appointment_attended`, etc.) pueden atribuirse al `playbook_id` y `playbook_version_id`
- los scorecards ya salen por `playbook` sin crear otra capa paralela de analytics

## Archivos principales
- `backend/app/proactive_reasoning_runtime.py`
- `backend/app/application/proactive_reasoning_service.py`
- `backend/app/api/routers/proactive_reasoning.py`
- `backend/app/schemas/proactive_reasoning.py`
- `backend/db/migrations/010_proactive_reasoning_engine.sql`
- `backend/tests/test_proactive_reasoning_engine.py`
