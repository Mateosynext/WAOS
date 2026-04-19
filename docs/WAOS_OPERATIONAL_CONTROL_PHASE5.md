# WAOS Operational Control Phase 5

This phase extends the phase 4 operational control epic with:

- mass rescheduling preview and execution with capacity-aware slot matching
- worker execution for scheduled bot state transitions
- enterprise-grade guardrails for WhatsApp operational numbers using allowed intents
- optional second approval for high-impact commands behind `ops_control_dual_approval_enterprise_v1`
- portal metrics for the last 7 days of operational commands

## Backend additions

- `GET /api/v1/client/operations/metrics`
- `POST /api/v1/client/operations/commands/{command_id}/approve`
- `POST /api/v1/client/operations/reschedule-batches/preview`
- `POST /api/v1/client/operations/reschedule-batches/execute`
- worker support for `operational_state_transition_execute`
- migration `2026-04-16-phase5-operational-control-enterprise-v1`

## Frontend additions

- portal metrics cards for command volume and high-risk commands
- mass reschedule guided forms in `/client/operaciones`
- second-approval action for enterprise-protected commands

## Verification

- `pytest -q backend/tests/test_operational_control_phase5.py backend/tests/test_operational_control_phase4.py backend/tests/test_activation_foundations.py`
- backend `py_compile` for touched python files
- local TypeScript transpile check for touched frontend files
