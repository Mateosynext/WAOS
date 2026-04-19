# WAOS Growth OS

WAOS Growth OS turns the proactive engine plus closed-loop outcomes into the operating center of revenue execution.

## What it does

For each cycle, WAOS Growth OS:

1. detects proactive opportunities from real business signals
2. prioritizes which contacts to attack first
3. chooses the business objective
4. chooses the specialist that should own the move
5. chooses timing/channel from the underlying candidate
6. executes by materializing the proactive playbook when autopilot is enabled
7. measures impact using the latest scorecards from the outcomes loop
8. iterates by storing every run and selected target

## Main concepts

### Growth run
A growth run is one operating cycle over the current opportunity pool.

Stored in `growth_os_runs`.

### Growth target
A growth target is a selected contact-opportunity pair with an objective, specialist, timing decision, expected value, supporting scorecards and execution status.

Stored in `growth_os_targets`.

## Sources of truth

Growth OS is intentionally thin and reuses existing subsystems:

- `proactive_reasoning_runtime.evaluate_proactive_candidates(...)` for opportunity detection
- `outcome_scorecard_snapshots` for measured historical impact
- `proactive_reasoning_runtime.materialize_proactive_candidate(...)` for execution in autopilot mode

## Ranking logic

The ranking formula combines:

- current proactive candidate priority
- latest playbook scorecard
- latest specialist scorecard
- latest channel scorecard
- objective-specific business weight
- guardrail penalties for failing scorecards

Current supported business goals:

- `payments`
- `appointments`
- `reactivation`
- `retention`

## API

### `GET /api/v1/growth-os/overview`
Returns the latest run, goal distribution, scorecard summary and recent proactive runs.

### `POST /api/v1/growth-os/run`
Runs one growth cycle.

Key body fields:

- `organization_id`
- `bot_id`
- `goals`
- `mode`: `recommend | autopilot | execute`
- `auto_execute`
- `max_targets`
- `scorecard_window`

### `GET /api/v1/growth-os/runs`
Lists historical growth runs with selected targets.

## Product meaning

This makes WAOS behave less like a chat responder and more like a growth operating system:

- opportunity discovery becomes continuous
- specialist choice becomes measurable
- objective selection becomes explicit
- execution becomes batch-operational, not just conversational
- the product value shifts toward appointments, payments, reactivation and retention outcomes
