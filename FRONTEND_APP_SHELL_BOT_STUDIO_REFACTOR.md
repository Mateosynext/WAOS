# Frontend refactor handoff

## Qué quedó hecho
- `frontend/app/client/ClientPortalContent.tsx` quedó como ensamblador fino y delega secciones a `frontend/app/client/ClientPortalSections.tsx`.
- `frontend/app/components/layout/shell.tsx` quedó centrado en el layout principal y delega snapshot/contexto a `frontend/app/components/layout/shellContext.tsx`.
- `frontend/app/lib/auth/refresh.ts` centraliza la historia de refresh para browser, server, edge y route handler.
- `frontend/app/bot-studio/*` quedó como capa app/compat y la implementación activa migró a:
  - `frontend/features/bot-studio/context/*`
  - `frontend/features/bot-studio/review/*`
  - `frontend/features/bot-studio/shared/*`
- `frontend/app/components/ConversationComposer.tsx` ya no construye inline todos los payloads; usa `frontend/app/components/conversation-composer/payload.ts`.

## Validación hecha aquí
- revisión estructural de imports y shims del frontend
- verificación de sintaxis práctica sobre los archivos tocados
- actualización de `frontend/tests/internal-refactor.test.ts` al nuevo split

## Limitación del entorno
No se pudo correr la batería completa de `npm run typecheck` ni `npm run test:node` porque este entorno no tiene red y el ZIP no trae `frontend/node_modules`, así que faltan `next`, `tsx`, `@types/node` y demás dependencias del proyecto.
