from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_rate_limit_storage_is_bounded_and_not_defaultdict() -> None:
    hardening = _read("app/hardening.py")
    assert "defaultdict" not in hardening
    assert "OrderedDict" in hardening
    assert "rate_limit_memory_max_buckets" in hardening
    assert "popitem(last=False)" in hardening
    assert "_RATE_BUCKETS[key]" not in hardening


def test_distributed_rate_limit_backend_is_supported() -> None:
    hardening = _read("app/hardening.py")
    assert "_check_distributed_rate_limit" in hardening
    assert "redis.asyncio" in hardening
    assert "_REDIS_RATE_LIMIT_LUA" in hardening
    assert "ZREMRANGEBYSCORE" in hardening
    assert "RateLimitBackendUnavailable" in hardening


def test_production_cannot_use_in_process_only_rate_limiting() -> None:
    config = _read("app/config.py")
    preflight = _read("scripts/preflight_check.py")
    assert "RATE_LIMIT_BACKEND must be redis, valkey, upstash, or gateway in production" in config
    assert "RATE_LIMIT_BACKEND must be redis, valkey, upstash, or gateway in production" in preflight
    assert "RATE_LIMIT_REDIS_URL or REDIS_URL is required" in preflight
    assert "RATE_LIMIT_GATEWAY_ENFORCED must be true" in preflight
