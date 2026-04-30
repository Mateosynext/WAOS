# WAOS Release Candidate Handoff

## Certificación productiva obligatoria

La certificación productiva completa se realiza en GitHub Actions mediante el workflow `production-certification-from-zip` y el script `scripts/validate_release_in_ci.sh`. Render puede validar y desplegar el backend, pero no debe considerarse por sí solo una certificación full-stack.

## Requisito de live AI evals

Antes de promover un tag/build a producción, el repositorio debe tener configurado el secreto de GitHub Actions `OPENAI_API_KEY`. El job productivo define:

```yaml
WAOS_REQUIRE_LIVE_AI_EVALS: '1'
WAOS_AI_EVAL_LIVE: '1'
OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

Si `OPENAI_API_KEY` no existe o está vacío, la certificación productiva debe fallar. Esto es deseable: evita certificar un release únicamente con evals determinísticos, stubs o validaciones parciales cuando los live AI evals son obligatorios.

## Requisito de pytest backend

`pytest -q backend/tests` es un gate bloqueante de certificación productiva. Si `pytest --version`, la colección o la suite se cuelgan/fallan en un entorno local, ese entorno no puede certificar el release. La promoción solo debe hacerse con evidencia de GitHub Actions donde el paso `backend pytest` termine en verde dentro de `production-certification-from-zip`.

## Requisito de certificación frontend npm

El frontend completo no se considera certificado por una auditoría local si `npm --version` o los comandos npm se quedan colgados en el entorno de empaquetado. Eso no implica necesariamente un fallo del código, pero sí impide afirmar certificación frontend local.

Antes de promover producción, `production-certification-from-zip` debe terminar en verde con estos gates frontend:

```bash
cd frontend
npm ci --no-audit --no-fund
npm audit --audit-level=moderate
npm run typecheck
npm run build
test -s .next/BUILD_ID
npm run test:node
```

`npm run test:node` también es parte del gate reproducible de ZIP en `scripts/validate_release_in_ci.sh`. Render no sustituye este requisito porque su `rootDir` es `backend`.

## Checklist de promoción

- [ ] El tag/build pasó `production-certification-from-zip`.
- [ ] `OPENAI_API_KEY` está configurado como GitHub Actions secret.
- [ ] Los live AI evals corrieron con `WAOS_REQUIRE_LIVE_AI_EVALS=1` y `WAOS_AI_EVAL_LIVE=1`.
- [ ] `backend pytest` ejecutó `pytest -q backend/tests` y terminó en verde en CI.
- [ ] `frontend npm ci` terminó en verde en CI.
- [ ] `frontend SCA npm audit` terminó en verde con `--audit-level=moderate`.
- [ ] `frontend typecheck` ejecutó `npm run typecheck` y terminó en verde en CI.
- [ ] `frontend production build` ejecutó `npm run build`, generó `.next/BUILD_ID` y terminó en verde en CI.
- [ ] `frontend node tests` ejecutó `npm run test:node` y terminó en verde en CI.
- [ ] Render no se usó como única evidencia de certificación full-stack.
