# Bot Studio app-shell architecture

`frontend/app/bot-studio` es la capa de rutas Next para Bot Studio. Su responsabilidad es aceptar URLs públicas, normalizar parámetros, redirigir entradas legacy y componer pantallas de `features/bot-studio`.

No debe ser el dueño final de payloads, guards, clientes API, recovery avanzado ni lógica de negocio del wizard.

## Responsabilidades permitidas

- Definir rutas públicas de Next.js.
- Leer `searchParams` y segmentos de ruta.
- Redirigir URLs antiguas hacia rutas canónicas.
- Renderizar shells de loading/error de nivel ruta.
- Delegar pantallas reales a `features/bot-studio/*`.

## Responsabilidades prohibidas

- Construir payloads wizard dentro de `page.tsx`.
- Llamar directamente APIs de wizard desde páginas.
- Mantener estado de negocio del wizard en rutas.
- Implementar validación de steps, dry run, apply o recovery.
- Importar internals profundos de `features/bot-studio/domain` salvo configuración estable de rutas.

<!-- BLOCK 9 DOCS ALIGNMENT -->
## Estado real actual

Esta documentación no debe presentar Bot Studio como completamente desacoplado todavía. La foto operativa actual es:

- Bot Studio tiene rutas nuevas y pantallas separadas para `create` y `reconfigure`.
- `features/bot-studio` ya no debe importar `app/**` directamente; las dependencias legacy que siguen siendo necesarias quedan encapsuladas temporalmente bajo `shared/**` y cubiertas por tests de arquitectura.
- `app/bot-studio` conserva dominio activo: routing, redirects legacy, shell de entrada, adaptación de parámetros y parte del ownership histórico del wizard.
- Los shims siguen vivos temporalmente para sostener imports antiguos mientras se completa la migración (`app/lib/data/wizard*`, barrels de `features/bot-studio/api/*`, rutas legacy y compatibilidad de URLs antiguas).
- El objetivo siguiente es mover el dominio restante a `features/bot-studio/domain` y dejar `app/bot-studio` como routing puro sin lógica de negocio.

## Ownership por módulo

| Módulo | Dueño | Puede importar | No puede importar |
|---|---|---|---|
| `app/bot-studio` | routing | `features/bot-studio`, `shared`, componentes app-shell | domain internals, payload builders, clientes API directos |
| `features/bot-studio/create` | create flow | `shared`, `features/bot-studio/domain`, `features/bot-studio/services`, `features/bot-studio/ui` | `app`, rutas Next, server-only loaders |
| `features/bot-studio/reconfigure` | reconfigure flow | `shared`, `features/bot-studio/domain`, `features/bot-studio/services`, `features/bot-studio/ui` | `app`, rutas Next, server-only loaders |
| `features/bot-studio/domain` | lógica pura | `shared/lib`, tipos puros, constantes serializables | React, Next, `app`, `services`, fetch/API |
| `features/bot-studio/services` | API | `shared/api`, `shared/lib`, `features/bot-studio/domain` | UI, React state, rutas `app` |
| `features/bot-studio/ui` | componentes visuales reutilizables | `shared`, tipos de `domain` | clientes API, route handlers, server-only loaders |
| `features/bot-studio/context` | estado runtime del wizard | `domain`, `services`, `shared` | `app`, payload builders dentro de pages |
| `app/lib/data/wizard*` | shim server compat | `features/bot-studio/services` | `app/bot-studio`, UI, cliente browser |
| `features/bot-studio/api/*` | shim feature compat | `features/bot-studio/services/*` | `app`, UI, lógica de pantalla |

## Guardrails documentados

- La documentación ya no debe afirmar que Bot Studio está desacoplado al 100% hasta que desaparezcan los shims y `app/bot-studio` sea routing puro.
- `features/**` no debe importar `app/**`; si se detecta, debe corregirse o cubrirse con tests de arquitectura.
- `app/lib/data/**` no debe importar `app/bot-studio/**`.
- `app/**/page.tsx` debe mantenerse fino: routing, params, redirects y composición; no debe construir payloads ni ejecutar flujo de negocio pesado.
- Los payload builders, guards, recovery y clientes wizard deben vivir bajo `features/bot-studio/domain` o `features/bot-studio/services` según corresponda.
- Los shims existen para migración incremental; cada shim debe apuntar hacia `features/bot-studio/services/*`, nunca al revés.
