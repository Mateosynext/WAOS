# WAOS Growth OS Master Scheduler

## Qué cambia

Growth OS deja de ser una capa manual y pasa a operar como **scheduler maestro** del revenue loop.

Ahora el sistema puede:

- correr ciclos automáticos por bot
- detectar oportunidades desde el proactive engine
- priorizar objetivos por scorecards
- materializar targets en modo recommend o autopilot
- persistir control state y foco activo por bot
- inyectar ese foco activo al runtime conversacional para priorizar specialist, tools y playbooks

## Componentes nuevos

### 1. Control plane por bot

Tabla: `growth_os_control_states`

Guarda:
- habilitación global
- scheduler enable/disable
- modo (`recommend`, `autopilot`, `execute`)
- intervalo de ciclo
- goals por defecto
- max targets
- auto execute
- scorecard window
- prioridades de runtime (`specialist`, `tools`, `handoffs`, `playbooks`)
- `latest_run_id`
- `last_started_at`, `last_completed_at`, `next_scheduled_at`
- `last_status`
- `last_summary_json`

### 2. Scheduler maestro en worker

`backend/worker.py` ahora corre `process_growth_os_cycles()` dentro de `run_once()`.

Ese paso:
- identifica bots due
- ejecuta `run_growth_os_master_scheduler()`
- corre `run_growth_os_cycle()` usando la configuración del control plane
- actualiza `growth_os_control_states`

### 3. Foco activo consumible por runtime

`active_growth_os_focus()` devuelve el target activo más relevante para:
- conversación actual
- contacto actual
- fallback global del bot

El foco activo se usa para:
- forzar specialist preferido
- inyectar channel / objective / timing al execution plan
- promover `execute_tool` o `trigger_playbook` desde self state cuando el riesgo es aceptable
- materializar el candidate específico de Growth OS cuando self state decide playbook

## Configuración

Se agregó `growth_os` al `default_bot_config()`.

Estructura base:

```json
{
  "growth_os": {
    "enabled": true,
    "scheduler": {
      "enabled": true,
      "mode": "recommend",
      "interval_minutes": 30,
      "goals": ["payments", "reactivation", "retention", "appointments"],
      "max_targets": 5,
      "auto_execute": false,
      "include_suppressed": false,
      "scorecard_window": "28d"
    },
    "runtime_priority": {
      "enabled": true,
      "contact_focus_hours": 72,
      "prioritize_specialist": true,
      "prioritize_tools": true,
      "prioritize_handoffs": true,
      "prioritize_playbooks": true
    }
  }
}
```

## Integración con runtime

### agent runtime

`orchestrate_runtime_turn()` ahora:
- carga `growth_os_focus`
- aplica foco a specialist route
- aplica foco al execution plan
- pasa el foco a `build_turn_self_state()`
- adjunta el foco a la decisión final

### self state

`build_turn_self_state()` ahora puede:
- elevar `next_best_action` a `execute_tool`
- elevar `next_best_action` a `trigger_playbook`
- generar `tool_plan` desde el objetivo activo de Growth OS cuando aplica

### materialización de playbook

`maybe_trigger_self_state_playbook()` primero intenta materializar el `candidate_id` exacto del foco activo de Growth OS antes de reevaluar candidatos.

## Validación corrida

- `pytest -q backend/tests/test_growth_os_runtime.py backend/tests/test_growth_os_master_runtime.py backend/tests/test_self_state_runtime.py`
- `python -m compileall backend/app backend/worker.py`

## Límite actual

Growth OS ya agenda, prioriza y empuja el runtime.
Todavía no reemplaza completamente todos los dispatchers finales de canal como único orquestador universal de salida.
