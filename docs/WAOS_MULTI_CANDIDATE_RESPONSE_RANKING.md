# WAOS Multi-Candidate Response Ranking

## Objetivo
Mover el runtime de `generate -> verify -> send` a `generate N -> verify each -> score -> select best -> send` para reducir respuestas aceptables pero subóptimas y subir claridad, seguridad y probabilidad de conversión.

## Qué agrega
- Variantes controladas por candidate spec antes del envío:
  - `balanced_default`
  - `concise_direct`
  - `warm_reassuring`
  - `conversion_push`
  - `consultative_clarity`
- Scoring por candidato sobre:
  - `quality`
  - `risk`
  - `clarity`
  - `intent_alignment`
  - `conversion`
- Selección automática del mejor candidato antes de crear el mensaje outbound.
- Persistencia de ranking en `response_candidate_rankings`.
- Resumen de selección en `message_ai_runs.selected_variant`, `candidate_count`, `ranking_version` y `ranking_summary_json`.
- Exposición de `assigned_variant` dentro del closed loop para scorecards por `response_variant`.

## Cómo funciona en runtime
1. El planner y el router siguen armando el execution plan normal.
2. Si la acción es `respond` o `respond_and_schedule_followup`, el runtime construye de 3 a 5 candidate specs.
3. Para cada spec:
   - genera respuesta
   - la verifica con el verifier existente
   - calcula subscores y score total
4. Elige el mejor candidato y solo ese se envía.
5. El run persiste la traza de todas las opciones para auditoría y aprendizaje.

## Persistencia
### Tabla nueva
- `response_candidate_rankings`

Campos clave:
- `message_ai_run_id`
- `candidate_index`
- `variant_key`
- `tone`
- `cta_style`
- `length`
- `framing`
- `response_text`
- `verification_status`
- `score_total`
- `score_json`
- `selected`

### Columnas nuevas en `message_ai_runs`
- `selected_variant`
- `candidate_count`
- `ranking_version`
- `ranking_summary_json`

## Closed loop
El exposure del specialist ahora también guarda `assigned_variant`, así el sistema puede recomputar scorecards por `response_variant` y aprender qué framing mueve mejor booking, cobro, soporte o reactivación.

## Archivos principales
- `backend/app/response_ranking_runtime.py`
- `backend/app/agent_runtime.py`
- `backend/app/ai.py`
- `backend/app/multi_agent_runtime.py`
- `backend/app/application/outcomes_service.py`
- `backend/db/migrations/011_multi_candidate_ranking.sql`
- `backend/tests/test_multi_candidate_response_ranking.py`
