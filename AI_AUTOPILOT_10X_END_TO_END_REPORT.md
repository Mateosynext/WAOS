# AI Autopilot 10x end-to-end

## Objetivo

Convertir la creación del bot en un flujo de IA fuerte, conectado de punta a punta y blindado por validación:

1. Usuario describe negocio / selecciona industria, subvertical y objetivo.
2. IA genera setup completo.
3. Backend guarda los 6 pasos del wizard en batch.
4. Backend corre dry run.
5. Si falla, backend ejecuta autofix iterativo.
6. Frontend aterriza directo en validación con wizard, dry run y snapshot ya conectados.
7. Apply final queda humano por seguridad, salvo que el endpoint reciba `auto_apply=true` explícitamente.

## Backend agregado

### Nuevo endpoint

`POST /api/v1/onboarding/wizard/ai-autopilot`

Schema: `GuidedOnboardingAiAutopilotRequest`

Campos principales:

- `organization_id`
- `bot_id`
- `vertical_id`
- `subvertical`
- `primary_objective`
- `user_description`
- `intensity`: `balanced | aggressive | conservative | savage`
- `existing_answers`
- `max_autofix_rounds`
- `auto_apply`

### Orquestador nuevo

Archivo: `backend/app/vertical_onboarding_ai_prefill.py`

Función nueva:

`generate_ai_wizard_autopilot(...)`

Hace:

- llama `generate_ai_wizard_prefill`
- crea/recupera wizard con `start_guided_onboarding_wizard`
- guarda todos los steps con `_apply_answers_patch_to_wizard`
- corre `dry_run_guided_onboarding_wizard`
- si no está listo, corre `apply_ai_autofix_to_wizard` con rondas iterativas
- devuelve `wizard`, `wizard_id`, `dry_run_result`, `validation_snapshot`, `pipeline`, `next_action`, `blocking_items`, `apply_ready`

### Autofix más duro

`apply_ai_autofix_to_wizard(...)` ahora acepta `max_rounds` y ejecuta rondas iterativas hasta que:

- el dry run queda `apply_ready`, o
- ya no hay campos rellenables automáticamente.

Devuelve:

- `autofix_rounds`
- `applied_steps`
- `blocking_items`
- `apply_ready`
- `dry_run_result`

### IA más opinionated

Se agregó intensidad `savage` y más payload generado:

- preguntas de calificación
- objection handlers
- lead scoring rules
- handoff matrix
- must_collect_before_handoff
- never_autopromise
- AI autopilot plan
- critical confirmation cards
- simulation scenarios
- dry run acceptance criteria

## Frontend agregado

### Ruta proxy Next

`frontend/app/api/onboarding/wizard/ai-autopilot/route.ts`

Conecta el frontend con el endpoint backend.

### Client API

`frontend/features/bot-studio/services/wizardApi.ts`

Nuevo helper:

`runWizardAiAutopilotRequest(...)`

### UI

`frontend/features/bot-studio/create/AiSetupAssistant.tsx`

Cambios:

- botón `Modo 10x duro`
- botón `Aceptar todo y correr Autopilot`
- al aceptar, ya no depende del batch save paso por paso desde cliente
- llama backend end-to-end
- muestra pipeline end-to-end cuando el backend responde:
  - Detectar negocio
  - Generar setup completo
  - Guardar 6 pasos en backend
  - Validar con dry run
  - Autofix iterativo
  - Apply final esperando humano

### Flow state

`frontend/features/bot-studio/flow/wizardScreenModels.ts`

Nuevo action:

`runAiAutopilot(...)`

Hace:

- llama `runWizardAiAutopilotRequest`
- aplica `buildStatePatchFromAiPrefill(result)`
- setea `wizard`
- setea `wizardId`
- setea `dryRunResult`
- deja autosave en `saved`

## Validación realizada

- Parsing Python con `ast.parse` para archivos backend modificados: OK.
- Revisión de wiring por grep: OK.
- No se pudo correr typecheck completo de frontend porque el ZIP no incluye `node_modules`.
