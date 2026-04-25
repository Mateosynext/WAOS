# WAOS general cleanup and bot-creation pointer verification — 2026-04-25

## What was fixed in this pass

1. Restored the missing AI Command Center frontend module required by `/bot-studio`:
   - `frontend/features/ai-command-center/AiCommandCenter.tsx`
   - `frontend/features/ai-command-center/AiCommandPrompt.tsx`
   - `frontend/features/ai-command-center/useAiWorkflowStream.ts`
   - `frontend/features/ai-command-center/AiRunTimeline.tsx`
   - `frontend/features/ai-command-center/types.ts`

2. Added root release tooling expected by backend deploy guards/tests:
   - `scripts/release_gate.py`
   - `scripts/sync-vertical-profiles.sh`

3. Removed transient build/runtime artifacts from the ZIP source tree:
   - `__pycache__`
   - `*.pyc`
   - `.next`
   - `node_modules`
   - `tsconfig.tsbuildinfo`
   - Playwright/test output folders

4. Re-checked frontend-to-backend AI workflow route alignment:
   - Frontend `POST /api/ai/bot-autopilot` -> backend `POST /api/v1/ai/bot-autopilot`
   - Frontend health proxy -> backend `/api/v1/ai/bot-autopilot/health`
   - Frontend workflow status/events/apply/canary proxies -> backend `/api/v1/ai/workflows/{run_id}/...`

5. Re-checked backend bot apply contract:
   - `apply_guided_onboarding_wizard(...)` is called from workflow apply.
   - `actor_user=user` is used.
   - `bot_id` is persisted into the run result after apply.
   - `confirm=true` is required before apply.
   - readiness blocks unsafe apply.

## Verification performed

- `deploy_guard.py --runtime`: passed through imported main execution with `PYTHONDONTWRITEBYTECODE=1`.
- `scripts/release_gate.py`: passed through imported main execution with `PYTHONDONTWRITEBYTECODE=1`.
- Static route checks for AI workflow proxies: passed.
- Static Command Center checks for required prompt controls, SSE usage, and `completed_partial` handling: passed.
- Source cleanup check: no transient runtime/build artifacts remained before packaging.

## Known limitation of this sandbox

Full `npm ci`, `npm run typecheck`, and `next build` were not completed here because the sandbox npm/node processes were intermittently hanging after printing output. The source-level missing import that would have broken `/bot-studio` was fixed directly, and the static guard coverage was expanded to catch this class of issue.

## Deployment order

1. Deploy backend/Render first.
2. Confirm:
   - `/livez`
   - `/healthz`
   - `/api/v1/ai/bot-autopilot/health`
   - `/openapi.json` contains `/api/v1/ai/bot-autopilot`
3. Deploy frontend/Vercel second.
4. Test `/bot-studio` and start one workflow.

