# WAOS Optimizer Live Runtime Integration

Date: 2026-04-18

## What is now live

WAOS Optimizer no longer stops at offline proposals and experiments. Promoted control states now influence runtime behavior in these paths:

- response generation:
  - reorders response candidates using the promoted `response_variant`
  - injects promoted `cta` style into candidate specs
  - propagates promoted `prompt_base` into runtime response contract metadata
  - records shadow comparisons when the optimizer-preferred variant differs from the ranker winner
- specialist routing:
  - overrides the chosen specialist with the promoted `routing_specialist`
- handoff policy:
  - can bias toward bot-first or human-first handoff decisions under explicit guardrails
- preferred channel:
  - propagates promoted `preferred_channel` into runtime response contract and followup/proactive metadata
- followups:
  - applies promoted `timing`, `collections_template`, `reactivation_template`, and `scheduling_template`
- proactive reasoning:
  - biases proactive candidate priority toward the promoted `playbook_proactive`
  - propagates preferred channel and template version metadata into proactive candidates

## Guardrail behavior

The live runtime integration is intentionally conservative:

- it does not bypass verification
- it does not force unsafe handoff suppression when the user explicitly asks for a human
- it records shadow evidence for response variant divergence rather than hard-switching blindly
- it keeps optimizer influence in metadata when a downstream subsystem does not yet support full native swapping

## Main files

- `backend/app/optimizer_runtime.py`
- `backend/app/agent_runtime.py`
- `backend/app/ai.py`
- `backend/app/proactive_reasoning_runtime.py`
- `backend/tests/test_optimizer_runtime_live_integration.py`

## Next hardening pass suggested

To make the optimizer fully end-to-end, the next pass should make downstream delivery systems consume optimizer-selected template/version IDs directly during send and should wire prompt-base overrides into the primary prompt compiler instead of metadata-only propagation.
