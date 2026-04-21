# Refactor: testing útil + view models fuera de UI

## Qué cambió
- `frontend/app/client/clientPortalViewModel.ts`
  - timeline
  - section meta
  - summary view model
  - agenda, promociones, conversaciones y bot card models
- `frontend/app/components/reactiveVerticalViewModel.ts`
  - subvertical options
  - subvertical profiles
  - preview model reactivo
  - validación de selección

## Objetivo
- sacar lógica narrativa y de negocio de componentes visuales
- poder testear sin renderizar UI
- subir el nivel del smoke test y de los tests de contratos

## Tests agregados
- `frontend/tests/client-portal-view-model.test.ts`
- `frontend/tests/reactive-vertical-view-model.test.ts`
- `frontend/tests/contracts-behavior.test.ts`

## Smoke
`npm run smoke` ahora valida comportamiento ejecutable de:
- normalizadores de contratos
- view models
- route policy
- cache policy

Ya no se limita a presencia de archivos.
