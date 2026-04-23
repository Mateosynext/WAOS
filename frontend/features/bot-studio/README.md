# Bot Studio feature modules

Esta carpeta existe para romper el patrón de mega wizard y aislar el producto por dominio.

## Reglas
- `create` y `reconfigure` no comparten experiencia principal.
- El shell puede compartirse, pero cada módulo vive desacoplado.
- Validación, mappers, payload builders y servicios quedan fuera del componente de pantalla.
- `frontend/app/bot-studio/BotStudioWizardClient.tsx` ya es un shim fino de compatibilidad; la orquestación real vive en `BotStudioFlowClient.tsx`.
