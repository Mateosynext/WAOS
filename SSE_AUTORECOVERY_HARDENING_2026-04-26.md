# SSE Autorecovery Hardening - 2026-04-26

## Problema observado

El frontend mostraba: `Stream SSE desconectado; usa Actualizar estado para recuperar.`

Eso significaba que, ante un corte normal de SSE por proxy, red o runtime serverless, el cliente cerraba el `EventSource` en `onerror` y dejaba la recuperación en manos del usuario.

## Corrección quirúrgica

1. `useAiWorkflowStream.ts` ya no cierra el `EventSource` en el primer `onerror`.
2. El navegador conserva el retry nativo de EventSource.
3. El cliente guarda `lastEventId` y puede reabrir con `last_event_id`.
4. Se agregó polling automático contra `/api/ai/workflows/{runId}` cuando SSE está desconectado.
5. El mensaje de UI cambió de recuperación manual a recuperación automática.
6. `to_sse()` emite eventos en el canal default `message`, dejando el tipo semántico dentro de `event_type`, para que `onmessage` reciba todos los eventos nuevos sin registrar manualmente cada nombre.
7. El backend envía keepalive cada ~10s y headers anti-buffering/keep-alive.
8. El proxy Next.js reenvía `Last-Event-ID` y `last_event_id` al backend.

## Resultado esperado

Si SSE se corta, el timeline sigue recuperando eventos por polling y el EventSource intenta reconectar. El usuario ya no necesita presionar `Actualizar estado` para que el flujo continúe visible.
