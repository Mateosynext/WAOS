# P1.3 — AI evals productivos con proveedor live

## Decisión

Los evals determinísticos actuales siguen siendo necesarios, pero no son suficientes para certificar comportamiento de IA productiva. A partir de este cambio, la certificación productiva debe incluir un gate live en modo sandbox contra proveedor OpenAI-compatible cuando `WAOS_REQUIRE_LIVE_AI_EVALS=1`.

## Gate agregado

- Módulo: `backend.app.ai_evals.eval_live_provider_sandbox`
- Fixtures versionados: `backend/app/ai_evals/fixtures/live_provider_golden_prompts.json`
- Baseline versionado: `backend/app/ai_evals/fixtures/live_provider_baseline.json`
- Activación live: `WAOS_AI_EVAL_LIVE=1`
- Requisito productivo: `WAOS_REQUIRE_LIVE_AI_EVALS=1`
- Credencial requerida en modo requerido: `OPENAI_API_KEY`

Si `WAOS_REQUIRE_LIVE_AI_EVALS=1` y no existe `OPENAI_API_KEY`, el gate falla explícitamente. Esto evita certificar producción solo con stubs o lógica determinística local.

## Cobertura mínima de fixtures

Los golden prompts cubren:

1. Hallucination de precios, horarios, promociones y certificaciones.
2. Prompt injection para revelar system prompt, secretos, tokens o herramientas.
3. Tool-use no autorizado, como reservar, cobrar o escribir en calendario sin herramienta confirmada.
4. Seguridad médica/urgencias y claims prohibidos.
5. Fallback vertical genérico cuando faltan datos reales de catálogo/cobertura.

Todos los casos son críticos y el baseline exige `minimum_suite_score = 1.0`.

## Política de CI

- Pull requests/source sanity: corre suite determinística y valida que los fixtures/baseline live existan y estén versionados.
- Tags/certificación productiva desde ZIP: `scripts/validate_release_in_ci.sh` falla si `WAOS_REQUIRE_LIVE_AI_EVALS=1` y no hay proveedor live configurado.
- El workflow `production-certification-from-zip` habilita `WAOS_REQUIRE_LIVE_AI_EVALS=1`, `WAOS_AI_EVAL_LIVE=1` y lee `OPENAI_API_KEY` desde secrets.

## Requisito bloqueante de release

Para promover un tag/build como certificado para producción, el repositorio de GitHub debe tener configurado el secreto `OPENAI_API_KEY` en **Settings -> Secrets and variables -> Actions** antes de ejecutar `production-certification-from-zip`.

Este requisito es intencional: si `OPENAI_API_KEY` falta o está vacío, la certificación productiva debe fallar. Un release no debe marcarse como full-stack/productivo cuando los live AI evals no pudieron ejecutarse contra un proveedor real en modo sandbox.

Checklist mínimo antes de promover un release:

1. `OPENAI_API_KEY` existe como GitHub Actions secret.
2. El workflow productivo corre con `WAOS_REQUIRE_LIVE_AI_EVALS=1`.
3. El workflow productivo corre con `WAOS_AI_EVAL_LIVE=1`.
4. `production-certification-from-zip` termina en verde; no basta con Render ni con la suite determinística local.

## No objetivos

Este gate no autoriza herramientas reales ni escribe en sistemas externos. El proveedor se evalúa con prompts sandbox y sin datos de clientes.
