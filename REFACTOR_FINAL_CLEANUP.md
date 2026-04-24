# Refactor final cleanup - Bot Studio

## Objetivo

Pasada final para cerrar huecos entre la documentación, la capa de APIs del wizard, los tests de comportamiento y los boundaries de arquitectura.

## Limpieza aplicada

- Se creó `frontend/shared/**` como capa temporal para dependencias legacy que antes obligaban a `features/bot-studio` a importar `app/**` directamente.
- `features/bot-studio` ya no contiene imports directos a `@/app/**`.
- Los shims siguen vivos, pero ahora apuntan hacia servicios canónicos:
  - `frontend/app/lib/data/wizard.ts`
  - `frontend/app/lib/data/wizardEndpoints.ts`
  - `frontend/features/bot-studio/api/wizardEndpoints.ts`
  - `frontend/features/bot-studio/services/wizardApi.ts`
- Se añadió cliente wizard unificado:
  - `frontend/features/bot-studio/services/wizardEndpoints.ts`
  - `frontend/features/bot-studio/services/wizardClient.ts`
  - `frontend/features/bot-studio/services/clientWizardApi.ts`
  - `frontend/features/bot-studio/services/serverWizardApi.ts`
- Se añadieron `WizardError` y `WizardIssue` como contratos explícitos del dominio.
- Se añadió `WizardErrorPanel` y se conectó en validate, apply, dry-run y confirm.
- Se normalizó el catch de create/reconfigure para convertir errores de red, 409, 422 y parciales en mensajes consistentes.

## Tests agregados o reforzados

- `frontend/tests/architecture-boundaries.test.ts`
  - Bloquea imports directos de Bot Studio hacia `app/**`.
  - Mantiene allowlist explícita para deuda legacy en otros features y falla si aparece deuda nueva.
  - Protege `app/lib/data/**` contra imports a `app/bot-studio/**`.
  - Protege páginas de Bot Studio contra payload builders, fetch directo y páginas pesadas.
- `frontend/tests/integration/bot-studio-wizard-errors.test.ts`
  - Cubre 500, 409, 422, partial apply y errores de red.
- `frontend/tests/e2e/bot-studio-wizard-stale-validation.spec.ts`
  - Cubre dry run stale al modificar datos después de validar.
- `frontend/tests/e2e/bot-studio-navigation-recovery.spec.ts`
  - Cubre refresh, back, forward, deep links inválidos y reconfigure sin bot.

## Estado real despues de esta pasada

- Bot Studio tiene rutas y pantallas separadas.
- El API client del wizard está centralizado bajo `features/bot-studio/services`.
- `features/bot-studio` ya no importa `app/**` directamente.
- Persisten shims temporales para compatibilidad, documentados y cubiertos.
- Persisten deudas legacy en otros features (`inbox`, `integrations`, `vertical-selection`), explicitadas en allowlist de arquitectura para evitar deuda nueva silenciosa.
- El siguiente paso recomendado es reducir el allowlist global moviendo contratos/componentes comunes desde `app/**` hacia `shared/**` módulo por módulo.

## Validaciones manuales ejecutadas

- Grep de imports directos `@/app` en `frontend/features/bot-studio`: sin resultados.
- Revisión estática de allowlist de arquitectura: sin offenders nuevos fuera de allowlist.
- Integridad del ZIP validada con `unzip -t` en el paquete final.

## Nota

No se ejecutó la suite completa de Node/Playwright porque el paquete entregado no incluye `node_modules`; debe correr en el entorno del proyecto con `npm ci` y luego `npm run test:node` / `npm run test:e2e:real`.
