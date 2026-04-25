# AI Autopilot para creación de bots

## Qué se agregó

- Backend `backend/app/vertical_onboarding_ai_prefill.py` con generación AI-first de wizard completo.
- Endpoint `POST /api/v1/onboarding/wizard/ai-prefill` para generar un draft estructurado con `answers_patch`, cards, supuestos, confianza y campos críticos a confirmar.
- Endpoint `POST /api/v1/onboarding/wizard/{wizardId}/ai-autofix` para rellenar pendientes bloqueantes y volver a correr dry run.
- Componente `frontend/features/bot-studio/create/AiSetupAssistant.tsx` con flujo “Cuéntame tu negocio → setup generado por IA → aceptar todo / editar detalles importantes”.
- Batch-save en aceptación del draft: crea o reutiliza wizard y guarda los seis pasos generados (`vertical_fit`, `business_basics`, `catalog_offer`, `knowledge_seed`, `integrations_rules`, `launch_review`) sin obligar al usuario a avanzar pantalla por pantalla.
- Botón “Arreglar pendientes con IA” en validación.
- Modo avanzado intacto: las pantallas existentes siguen editables después del prefill.

## Seguridad / blindaje

- La IA no aplica cambios finales al bot: genera draft y el flujo sigue pasando por dry run y apply.
- Horarios reales, precios/promos, WhatsApp, integraciones conectadas y políticas sensibles quedan marcadas como confirmación humana.
- Sin `OPENAI_API_KEY`, el sistema cae a generación heurística basada en perfiles verticales y reglas locales.

## Validación ejecutada

- `python3 -S -m py_compile` sobre los archivos backend modificados: OK.
- Transpilación sintáctica TypeScript con `typescript.transpileModule` sobre la mayoría de archivos frontend modificados: OK hasta que el proceso quedó colgado en la revisión de rutas; los archivos de rutas son simples y fueron inspeccionados manualmente.
- No se pudo ejecutar `npm run typecheck` completo porque el entorno no tenía `node_modules` y el proceso de `tsc` excedió el tiempo disponible.
