# WAOS Optimizer

WAOS Optimizer is the closed-loop optimization brain for runtime decisions. It reads outcome scorecards, identifies winners and losers, proposes configuration changes, spins up shadow/A-B experiments, promotes or degrades candidates with guardrails, and leaves a complete audit trail for every change.

## What it optimizes

- prompt base (`prompt_version`, `prompt_run`, `specialist_prompt`)
- response variant (`response_variant`)
- CTA and business templates (`template`, `template_version`, `nba_policy`)
- timing and preferred channel (`timing_policy`, `channel`)
- routing by specialist (`specialist_agent`, `routing_rule`, `agent_routing_run`)
- proactive playbooks (`playbook`, `playbook_version`)
- handoff policy (`handoff`, `escalation_policy`, `policy_profile`)
- collections / reactivation / scheduling templates

## New API

- `GET /api/v1/optimizer/overview`
- `GET /api/v1/optimizer/proposals`
- `POST /api/v1/optimizer/run`
- `POST /api/v1/optimizer/evaluate`

## Runtime model

1. Read the latest outcome scorecards for configured targets.
2. Rank candidates by outcome score, confidence and primary metric.
3. Detect winners and losers per optimization target.
4. Create machine-readable proposals with rationale, evidence and change sets.
5. Open a shadow or A/B experiment automatically.
6. Promote or degrade automatically when confidence, guardrails and shadow evidence pass.
7. Persist the resulting control state and decision audit.

## Persistence

New optimizer tables:

- `optimizer_cycles`
- `optimizer_proposals`
- `optimizer_experiments`
- `optimizer_control_states`
- `optimizer_change_audits`

The optimizer also writes applied decisions to `outcome_optimization_decisions` and audit logs.

## Guardrails

Auto-promotion is blocked when the candidate fails guardrails or does not beat the loser by the configured minimum delta. Shadow mode is preferred when confidence is not yet high enough for direct A/B or promotion.
