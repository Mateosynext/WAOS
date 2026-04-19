# WAOS Release Validation - Release Candidate

Fecha de validación: 2026-04-17

## Validaciones ejecutadas

### Preflight consolidado
```bash
bash scripts/release_candidate_smoke.sh
```
Resultado: **OK**

Incluye:
- `python -m compileall backend/app backend/worker.py`
- `python backend/scripts/validate_render_env.py` con variables productivas de muestra
- `node frontend/scripts/validate-env.mjs` con variables productivas de muestra
- `node frontend/scripts/smoke-routes.mjs`

### Frontend
```bash
cd frontend
npm ci
NODE_ENV=production NEXT_PUBLIC_API_BASE_URL=https://api.example.com API_INTERNAL_URL=https://api.example.com NEXT_PUBLIC_APP_URL=https://app.example.com API_BASE_URL=https://api.example.com API_TIMEOUT_MS=12000 API_RETRIES=1 SECURE_COOKIES=true npm run typecheck
NODE_ENV=production NEXT_PUBLIC_API_BASE_URL=https://api.example.com API_INTERNAL_URL=https://api.example.com NEXT_PUBLIC_APP_URL=https://app.example.com API_BASE_URL=https://api.example.com API_TIMEOUT_MS=12000 API_RETRIES=1 SECURE_COOKIES=true npm run build
```
Resultado:
- `npm ci`: **OK**
- `npm run typecheck`: **OK**
- `npm run build`: **OK**

### Backend
```bash
PYTHONPATH=backend pytest -q backend/tests/test_legal_public_endpoints.py backend/tests/test_production_hardening_phase9.py
```
Resultado: **4 passed**

## Alcance validado
- coherencia mínima de despliegue Render/Vercel
- variables obligatorias de producción
- presencia de rutas críticas frontend
- build productivo de Next.js
- endpoints legales públicos y endurecimiento base del backend

## Pendientes fuera de este preflight
- deploy real en Render con secrets definitivos
- deploy real en Vercel con dominios finales
- smoke autenticado contra ambiente público
- cierre jurídico de placeholders y datos corporativos finales
