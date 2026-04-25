# AI Autopilot Production Hardening V2 - 2026-04-24

This package adds a second hardening layer on top of the Autopilot validation fix.

## Added guardrails

- Centralized frontend Autopilot contract constants and normalization helpers.
- Strict JSON body parsing for wizard proxy routes; malformed JSON no longer silently becomes `{}`.
- Proxy-level `organization_id` validation before backend side effects.
- Bounded user description input at 4,000 characters in UI and API payload builders.
- Safe boolean parsing for `auto_apply`, including string values.
- Shared clamp for `max_autofix_rounds` with a single max of `2`.
- Stronger no-cache response headers plus `X-Content-Type-Options: nosniff` for wizard routes.
- Backend Pydantic hardening for AI prefill/Autopilot payloads: stripped strings, forbidden extra fields, required organization scope.
- Defensive backend runtime clamp for Autopilot rounds even if an internal caller bypasses Pydantic.
- Extra frontend and backend tests for the contract.
- New deploy guard: `scripts/autopilot_hardening_guard.py`, wired into `scripts/deploy-verify.sh`.

## Most important files changed

- `frontend/features/bot-studio/services/wizardAutopilotContract.ts`
- `frontend/app/api/onboarding/wizard/route-helpers.ts`
- `frontend/app/api/onboarding/wizard/ai-autopilot/route.ts`
- `frontend/app/api/onboarding/wizard/ai-prefill/route.ts`
- `frontend/app/lib/data/wizard.ts`
- `frontend/features/bot-studio/services/wizardApi.ts`
- `frontend/features/bot-studio/create/AiSetupAssistant.tsx`
- `backend/app/schemas/onboarding.py`
- `backend/app/vertical_onboarding_ai_prefill.py`
- `scripts/autopilot_hardening_guard.py`

## Local verification run in this sandbox

The static production hardening guard and Python compile checks pass in the sandbox. Full frontend `npm run typecheck` still requires installing `node_modules` in your environment.
