# WAOS Resilience Runtime Upgrade

## Included in this upgrade

- Real circuit-breaker module in `backend/app/circuit_breaker.py`
- Defensive client/public rate limiter in `backend/app/rate_limiter.py`
- Backpressure and retry/DLQ orchestration in `backend/app/backpressure.py`
- Worker loop with adaptive polling and dynamic batch sizing based on queue depth
- Retry-budget enforcement for jobs, outbox deliveries, integration syncs, and report generation
- Dead-letter registry populated automatically when retry budgets are exhausted
- Granular module health output for database, workers, AI, WhatsApp, payments, and graceful degradation
- Defensive inbound spam throttling before the normal tenant rate-limit layer
- Circuit metadata enriched with organization/module context for OpenAI and Meta calls

## New environment variables

- `WORKER_MIN_POLL_SECONDS`
- `WORKER_MAX_POLL_SECONDS`
- `WORKER_BACKPRESSURE_BATCH_CEILING`
- `WORKER_RETRY_BUDGET_WINDOW_SECONDS`
- `INBOUND_SPAM_WINDOW_SECONDS`
- `INBOUND_SPAM_MAX_EVENTS`
- `PUBLIC_INGEST_WINDOW_SECONDS`
- `PUBLIC_INGEST_MAX_EVENTS`
- `OPENAI_CIRCUIT_FAILURE_THRESHOLD`
- `OPENAI_CIRCUIT_OPEN_MINUTES`
- `META_CIRCUIT_FAILURE_THRESHOLD`
- `META_CIRCUIT_OPEN_MINUTES`

## Runtime behavior changes

### Graceful degradation

When OpenAI is unavailable or its circuit is open, the runtime continues on heuristic classification/generation fallback paths instead of crashing.

### Backpressure

The worker now:

- grows its claim batch size when backlog pressure rises
- reduces sleep time when the queue is hot
- keeps longer sleep only when the queue is cold

### Dead letters and retry budgets

The worker no longer retries forever. When retry budgets are exhausted or a delivery is non-retryable, the event is quarantined in `dead_letter_events` and the source row is moved to `dead_letter`.
