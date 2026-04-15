# WAOS Release Package

Paquete de release orientado a producción, auditoría técnica y operación verticalizada sobre WhatsApp.

## Qué incluye
- `backend/`: API, runtime, seguridad, worker, esquema y scripts operativos.
- `frontend/`: aplicación Next.js lista para despliegue.
- `docs/`: documentación interna y portafolio vertical.
- `scripts/`: tooling de release, gate y escaneo.

## Qué excluye deliberadamente del runtime release
- Bases SQLite embebidas.
- `__pycache__` y residuos de compilación local.
- PDFs o reportes generados durante operación.
- suites de prueba y artefactos temporales.
- credenciales visibles, usuarios temporales y dominios locales de staging.

## Base de datos de este release
- Este release es **PostgreSQL-only** para runtime, migraciones y despliegue.
- `DATABASE_URL` debe apuntar a PostgreSQL.

## Artefactos de release esperados
Ejecutando `python scripts/release_build.py --output-dir dist` se generan:
- `dist/waos_runtime_<version>-clean-release.zip`: runtime desplegable limpio.
- `dist/waos_audit_docs_<version>-clean-release.zip`: documentación y evidencia de auditoría.
- `dist/waos_source_<version>-clean-release.zip`: código fuente actualizado con tooling de release.
- `dist/RELEASE_MANIFEST.json`: manifiesto con hashes y conteos.

## Validación recomendada antes de publicar
```bash
python -m compileall backend/app backend/worker.py
PYTHONPATH=. pytest -q backend/tests
python backend/scripts/export_openapi.py
bash scripts/validate_release_in_ci.sh
```

## Frontend QA
- `npm run smoke`: verifica superficies críticas mínimas.
- `npm run test:node`: ejecuta pruebas Node/TS sin navegador.
- `npm run test:mocked-ui`: ejecuta regresión de navegador contra `mock-api-server.mjs`.
- `npm run test:e2e:real`: ejecuta Playwright contra frontend real + backend FastAPI vivo con SQLite efímero y seeds reproducibles.
- `npm run test:critical`: corre smoke + node tests + una variante crítica de browser E2E real.

## Notas operativas
- `RUN_BOOTSTRAP_SEED` queda desactivado por default.
- Si se activa bootstrap, exige credenciales explícitas por entorno.
- El directorio `backend/app/artifacts/reports/` se entrega vacío para generación runtime.

## Browser E2E real
- El modo real arranca `backend/scripts/run_browser_e2e_server.py`.
- Ese script levanta FastAPI con base SQLite efímera, seeds reproducibles y providers falsos solo para pruebas de navegador.
- Los artifacts del modo real se publican desde Playwright (`playwright-report`, `test-results`, traces, screenshots y video en fallos).
