# WAOS Human Ops Supervision Runtime Upgrade

## Objective

Close the gap between AI automation and human operation by making the human layer feel like a modern, AI-native contact center.

This upgrade adds explicit supervision primitives on top of the existing inbox, takeover, copilot and review foundations.

## What changed

### 1. Structured internal notes

New persistence for private/internal notes:

- `conversation_internal_notes`
- category
- priority
- risk level
- risk flags
- next steps
- sources
- visibility

This turns freeform notes into operational artifacts that can be reused by takeover briefs, copilot and supervisor views.

### 2. AI-native reply suggestions for humans

New human copilot suggestions now include:

- suggested reply
- explanation of why that reply is recommended
- grounded sources
- explicit risk assessment
- next best action
- macro suggestions
- AI reactivation guardrails

Persistence:

- `human_reply_suggestions`

### 3. Auto-brief at takeover

New takeover briefing runtime generates operational summaries for humans and supervisors:

- executive summary
- latest inbound/outbound context
- queue and SLA state
- pending items
- next best action
- attached internal notes
- objections / risks
- macro shortlist

Persistence:

- `conversation_takeover_briefs`

The explicit takeover endpoint now generates a brief automatically.

### 4. Failed takeover detection

WAOS now detects when the handoff did not actually resolve the situation, based on signals like:

- multiple inbound messages after takeover
- last message still being inbound
- freeze expired without resolution
- no meaningful human action after escalation

This signal is fed into:

- decision support
- supervisor console
- AI reactivation guardrails
- reply suggestion risk layer

### 5. Guardrailed AI reactivation

AI reactivation is no longer a blind toggle.

Before reactivating, WAOS checks blockers such as:

- failed takeover still unresolved
- payment-sensitive state
- sensitive intent still active

Response now returns:

- current conversation
- reactivation decision
- blockers / reasons
- reactivation plan

### 6. Supervisor console

New supervisor-level snapshot with:

- open conversations
- active takeovers
- failed takeovers
- unassigned work
- average response latency
- occupancy / workload by team queue
- QA scorecards
- coaching loops
- recommended supervisor actions

Persistence:

- `supervisor_console_snapshots`

### 7. QA and coaching loops

New QA aggregation logic produces:

- QA by agent
- QA by bot
- coaching recommendations for low-quality patterns

Persistence foundation:

- `coaching_recommendations`

## Runtime integration points

### Conversation decision support

`/api/v1/conversations/{conversation_id}/decision-support` now includes:

- `takeover_brief`
- `failed_takeover`
- `reactivation_guardrails`
- `reply_suggestion`

### Conversations API

New endpoints:

- `POST /api/v1/conversations/{conversation_id}/internal-notes/structured`
- `GET /api/v1/conversations/{conversation_id}/takeover-brief`
- `GET /api/v1/supervisor/console`
- `GET /api/v1/qa/overview`

### Engagement copilot

`POST /api/v1/conversations/{conversation_id}/copilot` now returns richer human guidance with:

- explanation
- sources
- risk
- suggested reply

## Main files added or updated

### New

- `backend/app/human_ops_runtime.py`
- `backend/tests/test_human_ops_supervision_runtime.py`
- `docs/WAOS_HUMAN_OPS_SUPERVISION_RUNTIME.md`

### Updated

- `backend/app/migrations.py`
- `backend/app/application/conversation_service.py`
- `backend/app/api/routers/conversations.py`
- `backend/app/api/handlers/engagement.py`
- `backend/app/schemas/conversations.py`

## Why this matters

Before this upgrade, WAOS had handoff and reviews, but the human layer still felt like manual inbox management assisted by AI.

After this upgrade, the human layer behaves more like supervised execution:

- private context is structured
- handoffs generate briefings
- supervisors get operational telemetry
- humans receive grounded suggestions with risk
- AI reactivation is policy-aware
- QA produces coaching loops

That makes the overall system feel less like “bot plus inbox” and more like an AI-native operations stack.
