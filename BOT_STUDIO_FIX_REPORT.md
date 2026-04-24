# Bot Studio blindado - fix report

Aplicado sobre `waos_web_fixed_botstudio_final.zip`.

## Endurecimiento incluido

- Sanitizacion global de placeholders de ruta/query: `-`, `null`, `undefined`, `NaN`, en mayusculas/minusculas.
- `buildBotStudioHref()` ya filtra valores sucios antes de construir URLs canonicas.
- `/bot-studio` y `/bot-studio/[mode]/[[...slug]]` limpian query params antes de redirigir o cargar datos.
- `?bot=-` ya no fuerza modo `reconfigure`; create queda explicitamente create.
- `loadBotStudioRoute()` ya limita trabajo RSC por paso activo.
- `loadBotStudioRoute()` ahora degrada fetches opcionales con `safeOptional()` para que errores en wizard, catalogo, bots, blueprint o vertical-profile no tumben el RSC payload.
- Create carga blueprint/profile tambien en pasos editables directos: `offer`, `knowledge`, `integrations`, `review`, `validate`, `apply`, `success`.
- Client preview dedupe por selection key para evitar fetches repetidos del mismo blueprint/profile.
- Reactive preview puede seedear secciones editables vacias despues de cargar, sin pisar datos ya escritos por el usuario.
- FAQs quedan en formato `pregunta | respuesta`, compatible con guards y payload builders.
- `useBotStudioFlowStateModel.ts` fue refactorizado a 317 lineas para cumplir la prueba de arquitectura interna y separar helpers.
- Nuevos modulos:
  - `features/bot-studio/flow/wizardPreviewSeed.ts`
  - `features/bot-studio/flow/wizardScreenModels.ts`
- Tests de regresion actualizados para sanitizacion, prefill, seed reactivo, dedupe y safe optional fetches.

## Validacion estatica realizada aqui

- Se verifico line count de `useBotStudioFlowStateModel.ts` <= 430.
- Se verifico que no haya patrones peligrosos conocidos como `bot=-`, `safeText(data.botId)`, `Boolean(routeBotId)` o inference create->reconfigure por bot truthy.
- Se verifico estructura del ZIP con `unzip -t` al generar el artefacto.

## Validacion pendiente en tu entorno

Este entorno no pudo completar `npm ci`/`tsc` porque la instalacion de dependencias se quedo sin responder. En local/Vercel corre:

```bash
cd frontend
npm ci
npm run typecheck
npm run test:node
npm run build
```

## Rutas criticas a probar en browser

- `/bot-studio?mode=create&bot=-`
- `/bot-studio/create?bot=-`
- `/bot-studio/create/knowledge?bot=-&organization_id=<org>&vertical=<vertical>`
- `/bot-studio/create/offer?organization_id=<org>&vertical=<vertical>&subvertical=<subvertical>`
- `/bot-studio/create/integrations?organization_id=<org>&vertical=<vertical>&subvertical=<subvertical>`
- Avance normal: context -> identity -> offer -> knowledge -> integrations -> review -> validate -> apply.
