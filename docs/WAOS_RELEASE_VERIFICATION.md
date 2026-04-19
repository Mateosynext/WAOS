# WAOS Release Verification

Version: 0.17.5-internal-refactor

## Scope of this artifact

This package improves the **internal frontend only** and keeps the external portal under `frontend/app/client/**` out of scope.

## Verified commands on this artifact

- `cd frontend && npm ci --registry=https://registry.npmjs.org/`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run smoke`
- `cd frontend && npm run test:node`
- `cd frontend && npm run build`

## Verification status

### Green in this environment

- Frontend typecheck
- Frontend smoke checks
- Frontend node tests
- Next production build compilation reached optimized production build and type validation successfully in this environment
- Internal refactor checks for:
  - `status`, `support`, and `launch-center` now being real pages instead of redirects
  - API context headers and safe retry guardrails
  - Session scope cleanup for org/bot changes
  - Tokenized visual shell in critical access/error surfaces

## Evidence

Evidence files are expected to be exported to the CI artifact store for each release run. This cleaned production tree does not bundle local verification artifacts.
