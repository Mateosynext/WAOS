# WAOS Maintainability Review — 2026-04-18

## Objetivo
Reducir riesgo de crecimiento desordenado en módulos runtime muy grandes y dejar un criterio explícito para próximas iteraciones.

## Hallazgos principales
Los módulos más grandes y sensibles en este corte son:

- `backend/app/ai.py`
- `backend/worker.py`
- `backend/app/application/tool_execution_service.py`
- `backend/app/application/operational_control_service.py`

### Riesgos observados
- mezcla de responsabilidades de dominio, persistencia, serialización y control de flujo en un mismo archivo
- alto costo de lectura para cambios pequeños
- mayor superficie de regresión al tocar lógica transversal
- pruebas con cobertura amplia, pero con módulos difíciles de aislar por unidad

## Mejora aplicada en este paquete
Se extrajo la capa de adapters y políticas de `tool_execution_service.py` hacia:

- `backend/app/application/tool_execution_adapters.py`

Con esto:
- el archivo principal de servicio queda más enfocado en coordinación del caso de uso
- los adapters quedan aislados por responsabilidad operacional
- futuras integraciones nuevas pueden entrar sin seguir inflando el servicio principal

## Siguientes candidatos recomendados
### `operational_control_service.py`
Separar en módulos por responsabilidad:
- resolución de filtros / query params
- scorecards y métricas
- serialización de vistas API
- reglas de alertas y handoff

### `worker.py`
Separar por pipeline:
- jobs operativos
- outbox / delivery
- reglas de alertas
- report generation / publication
- scheduler loop

### `ai.py`
Separar por capas:
- clasificación
- generación
- tono / idioma / voice layer
- memory updates
- orchestration pipeline

## Criterio sugerido de refactor
Cuando un archivo mezcle 3 o más de estas categorías, debe dividirse:
- acceso a datos
- lógica de negocio
- serialización / respuesta
- integración externa
- control de flujo / jobs

## Impacto esperado
- menor tiempo de onboarding para cambios en runtime
- diffs más pequeños y revisables
- menor probabilidad de side effects al evolucionar features enterprise
