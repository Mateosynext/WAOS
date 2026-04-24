# Refactor documentation alignment

## Objetivo

Alinear la documentación de Bot Studio con el estado real del desacoplamiento, evitando afirmar que el feature ya está completamente aislado cuando todavía existen app-shell, shims y deuda de migración.

## Archivos actualizados

- `REFACTOR_FRONTEND_ARCHITECTURE.md`
- `FRONTEND_APP_SHELL_BOT_STUDIO_REFACTOR.md`
- `REFACTOR_BOT_STUDIO_WIZARD.md`
- `frontend/features/bot-studio/README.md`
- `frontend/app/bot-studio/README_ARCHITECTURE.md`

## Cambios documentados

- Estado real actual de Bot Studio.
- Tabla de ownership por módulo.
- Reglas de imports permitidos y prohibidos.
- Guardrails para evitar regresiones de arquitectura.
- Estado temporal de shims y siguiente objetivo de migración hacia `features/bot-studio/domain`.

## Nota de realidad

La meta no es declarar victoria prematura. El app-shell sigue existiendo, los shims siguen vivos y cualquier dependencia feature -> app debe tratarse como regresión o deuda activa hasta que la migración termine.
