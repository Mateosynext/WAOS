# WAOS Guided Vertical Onboarding

## Objetivo
Pasar de activacion generica a un wizard verticalizado que deje operativo a un negocio por industria en horas, no dias.

## Que agrega
- wizard guiado por `vertical` y `subvertical`
- defaults inteligentes para:
  - prompts y tono
  - knowledge seed
  - catalogo inicial
  - CTAs
  - flows y playbooks recomendados
  - integraciones planeadas
  - reglas y escalamiento
- aplicacion real al runtime existente:
  - `organizations.vertical`
  - `bots.vertical`
  - `bot_behavior_settings`
  - `bot_response_templates`
  - `catalog_services`
  - `knowledge_documents`
  - `integration_connections`

## API
- `GET /api/v1/onboarding/wizard/verticals`
- `GET /api/v1/onboarding/wizard/blueprint`
- `POST /api/v1/onboarding/wizard/start`
- `GET /api/v1/onboarding/wizard/{wizard_id}`
- `POST /api/v1/onboarding/wizard/{wizard_id}/steps/{step_key}`
- `POST /api/v1/onboarding/wizard/{wizard_id}/apply`

## Persistencia
- `vertical_onboarding_wizards`
- `vertical_onboarding_step_runs`

## Flujo
1. elegir vertical y subvertical
2. capturar datos minimos del negocio
3. ajustar catalogo y CTAs
4. sembrar knowledge y fuentes vivas
5. escoger integraciones y reglas
6. aplicar pack al runtime real

## Resultado
El tenant queda con un setup base coherente por industria, menor variabilidad y menor tiempo a valor.
