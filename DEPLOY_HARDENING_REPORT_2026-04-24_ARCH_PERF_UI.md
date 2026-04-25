# WAOS Deploy Hardening — Architecture, Performance and UX Follow-up

Date: 2026-04-24

## Applied fixes

### 7. UI accepts all without double round-trip
- `frontend/features/bot-studio/create/AiSetupAssistant.tsx` now calls `onAutopilot({ userDescription: description, intensity: "savage" })` directly from the primary accept button.
- Removed the forced preview dependency from the accept-all path.
- The previous `accept("accept")` path is blocked by `deploy_guard.py` and tests.

### 8. Canonical frontend env example
- Kept only `frontend/.env.production.example` as the canonical source of truth.
- Removed `frontend/.env.example` and `frontend/.env.vercel.example`.
- Documented public URLs, server API URLs, timeout/retry settings, cookies and fallback behavior in one file.

### 9. Render proxy headers
- `TRUST_PROXY_HEADERS=true` in both `render.yaml` files.
- Added `TRUSTED_PROXY_IPS` with private/proxy CIDRs.
- Backend proxy trust now supports CIDR matching via `ipaddress.ip_network`, not only exact IP strings.

### 10. OPENAI_API_KEY production gate
- `preflight_check.py` now treats missing `OPENAI_API_KEY` as a production error instead of a soft warning.
- This prevents silent fallback to heuristic-only Autopilot in production.

### 11. Split AI runtime persistence
- Split `backend/app/ai_runtime/persistence.py` into:
  - `persistence_load.py`: context loading and execution-run start.
  - `persistence_write.py`: decision persistence, specialist route artifacts, AI run artifacts and finalization.
- Left a small backwards-compatible facade in `persistence.py`.
- Updated `pipeline.py` to import from the split modules directly.

### 12. Vertical fallback profile sync
- Added `backend/scripts/export_vertical_profiles.py`.
- Added `scripts/sync-vertical-profiles.sh`.
- Made `frontend/app/lib/vertical-fallback/index.ts` data-driven: it loads profile files from `index.json` instead of a hardcoded loader map.
- Added release/deploy checks so backend and frontend vertical IDs cannot drift silently.

### 13. WEB_CONCURRENCY increased to 3
- `render.yaml` and `backend/render.yaml`: `WEB_CONCURRENCY=3`.
- `backend/scripts/bootstrap.sh`: default `WEB_CONCURRENCY=${WEB_CONCURRENCY:-3}`.
- `backend/app/config.py`: production default is now 3.
- `deploy_guard.py` fails if this regresses.

### 14. Autopilot endpoint in Release Gate
- Added `scripts/release_gate.py`.
- Critical route contract now includes `/api/v1/onboarding/wizard/ai-autopilot`.
- `scripts/deploy-verify.sh` and GitHub Actions run the release gate before frontend build.

### 15. Long-running Autopilot progress UI
- `AiSetupAssistant.tsx` now shows staged progress while Autopilot runs:
  - `Detectando industria...`
  - `Generando setup completo...`
  - `Validando...`
  - `Listo`
- Uses an accessible `role="status"` live region.

## Validation performed in sandbox

```bash
python -S backend/scripts/deploy_guard.py
python -S scripts/release_gate.py --profile source
python -S backend/scripts/validate_render_env.py  # with production dummy env
node frontend/scripts/validate-env.mjs
node frontend/scripts/clean-stale-botstudio.mjs
compile() checks for split persistence modules
cmp render.yaml backend/render.yaml
```

## Not completed in sandbox

`npm ci`, `npm run typecheck`, and `npm run build` were not completed here because package installation/build commands time out in this sandbox. They remain wired into:

```bash
./scripts/deploy-verify.sh
```

and `.github/workflows/deploy-guard.yml`.
