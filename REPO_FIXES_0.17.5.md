# WAOS 0.17.5 - repo corregido y reforzado

## Cambios aplicados

1. `frontend/app/actions/auth.ts`
   - Se movió `redirect()` fuera del `try/catch` para evitar que Next muestre `NEXT_REDIRECT` como error de login.
   - Archivo reescrito limpio en UTF-8.

2. `frontend/app/bot-studio/page.tsx`
   - Se ajustó `searchParams` para que sea compatible con Next 15.

3. `backend/app/db.py`
   - Se movieron imports de migraciones a imports locales para cortar el ciclo de importación.

4. `backend/app/vertical_onboarding_runtime.py`
   - Se movió `create_bot` a import local dentro del flujo del wizard.

5. `backend/app/repositories/__init__.py`
   - Se cambió a exports lazy para evitar cargar repositorios en cascada durante import time.

6. `backend/app/repositories/audit.py`
   - Se limpiaron imports no usados para reducir acoplamiento con `app.db`.

## Recomendación de deploy

1. Render worker
2. Render API
3. Vercel frontend
