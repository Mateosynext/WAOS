# WAOS Frontend Architecture Distilled

## Active surface

The supported application surface lives under `frontend/app/*`.

## Legacy compatibility routes

Legacy compatibility routes are isolated under the hidden route group:

- `frontend/app/(legacy)/v14/page.tsx`
- `frontend/app/(legacy)/v15/page.tsx`
- `frontend/app/(legacy)/v16/page.tsx`

This keeps the legacy URL aliases working while preventing older generations from appearing as first-class application sections in the active app root.

## Source of truth

Frontend source of truth is declared in `frontend/app/lib/architecture.ts`.
