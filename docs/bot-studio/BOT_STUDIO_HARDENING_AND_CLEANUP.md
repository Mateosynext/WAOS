# Bot Studio: hardening y cleanup

## Qué se dejó blindado
- El flujo de Bot Studio vive por rutas y deja de depender de una sola pantalla monolítica.
- `create` y `reconfigure` quedan separados como experiencias distintas.
- Review, dry run, confirm/apply y resultado viven en pantallas exclusivas.
- Se agregan guardrails operativos para higiene y verificación:
  - `scripts/clean_repo_artifacts.sh`
  - `scripts/hardening_gate.sh`
- Se documenta que `BotStudioWizardClient.tsx` debe considerarse shim temporal, no punto de expansión.

## Regla operativa
Una pantalla = una sola decisión principal.

## Qué queda fuera del camino principal
- autosave visible como protagonista
- diagnósticos de runtime
- JSON overrides y paneles técnicos
- mezcla de review, validación y confirmación en una sola vista
