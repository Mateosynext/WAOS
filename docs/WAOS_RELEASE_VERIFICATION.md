# WAOS Release Verification

Version: 0.17.5

Verified commands on this artifact:
- `PYTHONPATH=. pytest -q backend/tests`
- `cd frontend && npm install --no-audit --no-fund --prefer-offline`
- `cd frontend && npm run -s typecheck`
- `cd frontend && npm run -s test:node`
- `cd frontend && npm run -s smoke`

Evidence files live in `docs/verification/`.

Browser E2E note:
- The real critical path remains wired via `npm run test:e2e:real:critical`.
- In this sandbox, the system Chromium process cannot complete the browser probe cleanly, so the artifact is not being falsely labeled as browser-E2E-green from this environment.
- See `docs/verification/browser-probe.txt` plus the server logs in the same directory.
