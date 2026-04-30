# Distributed rate limiting

WAOS must not rely on process-local rate limiting in production. Multiple API replicas need a shared limiter, otherwise attackers can bypass limits by spreading traffic across instances and can exhaust memory by creating high-cardinality client keys.

## Required production configuration

Choose exactly one primary production strategy:

1. Redis / Valkey / Upstash Redis-compatible endpoint:
   - `SECURITY_RATE_LIMIT_ENABLED=true`
   - `RATE_LIMIT_BACKEND=redis` (or `valkey`, or `upstash`)
   - `RATE_LIMIT_REDIS_URL=rediss://...` or `REDIS_URL=rediss://...`
   - `RATE_LIMIT_REDIS_TIMEOUT_SECONDS=0.5`
   - `RATE_LIMIT_KEY_PREFIX=waos:rate-limit`

2. External gateway / load balancer enforced limit:
   - `SECURITY_RATE_LIMIT_ENABLED=true`
   - `RATE_LIMIT_BACKEND=gateway`
   - `RATE_LIMIT_GATEWAY_ENFORCED=true`
   - Configure equivalent global, auth, and webhook limits at the gateway.

`RATE_LIMIT_BACKEND=memory` is allowed only for local development and tests. Production startup and preflight reject it. The in-process limiter remains as a bounded fallback/defense-in-depth implementation and uses `RATE_LIMIT_MEMORY_MAX_BUCKETS` plus LRU eviction to avoid unbounded bucket growth.

## Fail-closed behavior

When `RATE_LIMIT_BACKEND` is `redis`, `valkey`, or `upstash`, WAOS returns `503 rate_limit_backend_unavailable` if the distributed backend is unavailable. It does not silently fall back to process-local rate limiting in production.

## Gateway limits to mirror

Keep gateway/load-balancer limits aligned with application limits:

- global: `GLOBAL_RATE_LIMIT_MAX_REQUESTS` per `GLOBAL_RATE_LIMIT_WINDOW_SECONDS`
- auth: `AUTH_RATE_LIMIT_MAX_REQUESTS` per `AUTH_RATE_LIMIT_WINDOW_SECONDS` for login/refresh
- webhooks: `WEBHOOK_RATE_LIMIT_MAX_REQUESTS` per `WEBHOOK_RATE_LIMIT_WINDOW_SECONDS`

The app hashes client/scope keys before storing them in Redis to avoid leaking raw IP addresses or client identifiers into Redis key names.
