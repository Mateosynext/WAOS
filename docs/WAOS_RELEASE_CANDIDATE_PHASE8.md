# WAOS Release Candidate - Phase 8

## Qué quedó listo

### Verticales conectadas de punta a punta
- la subvertical activa ahora se persiste en `organizations.settings_json`
- el bot conserva `selected_subvertical` en `config_draft_json`
- el runtime de vertical resuelve:
  - vertical activa
  - subvertical activa
  - estado del pack aplicado
  - foco por superficie
- la capa vertical ya aparece integrada en:
  - home
  - inbox
  - agenda
  - business hub
  - portal cliente
  - organizations

### Limpieza de release
- se eliminaron archivos y specs mock/demo no productivos
- se eliminó `backend/waos.db`
- se eliminaron `__pycache__`, `.pytest_cache` y `frontend/tsconfig.tsbuildinfo`
- Playwright quedó apuntando a la configuración real
- se limpiaron referencias rotas a artefactos locales de verificación

### Producción
- backend listo para Render con blueprint en:
  - `render.yaml`
  - `backend/render.yaml`
- frontend listo para Vercel con:
  - `frontend/vercel.json`
- configuración endurecida para que producción requiera `DATABASE_URL`
- ejemplos de entorno saneados sin dominios locales ni placeholders de despliegue inseguros

## Validaciones ejecutadas
- `python -m compileall backend/app backend/scripts`
- `pytest -q backend/tests/test_vertical_connected_phase8.py backend/tests/test_vertical_10x_phase7.py backend/tests/test_operational_control_phase6.py backend/tests/test_activation_foundations.py`
- `cd frontend && npm run smoke`
- `cd frontend && npm run test:node`
- `python scripts/release_scan.py .`

## Notas honestas
- el backend quedó validado como release candidate para Render
- el frontend quedó limpio y con pruebas smoke/node verdes
- no se afirma que todo el frontend esté typecheck green global porque el repo arrastra deuda previa fuera de esta fase
- para Vercel, el proyecto debe configurarse con `Root Directory = frontend`
