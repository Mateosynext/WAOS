# WAOS AI Production Autopilot v3 Hardening

## Objetivo

La v3 refuerza la v2 end-to-end para que el flujo falle de forma segura, trazable y bloqueada. No intenta ocultar errores: los convierte en estado persistente, eventos SSE, blockers de readiness o acciones humanas requeridas.

Flujo blindado:

`business prompt -> run_id inmediato -> SSE real -> workflow engine -> artifacts -> dry run -> autofix -> simulation -> readiness -> human confirmations -> safe apply -> canary`

## Cambios principales v3

### 1. Tenant isolation por `run_id`

Todos los endpoints que leen o mutan un workflow usan `require_authorized_run`, que:

- valida formato de `run_id`
- busca el run
- valida acceso a `organization_id`
- devuelve 404 si no existe
- devuelve 403 si el usuario no tiene acceso

Esto cubre:

- workflow detail
- SSE
- cancel/resume/rerun
- simulation
- readiness
- human confirmations
- prepare apply
- apply
- canary
- AI Ops run detail
- runtime turn inspection

### 2. Background task failure safety

`run_bot_autopilot_background` ahora tiene guard final. Si cualquier excepción escapa del workflow:

- persiste `status=failed`
- guarda `error_json`
- emite `workflow.failed`
- no provoca rollback silencioso de toda la telemetría

Además, `execute_bot_autopilot_run` ya no re-lanza el error genérico después de registrar fallo; devuelve payload de fallo inspeccionable.

### 3. Cancel cooperativo

El workflow revisa cancelación entre pasos críticos con `_check_cancelled`.

Si el operador cancela:

- se registra `workflow.cancelled`
- el run termina en `cancelled`
- el SSE cierra como terminal

### 4. Fallback seguro cuando falla el wizard legacy

Si `generate_ai_wizard_autopilot` falla:

- no se aplica nada
- se genera `fallback_draft`
- se marca `wizard.failed_partial`
- dry run/readiness quedan bloqueados
- el run puede terminar `completed_partial`
- AI Ops conserva el error

### 5. Apply recalcula readiness

`POST /api/v1/ai/workflows/{run_id}/apply` ya no confía en un snapshot viejo.

Antes de aplicar:

1. valida que el workflow terminó
2. recalcula readiness usando confirmaciones humanas actuales
3. bloquea si `status=blocked` o `can_apply=false`
4. exige `{ "confirm": true }`
5. persiste `apply_result`
6. emite `apply.completed`

### 6. Canary exige apply previo

`prepare-canary` ahora requiere que exista `apply_result.status = applied`.

Esto evita preparar canary sobre configuración no aplicada.

### 7. Human confirmation más estricta

`human-confirmations` requiere valor confirmado cuando `status=confirmed`.

Estados seguros soportados:

- `confirmed`
- `range_confirmed`
- `deferred_safe`
- `blocked_response`
- `escalate_to_human`
- `not_applicable`

Confirmaciones pendientes bloquean readiness con `pending_human_confirmations`.

### 8. Persistencia defensiva

`persistence.py` agrega:

- allowlist de campos actualizables en `ai_workflow_runs`
- clamp de progreso `0..100`
- sanitización/redacción de secretos en JSON
- límite de tamaño JSON
- decode defensivo de JSON corrupto
- orden estable de events/steps
- índices operativos

### 9. SSE más robusto

SSE ahora incluye:

- `id:`
- `retry:`
- soporte para `Last-Event-ID`
- eventos terminales adicionales
- keepalive
- cierre limpio en terminal

Eventos terminales cubiertos:

- `workflow.completed`
- `workflow.completed_partial`
- `workflow.failed`
- `workflow.cancelled`
- `workflow.paused_cost_limit`

### 10. Frontend resiliente

AI Command Center ahora:

- fuerza `async_mode=true`
- nunca manda `auto_apply=true`
- valida que backend devuelva `run_id`
- refresca el workflow al recibir terminal event
- maneja errores JSON/no JSON
- muestra errores de launch actions
- exige valor en human confirmations
- no crashea por SSE frames malformados

## Endpoints reforzados

- `POST /api/v1/ai/bot-autopilot`
- `GET /api/v1/ai/workflows/{run_id}`
- `GET /api/v1/ai/workflows/{run_id}/events`
- `POST /api/v1/ai/workflows/{run_id}/cancel`
- `POST /api/v1/ai/workflows/{run_id}/resume`
- `POST /api/v1/ai/workflows/{run_id}/rerun-failed-step`
- `POST /api/v1/ai/workflows/{run_id}/simulate`
- `GET /api/v1/ai/workflows/{run_id}/simulation-report`
- `GET /api/v1/ai/workflows/{run_id}/go-live-readiness`
- `POST /api/v1/ai/workflows/{run_id}/go-live-readiness`
- `POST /api/v1/ai/workflows/{run_id}/human-confirmations`
- `POST /api/v1/ai/workflows/{run_id}/prepare-apply`
- `POST /api/v1/ai/workflows/{run_id}/apply`
- `POST /api/v1/ai/workflows/{run_id}/prepare-canary`
- `GET /api/v1/internal/ai-ops/runs`
- `GET /api/v1/internal/ai-ops/runs/{run_id}`
- `GET /api/v1/internal/ai-ops/runtime-turns/{turn_id}`

## Validación v3

Comandos ejecutados:

```bash
python -S -c "import py_compile; files=[...]; [py_compile.compile(f,doraise=True) for f in files]; print('pycompile_ok')"
python -S /tmp/run_static_tests.py
node scripts/validate-waos-autopilot-v3.mjs
node scripts/validate-waos-autopilot-v2.mjs
```

Resultados:

```text
pycompile_ok
9 static test functions passed
14/14 checks passed
9/9 checks passed
```

## Limitaciones pendientes de entorno

No se ejecutó `npm run typecheck` ni Playwright porque el ZIP no incluye `frontend/node_modules`.

Para cerrar en una workstation o CI real:

```bash
cd frontend
npm ci
npm run typecheck
npm run test:node
npx playwright test
```

Para backend completo:

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Demo E2E esperada

1. Abrir `/bot-studio`.
2. Confirmar que no aparece `Crear desde cero`, `Create` ni `Rutas canónicas`.
3. Crear run con prompt dental.
4. Ver `workflow.started` por SSE.
5. Ver vertical/business profile/wizard/packs/simulation/readiness.
6. Si readiness bloquea por handoff/precios/horarios, completar Human Confirmation.
7. Recalcular readiness.
8. Preparar apply.
9. Aplicar solo con `{ confirm: true }`.
10. Preparar canary solo después de apply.
11. Abrir AI Ops y auditar timeline, steps, payloads, costos y errores.
