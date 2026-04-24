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


<!-- BLOCK 9 DOCS ALIGNMENT -->
## Estado real actual

Esta documentación no debe presentar Bot Studio como completamente desacoplado todavía. La foto operativa actual es:

- Bot Studio tiene rutas nuevas y pantallas separadas para `create` y `reconfigure`.
- `features/bot-studio` ya no debe importar `app/**` directamente; las dependencias legacy que siguen siendo necesarias quedan encapsuladas temporalmente bajo `shared/**` y cubiertas por tests de arquitectura.
- `app/bot-studio` conserva dominio activo: routing, redirects legacy, shell de entrada, adaptación de parámetros y parte del ownership histórico del wizard.
- Los shims siguen vivos temporalmente para sostener imports antiguos mientras se completa la migración (`app/lib/data/wizard*`, barrels de `features/bot-studio/api/*`, rutas legacy y compatibilidad de URLs antiguas).
- El objetivo siguiente es mover el dominio restante a `features/bot-studio/domain` y dejar `app/bot-studio` como routing puro sin lógica de negocio.

## Ownership por módulo

| Módulo | Dueño | Puede importar | No puede importar |
|---|---|---|---|
| `app/bot-studio` | routing | `features/bot-studio`, `shared`, componentes app-shell | domain internals, payload builders, clientes API directos |
| `features/bot-studio/create` | create flow | `shared`, `features/bot-studio/domain`, `features/bot-studio/services`, `features/bot-studio/ui` | `app`, rutas Next, server-only loaders |
| `features/bot-studio/reconfigure` | reconfigure flow | `shared`, `features/bot-studio/domain`, `features/bot-studio/services`, `features/bot-studio/ui` | `app`, rutas Next, server-only loaders |
| `features/bot-studio/domain` | lógica pura | `shared/lib`, tipos puros, constantes serializables | React, Next, `app`, `services`, fetch/API |
| `features/bot-studio/services` | API | `shared/api`, `shared/lib`, `features/bot-studio/domain` | UI, React state, rutas `app` |
| `features/bot-studio/ui` | componentes visuales reutilizables | `shared`, tipos de `domain` | clientes API, route handlers, server-only loaders |
| `features/bot-studio/context` | estado runtime del wizard | `domain`, `services`, `shared` | `app`, payload builders dentro de pages |
| `app/lib/data/wizard*` | shim server compat | `features/bot-studio/services` | `app/bot-studio`, UI, cliente browser |
| `features/bot-studio/api/*` | shim feature compat | `features/bot-studio/services/*` | `app`, UI, lógica de pantalla |

## Guardrails documentados

- La documentación ya no debe afirmar que Bot Studio está desacoplado al 100% hasta que desaparezcan los shims y `app/bot-studio` sea routing puro.
- `features/**` no debe importar `app/**`; si se detecta, debe corregirse o cubrirse con tests de arquitectura.
- `app/lib/data/**` no debe importar `app/bot-studio/**`.
- `app/**/page.tsx` debe mantenerse fino: routing, params, redirects y composición; no debe construir payloads ni ejecutar flujo de negocio pesado.
- Los payload builders, guards, recovery y clientes wizard deben vivir bajo `features/bot-studio/domain` o `features/bot-studio/services` según corresponda.
- Los shims existen para migración incremental; cada shim debe apuntar hacia `features/bot-studio/services/*`, nunca al revés.
