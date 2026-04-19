# WAOS Product Integration - Phase 3

## Scope landed in code

This phase continues on top of phase 2 and adds three product foundations without breaking the current multi-tenant contract model:

1. **Inbox ownership and auto-assignment**
2. **Bot simulation and draft snapshots**
3. **Agenda resource capacity foundations**

All changes were added as additive extensions over the existing FastAPI + PostgreSQL + Next.js structure and avoid importing from legacy code outside `backend/app/legacy`.

## Backend

### Inbox ownership and auto-assignment
- Added `conversation_assignment_history`
- Added ownership summary and routing helpers inside `ConversationService`
- Added endpoints:
  - `GET /api/v1/inbox/ownership`
  - `POST /api/v1/inbox/auto-assign`
  - `POST /api/v1/conversations/{conversation_id}/assign`
- Assignment writes owner changes back to `conversations.assigned_user_id`
- Auto-assignment uses role queue + least-open-load as an initial deterministic strategy
- Human takeover is enabled when a conversation is explicitly assigned

### Bot simulation and draft snapshots
- Added `bot_simulation_cases`
- Added `bot_simulation_runs`
- Added `bot_simulation_run_results`
- Added endpoints:
  - `GET /api/v1/bots/{bot_id}/simulation-cases`
  - `POST /api/v1/bots/{bot_id}/simulation-cases`
  - `GET /api/v1/bots/{bot_id}/simulation-runs`
  - `POST /api/v1/bots/{bot_id}/simulate`
  - `POST /api/v1/bots/{bot_id}/versions/draft-snapshot`
- The simulator is intentionally simple and safe in this phase:
  - runs over saved cases
  - compares expected action / expected queue / escalation expectation
  - stores pass/fail outcomes per case

### Agenda resource capacity foundations
- Added `agenda_resources`
- Added `agenda_resource_capacity_rules`
- Added `appointment_resource_assignments`
- Added endpoints:
  - `GET /api/v1/agenda/resources`
  - `POST /api/v1/agenda/resources`
  - `GET /api/v1/agenda/capacity-rules`
  - `POST /api/v1/agenda/capacity-rules`
  - `GET /api/v1/agenda/capacity/overview`
  - `POST /api/v1/appointments/{appointment_id}/assign-resource`
- Capacity overview now reports:
  - declared resources
  - active rules
  - weekly declared slots
  - upcoming appointments without resource

## Frontend

### Inbox
- Added queue ownership summary to `/inbox`
- Added auto-assignment action from the inbox surface
- Added visible owner workload cards

### Bot Studio
- Added a simulation section to `/bot-studio`
- Allows creating simulation cases
- Allows running simulation batches
- Allows saving draft snapshots before risky changes

### Agenda
- Added resource and capacity rule management to `/agenda`
- Added first utilization summary around resources, declared slots and unassigned appointments

## Database and migrations

Phase 3 is registered through a new additive migration:
- `2026-04-16-phase3-assignment-simulation-capacity-v1`

This phase only adds tables and does not require destructive schema rewrites.

## Permissions, audit and rollout notes

- Assignment history is persisted when the phase 3 tables are present
- Bot simulations are isolated from production channels
- Agenda capacity is additive and does not block the existing appointment model
- This phase is suitable for rollout behind the same tenant-scoped release pattern used in earlier phases

## Validation performed

- Python compile validation on touched backend modules
- Backend tests in `backend/tests/test_activation_foundations.py`
- Added a phase 3 coverage test for assignment, simulations and capacity

## Known limitations intentionally left for the next phase

- Auto-assignment is deterministic but still basic; it does not yet combine skills, schedules and SLA pressure
- Simulator is useful for regression control but is not yet a fully faithful runtime emulator
- Capacity does not yet enforce booking conflicts at all booking entry points
- Frontend repo still contains broad pre-existing typecheck debt unrelated to phase 3

## Recommended next phase

1. Skill-aware auto-assignment with capacity and SLA weighting
2. Bot simulator with diff view and publish gates
3. Real capacity enforcement on booking and rescheduling
4. Pipeline board + stage automation wired to ownership and agenda availability
