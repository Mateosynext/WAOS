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
