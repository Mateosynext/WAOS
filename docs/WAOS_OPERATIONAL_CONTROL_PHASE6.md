# WAOS Operational Control Phase 6

## Scope
This phase hardens operational control for enterprise use on top of phase 5.

## Added in this phase

### 1. Fine-grained WhatsApp scope enforcement
Authorized operational numbers can now be restricted by:
- branch names
- resource ids
- resource names
- service names
- allowed intents

Those scopes are enforced when selecting affected appointments and when resolving operational previews over WhatsApp.

### 2. Operational rate limits
WhatsApp operational commands now enforce rate limits at two levels:
- per phone number
- per phone number plus high-impact intent

When rate limits are exceeded:
- the command is rejected safely
- an operational alert is created
- the actor receives a clear rate-limit response

### 3. Persistent operational alerts
New table:
- `operational_command_alerts`

Alerts are generated for:
- unauthorized WhatsApp command attempts
- forbidden intents for an authorized number
- rate-limit violations
- execution failures
- partial reschedule outcomes

New endpoint:
- `GET /api/v1/client/operations/alerts`

The client portal now shows open operational alerts.

### 4. Undo for executed commands
Operational commands that already executed can now be undone when reversible.

New endpoint:
- `POST /api/v1/client/operations/commands/{command_id}/undo`

Current undo coverage includes:
- restoring appointments moved by reschedule batches
- cancelling remaining notifications when possible
- marking commands as `reverted` or `partially_reverted`

### 5. Local-time natural language interpretation
Operational date parsing now resolves relative expressions like:
- hoy
- mañana
- el lunes a las 8

using `America/Mexico_City` before converting to UTC for storage and execution.

## Frontend updates
Portal operations now includes:
- alert count in metrics
- alert list
- scope fields for authorized numbers
- scope summary display
- undo action for eligible recent commands

## Security notes
This phase improves safety by combining:
- number authorization
- intent allowlisting
- scope restrictions
- rate limiting
- alerting
- auditability

## Validation
Validated with:
- backend compile on changed files
- targeted backend test suite for phases 4, 5 and 6
- local transpile validation of changed frontend files

## Remaining hardening after phase 6
Still useful for later phases:
- dedicated observability dashboards outside portal summary
- richer undo coverage for every batch side effect
- more granular branch or professional policies at role level
- deeper frontend UX polish around enterprise approvals and alert workflows
