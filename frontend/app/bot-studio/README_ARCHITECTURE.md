# Guardrail de arquitectura para Bot Studio

`BotStudioWizardClient.tsx` quedó reducido a un adaptador fino de rutas hacia `BotStudioFlowClient.tsx`.

## No hacer
- seguir agregando lógica de negocio ahí
- mezclar create y reconfigure en la misma experiencia
- exponer autosave, diagnósticos o overrides como parte central del flujo
- unir review, dry run, confirm y success en una sola pantalla

## Sí hacer
- mover estado por dominio a `frontend/features/bot-studio/*`
- mover mappers y payload builders fuera de la pantalla
- validar por etapa
- usar un shell común con contenido desacoplado por módulo
