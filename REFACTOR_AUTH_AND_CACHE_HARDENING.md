# Refactor auth middleware y cache frontend

## Qué cambió

### Auth middleware
- `frontend/middleware.ts` dejó de validar solo existencia de cookie.
- Ahora clasifica rutas con `frontend/app/lib/auth/route-policy.ts`.
- Valida sesión real con `frontend/app/lib/auth/edge-session.ts` usando:
  - expiración del JWT
  - refresh token cuando el access token ya venció o falta
  - verificación backend con `/api/v1/auth/me`
  - rol permitido por ruta
  - organización activa cuando la ruta la requiere
- Si la organización no está fijada y la ruta la exige, redirige a `/organizations?source=context-lock`.
- Si la organización válida es única, la fija automáticamente.
- Si la sesión ya no es válida, limpia cookies y redirige a login.

### Cookies y compatibilidad
- Se extrajeron nombres y opciones de cookies a `frontend/app/lib/auth/cookies.ts`.
- `frontend/app/lib/session.ts` conserva exports compatibles para no romper módulos existentes.

### Cache-Control
- `frontend/next.config.ts` ya no aplica `no-store` global.
- La política vive en `frontend/app/lib/http/cache-policy.ts`.
- Se separó por clases de ruta:
  - assets inmutables
  - estáticos semiestables
  - documentos públicos (`/legal`)
  - auth (`/login`) con `no-store`
  - API con `no-store`
  - consola privada con `private, no-cache, max-age=0, must-revalidate`

## Resultado
- mejor control real de acceso
- menor acoplamiento entre middleware y reglas ad hoc
- caché menos agresiva en toda la app
- base lista para seguir endureciendo reglas por ruta o por bounded context
