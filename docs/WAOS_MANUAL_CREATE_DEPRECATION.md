# WAOS Manual Create Deprecation

Default producción:
- `NEXT_PUBLIC_ENABLE_AI_COMMAND_CENTER=true`
- `NEXT_PUBLIC_ENABLE_MANUAL_BOT_CREATE=false`
- `NEXT_PUBLIC_ENABLE_AI_WORKFLOW_STREAM=true`

Las rutas `/bot-studio/create/*` redirigen a `/bot-studio` salvo que el feature flag interno esté activo. Reconfigure sigue disponible para bots existentes.
