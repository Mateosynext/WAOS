# AI Autopilot production fix - 2026-04-24

## Scope
This patch hardens the end-to-end bot creation Autopilot path that previously surfaced a generic `Validation failed` message when accepting the generated setup.

## Fixed
- Frontend no longer sends `maxAutofixRounds: 3` to a backend schema that allows `max_autofix_rounds <= 2`.
- Next.js Autopilot proxy clamps `maxAutofixRounds` to the backend-safe range `1..2`.
- Next.js Autopilot proxy parses booleans explicitly, so string values like `"false"` are not coerced to `true`.
- Server data layer also clamps `max_autofix_rounds` before hitting the backend API.
- Browser wizard API now extracts the first backend/Pydantic validation field error from `details.errors` instead of showing only a generic message.
- Wizard route helper now preserves backend validation `details` in the JSON response.
- Autopilot response handling now prefers the fresh wizard from `dry_run_result.wizard`.
- Frontend wizard runtime now restores `validatedWizardRevision` after Autopilot, preventing stale validation gates after a successful dry run.
- Backend Autopilot now refreshes its local `wizard` from the first dry run result, so the returned wizard includes the latest validation data.
- Autopilot success navigation now preserves `wizard_id` when moving to `/bot-studio/create/validate`.
- Button copy was adjusted from “Aceptar todo” to “Preparar y validar” because the current flow prepares/validates and still leaves final apply under human control.

## Added tests
- `frontend/tests/ai-autopilot-production-contract.test.ts`
  - Guards the `max_autofix_rounds` contract.
  - Guards safe boolean parsing.
  - Guards propagation of validation details.
  - Guards dry-run wizard freshness and `wizard_id` navigation.

## Local verification performed
- Ran `frontend/scripts/clean-stale-botstudio.mjs` successfully.
- Ran custom static production checks against the patched files successfully.

## Verification not completed in this environment
- `npm run typecheck` and full frontend tests could not be completed because the uploaded ZIP does not include `node_modules`; TypeScript reported missing packages/types such as `next`, `@types/node`, and Playwright before reaching patch-specific checks.
- `npm ci` was not completed inside the sandbox due environment instability while installing dependencies.

## Recommended production verification after unpacking
From `frontend/` in a normal environment with network/dependency cache:

```bash
npm ci
npm run typecheck
npm run test:node
npm run build
```

From repo root, if Python dependencies/runtime are available:

```bash
bash scripts/deploy-verify.sh
```
