# P1.5 — Requisito bloqueante de certificación pytest

## Decisión

La validación estática y los guardrails frontend/backend no sustituyen una corrida real de `pytest` sobre `backend/tests`. Un release no debe marcarse como certificado para producción si `pytest -q backend/tests` no terminó en verde dentro del workflow de certificación.

## Hallazgo de esta revisión

En el entorno local usado para esta revisión, `pytest --version` se quedó colgado. Por eso no se pudo certificar una corrida limpia real de:

```bash
pytest -q backend/tests
```

Esto no se considera un pase parcial ni evidencia suficiente de certificación backend. Es un estado **no certificado** hasta que GitHub Actions ejecute y complete `backend pytest` en verde.

## Política de release

El workflow `production-certification-from-zip` y `scripts/validate_release_in_ci.sh` deben seguir tratando `backend pytest` como gate obligatorio. Si `pytest` se cuelga, expira o falla, la certificación productiva debe fallar.

La promoción de un tag/build requiere evidencia de CI donde se vea que:

1. `backend pytest` ejecutó `pytest -q backend/tests`.
2. El comando terminó en verde, no por timeout ni por skip local.
3. El resto de gates productivos también terminó en verde, incluyendo guardrails Node y live AI evals cuando `WAOS_REQUIRE_LIVE_AI_EVALS=1`.

## Estado del paquete

Este paquete incorpora la corrección del scanner de imports local para evitar que `check-local-imports.mjs` bloquee el gate por regex frágil. Sin embargo, esta revisión no certifica pytest localmente; la certificación final debe venir de una corrida limpia del workflow productivo.
