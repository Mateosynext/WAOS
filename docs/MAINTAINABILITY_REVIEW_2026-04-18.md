# Maintainability review — 2026-04-18

## Context
This review captures the remaining architectural hotspots after the backend application split, AI runtime separation, schema ownership cleanup, frontend app-shell reduction, and Bot Studio feature migration.

## Highest-priority remaining fronts

### 1. Frontend vertical fallback dataset
- The fallback catalog must not keep growing as a single TypeScript blob.
- The dataset is now split by vertical under `frontend/app/lib/vertical-fallback/profiles/` with an indexed loader.
- Remaining follow-up: move the source-of-truth build step closer to backend/catalog publishing so the frontend fallback is purely a resilience artifact.

### 2. Contracts and compatibility discipline
- Keep `response_model` and DTO enforcement as the default in touched backend endpoints.
- Prevent new legacy shims from leaking back to backend/app root.
- Keep frontend data modules consuming normalized contracts instead of re-embedding response shaping in route components.

### 3. Repo hygiene and release discipline
- Source hygiene, release gate, and release build must enforce the same forbidden artifacts.
- README/document references must stay machine-verifiable.
- Local databases, test artifacts, bytecode, and generated reports should fail before packaging, not during handoff.

## Medium-priority follow-up

### Frontend app shell
- Keep route shells thin.
- Push snapshot/context composition into view-models and focused subcomponents.
- Avoid re-centralizing cross-mode branching in `shell.tsx`.

### Backend domains
- Continue moving SQL, schema bootstrap, and operational audit helpers out of `backend/app/domains/*`.
- Preserve the domain layer for business rules, invariants, and transformations.

### Repositories
- Finish consolidating direct SQL paths behind repositories per bounded context.
- Keep policy, handler, presenter, and repository responsibilities split.

## Guardrails
- No new runtime-owned DDL outside `backend/db/migrations/*.sql`.
- No new root-level historical compatibility files.
- No new frontend monoliths that mix fallback data + accessors + composition in one file.
