# Frontend architecture refactor

## What changed

### `frontend/app/components.tsx`
The old kitchen-sink file was converted into a thin compatibility barrel.

New structure:
- `frontend/app/components/primitives/shared.tsx`
- `frontend/app/components/primitives/cards.tsx`
- `frontend/app/components/primitives/data-display.tsx`
- `frontend/app/components/layout/shell.tsx`
- `frontend/app/components/navigation/config.ts`
- `frontend/app/components/navigation/index.tsx`
- `frontend/app/components/feedback/index.tsx`
- `frontend/app/components/domain/WhatsAppPreview.tsx`

Result:
- existing imports from `app/components.tsx` keep working
- implementation now lives in focused folders by responsibility
- shell/layout concerns are no longer mixed with all primitives and feedback UI

### `frontend/app/lib/waos.ts`
The old God file was converted into a thin server-only barrel.

New structure:
- `frontend/app/lib/data/shared.ts`
- `frontend/app/lib/data/client-portal.ts`
- `frontend/app/lib/data/bots.ts`
- `frontend/app/lib/data/onboarding.ts`
- `frontend/app/lib/data/verticals.ts`
- `frontend/app/lib/data/inbox.ts`
- `frontend/app/lib/data/analytics.ts`
- `frontend/app/lib/data/commerce.ts`
- `frontend/app/lib/data/integrations.ts`

Result:
- pages can still import from `app/lib/waos.ts` without breakage
- data access is now grouped by domain instead of one file owning everything
- backend contract changes are more localized

## Validation
- `npm run typecheck`
- `npm run test:node`

## Guardrails added
`frontend/tests/internal-refactor.test.ts` now checks that:
- `app/components.tsx` stays as a barrel instead of regrowing implementation
- `app/lib/waos.ts` stays as a barrel instead of regrowing API logic
- the new focused modules contain the expected domain exports

### `frontend/app/lib/contracts.ts`
The oversized contracts file was converted into a thin barrel.

New structure:
- `frontend/app/lib/contracts/shared.ts`
- `frontend/app/lib/contracts/auth.ts`
- `frontend/app/lib/contracts/bots.ts`
- `frontend/app/lib/contracts/onboarding.ts`
- `frontend/app/lib/contracts/inbox.ts`
- `frontend/app/lib/contracts/analytics.ts`
- `frontend/app/lib/contracts/integrations.ts`
- `frontend/app/lib/contracts/commerce.ts`
- `frontend/app/lib/contracts/portal.ts`
- `frontend/app/lib/contracts/verticals.ts`
- `frontend/app/lib/contracts/talent.ts`

Result:
- contract types and normalizers now live next to their bounded context
- `frontend/app/lib/contracts.ts` stays as a compatibility barrel for existing imports
- domain data modules can import focused contracts directly instead of depending on one God file


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
