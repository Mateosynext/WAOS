# AI Command Center click feedback fix - 2026-04-26

## Symptom
The user clicks "Construir agente con IA" / "Generar bot con IA" and visually nothing happens.

## Evidence
The production log sample only shows repeated `GET /api/v1/ai/workflows/<run_id>/events` and `/livez` requests. There is no `POST /api/v1/ai/bot-autopilot` nor `POST /apply` in the pasted window, which means the browser did not trigger a new start/apply request during that interaction.

## Root cause
The main generation button was disabled when either organization was missing or the description had fewer than 20 characters:

```tsx
disabled={!canSubmit}
```

But the global button CSS had no visible disabled state. The button looked like a normal primary CTA, so the UI felt dead: the click was swallowed by the browser and the React validation branch never ran.

## Fix
- The generation CTA is now disabled only while a request is busy.
- Missing organization / short description now shows inline helper copy.
- Clicking the CTA with invalid inputs now runs `start()` and surfaces a warning message instead of doing nothing.
- Global button disabled styles were added so disabled CTAs are visibly disabled.
- Static regression guard added in `frontend/tests/ai-command-center-e2e-guard.test.ts`.

## Files changed
- `frontend/features/ai-command-center/AiCommandPrompt.tsx`
- `frontend/features/ai-command-center/AiCommandCenter.tsx`
- `frontend/app/globals.css`
- `frontend/tests/ai-command-center-e2e-guard.test.ts`
