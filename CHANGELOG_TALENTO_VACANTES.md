# Cambios aplicados: módulo Talento / Vacantes por bot

## Backend
- Se agregó `backend/app/talent_runtime.py` con:
  - configuración por bot para talento/vacantes
  - detección de candidatos y trabajadores
  - respuestas específicas para vacantes, sueldo, requisitos, ubicación y entrevista
  - fallback explícito para entrevistas sin horario
  - registro de candidatos al confirmar asistencia
- Se agregaron rutas nuevas:
  - `GET /api/v1/bots/{bot_id}/talent/overview`
  - `PATCH /api/v1/bots/{bot_id}/talent/policy`
  - `POST /api/v1/bots/{bot_id}/talent/vacancies`
  - `PATCH /api/v1/bots/{bot_id}/talent/vacancies/{vacancy_id}`
  - `GET /api/v1/bots/{bot_id}/talent/candidates`
  - `POST /api/v1/bots/{bot_id}/talent/candidates/confirm`
- Se agregó persistencia para `talent_candidates` con índices por bot, organización y contacto.
- Se integró la lógica de talento al pipeline conversacional para:
  - reconocer trabajadores
  - detectar intención de vacante
  - nunca quedarse callado cuando faltan horarios de entrevista
  - registrar candidato después de confirmar entrevista

## Frontend
- Se agregó la ruta `/vacantes`.
- Se agregó navegación principal a `Vacantes`.
- Se agregaron acciones server-side para:
  - guardar política del módulo
  - crear vacantes
  - registrar confirmaciones manuales de candidatos
- Se agregaron contratos y fetchers para `TalentOverview`.

## Reglas implementadas
- Las vacantes viven por bot por default.
- Los horarios de entrevista se toman del portal.
- Si no hay horarios definidos, el bot responde con fallback seguro.
- El bot nunca se queda callado.
- El sueldo se toma del portal y solo se muestra si está configurado.
- Los candidatos se registran al confirmar asistencia a entrevista.
- Se agregó reconocimiento básico de trabajadores para no tratarlos como postulantes.

## Validación
- Backend: `PYTHONPATH=. pytest -q backend/tests` → 34 passed.
- Frontend: se dejó integrado el módulo nuevo, pero la validación completa de typecheck del proyecto no quedó confiable en este entorno porque el frontend ya traía errores/resolución incompleta de dependencias fuera del módulo nuevo.
