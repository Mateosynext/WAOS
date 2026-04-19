# AI cost optimization + long-term memory updates

This package includes the following product upgrades:

## 1) AI cost optimization
- Semantic cache thresholds moved to runtime settings.
- Prompt compression budgets moved to runtime settings.
- Model mix configurable (`fast_model`, `complex_model`).
- Micro-batch context for near-simultaneous inbound messages.
- Embeddings/knowledge query cache with TTL.
- Instant FAQ / knowledge shortcut path that can answer without calling OpenAI.
- AI dashboard now exposes cache efficiency and optimization profile.
- Streaming preview endpoint added:
  - `GET /api/v1/conversations/{conversation_id}/ai/stream-preview?message=...`

## 2) Context and long-term memory
- New `memory_episodes` table for episodic memory.
- Cross-bot memory support via org-level episodes.
- Runtime-configurable checkpoint cadence and summarization thresholds.
- Episodic recall added into response generation.
- AI dashboard now exposes memory runtime metrics.
- Global settings/UI extended with JSON config blocks for:
  - `ai_optimization`
  - `memory_runtime`

## Key backend files changed
- `backend/app/ai.py`
- `backend/app/world_class.py`
- `backend/app/runtime_settings.py`
- `backend/app/application/runtime_service.py`
- `backend/app/api/routers/runtime.py`
- `backend/app/schemas/system.py`
- `backend/app/static/index.html`
- `backend/app/static/app.js`

## Added test coverage
- `backend/tests/test_ai_cost_and_memory_runtime.py`
