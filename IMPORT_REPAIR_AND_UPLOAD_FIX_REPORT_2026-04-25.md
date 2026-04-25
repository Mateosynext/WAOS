# Import repair and upload-safe package - 2026-04-25

## Fixed Vercel TypeScript blockers

The previous clean package was missing feature modules that were still referenced by active routes/components. This package restores the missing modules and adds an import guard to prevent the same class of breakage.

Restored:

- `frontend/features/ai-ops/AiOpsInspector.tsx`
- `frontend/features/vertical-selection/server/getVerticalsPageModel.ts`
- `frontend/features/vertical-selection/components/VerticalsShell.tsx`
- `frontend/features/vertical-selection/components/SubverticalPanel.tsx`
- `frontend/features/vertical-selection/components/TransactionalMotorPanel.tsx`
- `frontend/features/vertical-selection/components/VerticalCatalog.tsx`
- `frontend/features/vertical-selection/components/VerticalProfile.tsx`
- `frontend/features/vertical-selection/components/VerticalReadiness.tsx`
- `frontend/features/integrations/sync/SyncSection.tsx`

## Added guard

- `frontend/scripts/check-local-imports.mjs`
- `package.json` now runs `npm run check:imports` before `tsc --noEmit` and `next build`.

## Verified locally in the package

- `node scripts/clean-stale-botstudio.mjs` passed.
- `npm run check:imports` passed: all local `@/` and relative imports resolve.
- `python3 backend/scripts/deploy_guard.py --runtime` passed.
- `python3 scripts/release_gate.py` passed.
- `python3 -m compileall -q backend scripts` passed.
- Removed generated caches from package: `__pycache__`, `.pyc`, `.next`, `node_modules`, `test-results`, `coverage`.

## Note

A full `npm run typecheck` inside this sandbox still cannot be treated as authoritative because dependencies are not installed here. In Vercel/Render, `npm install`/`npm ci` installs the declared dependencies before typecheck. The concrete missing-module errors reported by Vercel are fixed in this package.
