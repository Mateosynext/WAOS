# Refactor: portal typing and wizard gateways

## Qué se corrigió

### ClientPortalContent
- Se eliminó el uso de `as any` sobre respuestas vivas de backend en la sección operativa del portal.
- Se agregaron contratos y normalizadores explícitos para:
  - resumen operativo
  - disponibilidad
  - métricas
  - alertas
  - comandos recientes
  - números autorizados
- La UI ahora consume `getClientOperationsData(...)` desde `frontend/app/lib/data/client-operations.ts`.

### Onboarding / Bot Studio
- Se creó `frontend/app/lib/data/wizard.ts` como fuente server-side para:
  - blueprint
  - vertical profile
  - wizard instance
  - start
  - save step
  - dry run
  - apply
- Se creó `frontend/app/api/onboarding/wizard/route-helpers.ts` para evitar boilerplate repetido de proxy interno.
- Se creó `frontend/app/bot-studio/wizardApi.ts` para que `BotStudioWizardClient.tsx` deje de hardcodear rutas internas del wizard.

## Efecto arquitectónico
- Menos parsing ad hoc dentro de componentes visuales.
- Menos conocimiento de rutas dentro de la UI del wizard.
- Los route handlers de onboarding wizard ahora son frontera de transporte, no un segundo lugar con lógica propia.

## Validación
- `npm run typecheck`
- `npm run smoke`
- `npm run test:node`
