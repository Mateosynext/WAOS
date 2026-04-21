# Release handoff

## Plataforma objetivo
- Backend: Render
- Frontend: Vercel

## Backend
- Usa `render.yaml` de la raíz.
- El servicio web corre `backend/scripts/bootstrap.sh`.
- El worker corre `backend/scripts/worker_bootstrap.sh`.
- Toma variables base desde `backend/.env.render.example`.

## Frontend
- Crea el proyecto con `Root Directory = frontend`.
- Usa `frontend/vercel.json`.
- Toma variables base desde `frontend/.env.vercel.example`.

## Limpieza aplicada a este ZIP
- sin `__pycache__`
- sin `.next`
- sin `tsconfig.tsbuildinfo`
- sin logs temporales
- sin artefactos de Playwright
