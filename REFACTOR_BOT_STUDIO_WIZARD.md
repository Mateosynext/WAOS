# Refactor del Bot Studio Wizard

## Cambios realizados

### 1) Estado centralizado con `useReducer`
Se creó `frontend/app/bot-studio/useBotStudioWizardState.ts` para sacar del componente principal la inicialización y actualización de estado del wizard.

El estado ahora está organizado por dominios:
- `scope`
- `basics`
- `catalog`
- `knowledge`
- `integrations`
- `launch`
- `simulation`
- `preview`
- `wizardRuntime`
- `postApply`
- `autosave`

### 2) `BotStudioWizardClient.tsx` ya no usa decenas de `useState`
El componente principal ahora consume el hook `useBotStudioWizardState(...)` y deja la mutación de estado en una capa dedicada.

### 3) Reseteo transitorio agrupado
`resetTransientState(...)` ahora aplica un patch por dominios en vez de disparar una larga secuencia de setters independientes.

## Validación ejecutada
- `npm run typecheck` ✅
- `npm run test:node` ✅

## Impacto esperado
- Menos acoplamiento en el componente principal
- Más fácil mover después a una state machine si decides endurecer el flujo
- Mejor legibilidad del ownership del estado por dominio
- Menor riesgo al tocar lógica de wizard/autosave/reconfiguración

### 4) Fuente única para blueprint + vertical profile reactivos
Se creó `frontend/app/bot-studio/wizardReactiveData.ts` para centralizar:
- construcción de params
- URLs de `/api/onboarding/wizard/blueprint` y `/api/onboarding/wizard/vertical-profile`
- fetch de ambos contratos
- agregación de errores parciales en un solo loader (`loadWizardReactiveSelection`)

Ahora `BotStudioWizard.tsx`, `BotStudioWizardClient.tsx` y `ReactiveVerticalConfigurator.tsx` consumen el mismo loader compartido.

### 5) Eliminación de fuente paralela obsoleta
Se removió `frontend/app/bot-studio/BotStudioWizard.tsx.bak` para evitar que siga funcionando como referencia equivocada durante cambios futuros.

### 6) Protección por test de arquitectura interna
Se agregó una validación en `frontend/tests/internal-refactor.test.ts` para asegurar que los componentes del wizard no vuelvan a hardcodear esas URLs y sigan usando el módulo compartido.

### 7) Payload builders extraídos a un módulo puro
Se creó `frontend/app/bot-studio/wizardPayloadBuilders.ts` para sacar del cliente principal la construcción de payloads de:
- `start`
- `vertical_fit`
- `business_basics`
- `catalog_offer`
- `knowledge_seed`
- `integrations_rules`
- `launch_review`

`BotStudioWizardClient.tsx` ahora consume un `buildWizardPayloads(...)` memoizado y reutiliza esa misma fuente para:
- `ensureWizardExists(...)`
- persistencia por step
- autosave
- snapshots de payload ya guardado

### 8) Bloques grandes de review / dry run extraídos
Se creó `frontend/app/bot-studio/wizardReviewSections.tsx` para mover fuera del cliente principal componentes densos de UI como:
- `ValidationSnapshotPanel`
- `VerticalScorecardPanel`
- `DiffCard`
- `OperationalDiffDomainCard`
- `HandoffPreviewCard`
- `PackPreviewBlock`
- `StickySummaryRail`

Con esto `BotStudioWizardClient.tsx` baja de 3075 líneas a 2518 líneas y deja de mezclar tanta lógica de render pesado con la orquestación del flujo.

### 9) Protección contra regresión de modularidad
Se amplió `frontend/tests/internal-refactor.test.ts` para verificar que `BotStudioWizardClient.tsx`:
- importe `wizardPayloadBuilders`
- importe `wizardReviewSections`
- ya no declare localmente builders de payload ni paneles principales de review
