# WAOS Self State Runtime

WAOS now computes `self_state` at two levels:

- **turn self_state**: per inbound turn
- **conversation self_state**: rolling operational state for the conversation

## Core fields

- `confidence`
- `uncertainty_reason`
- `evidence_coverage`
- `execution_readiness`
- `risk_if_send`
- `need_verification`
- `need_tool`
- `need_human`
- `next_best_action`
- `learning_opportunity`

## Operational decisions driven by self_state

The runtime can now steer actions toward:

- `respond`
- `verify`
- `request_missing_data`
- `handoff` via `escalate`
- `wait`
- `trigger_playbook`
- `execute_tool` when the turn is tool-ready and a concrete tool plan exists

## Runtime wiring

Self state is computed inside `agent_runtime.orchestrate_runtime_turn()` after:

1. message understanding
2. grounded context assembly
3. specialist routing
4. execution planning
5. first-pass decisioning

Then `self_state` can override the first-pass decision conservatively.

## Persistence

New tables:

- `runtime_self_state_turns`
- `runtime_self_state_conversations`

These preserve the full JSON snapshot plus queryable summary columns.

## Playbook integration

When `next_best_action = trigger_playbook`, the runtime evaluates proactive candidates for the current contact/conversation and materializes the strongest candidate.

## Tool execution note

The runtime can now select `execute_tool` and persist a structured `tool_plan` in self-state. In this pass, the operational brain is deciding and tracing tool readiness natively, while the final adapter auto-commit layer remains conservative and governed.
