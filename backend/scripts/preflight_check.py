from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

REQUIRED = [
    "DATABASE_URL", "APP_SECRET", "SECRET_ENCRYPTION_KEY", "PUBLIC_APP_URL", "API_BASE_URL",
    "CORS_ALLOWED_ORIGINS", "ALLOWED_HOSTS", "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "META_VERIFY_TOKEN",
]
WEAK = {"", "change-me", "changeme", "dev", "development", "test", "secret", "super-secret", "replace-me", "replace_me", "example", "default"}


def truthy(k: str, default: str = "false") -> bool:
    return os.getenv(k, default).strip().lower() in {"1", "true", "yes", "on"}


def csv(v: str) -> list[str]:
    return [x.strip() for x in v.split(",") if x.strip()]


def host_from_url(value: str) -> str:
    return urlparse(value).netloc.split("@")[-1].split(":")[0].lower()


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return -1


def main() -> None:
    env = os.getenv("APP_ENV", "").lower()
    if env not in {"production", "prod"} and not truthy("WAOS_FORCE_PRODUCTION_PREFLIGHT"):
        print("production preflight skipped outside production")
        return

    errors: list[str] = []
    for k in REQUIRED:
        if not os.getenv(k):
            errors.append(f"missing required env var: {k}")

    for k in ("APP_SECRET", "SECRET_ENCRYPTION_KEY", "META_VERIFY_TOKEN"):
        v = os.getenv(k, "").strip()
        if v.lower() in WEAK or len(v) < 32:
            errors.append(f"{k} must be a strong non-default secret of at least 32 characters")
    if os.getenv("APP_SECRET", "").strip() == os.getenv("SECRET_ENCRYPTION_KEY", "").strip():
        errors.append("SECRET_ENCRYPTION_KEY must be distinct from APP_SECRET")

    db = os.getenv("DATABASE_URL", "")
    if db and not db.startswith(("postgres://", "postgresql://")):
        errors.append("DATABASE_URL must be PostgreSQL in production")
    if truthy("ENABLE_API_DOCS"):
        errors.append("ENABLE_API_DOCS must be false in production")
    if truthy("USE_FAKE_PROVIDERS") or truthy("USE_FAKE_PAYMENT_PROVIDER") or truthy("WAOS_E2E_FAKE_PROVIDERS"):
        errors.append("fake providers must be disabled in production")
    if not truthy("STARTUP_DB_REQUIRED", "true"):
        errors.append("STARTUP_DB_REQUIRED must remain true in production")
    if not truthy("AUTO_RUN_MIGRATIONS", "true"):
        errors.append("AUTO_RUN_MIGRATIONS must remain true for production deploys")

    for k in ("PUBLIC_APP_URL", "API_BASE_URL"):
        v = os.getenv(k, "")
        if v:
            u = urlparse(v)
            if u.scheme != "https":
                errors.append(f"{k} must use https")
            if "example.com" in v or "localhost" in v or "127.0.0.1" in v:
                errors.append(f"{k} must not use example.com, localhost or loopback hosts")

    public_host = host_from_url(os.getenv("PUBLIC_APP_URL", "")) if os.getenv("PUBLIC_APP_URL") else ""
    api_host = host_from_url(os.getenv("API_BASE_URL", "")) if os.getenv("API_BASE_URL") else ""
    cors_origins = csv(os.getenv("CORS_ALLOWED_ORIGINS", ""))
    allowed_hosts = {item.lower() for item in csv(os.getenv("ALLOWED_HOSTS", ""))}

    if "*" in cors_origins:
        errors.append("CORS_ALLOWED_ORIGINS must not contain wildcard")
    if "*" in allowed_hosts:
        errors.append("ALLOWED_HOSTS must not contain wildcard")
    if public_host and not any(host_from_url(origin) == public_host for origin in cors_origins if "://" in origin):
        errors.append("CORS_ALLOWED_ORIGINS must include PUBLIC_APP_URL host")
    if api_host and api_host not in allowed_hosts:
        errors.append("ALLOWED_HOSTS must include API_BASE_URL host")

    if not truthy("SECURE_COOKIES", "true"):
        errors.append("SECURE_COOKIES must be true in production")
    if not truthy("SECURITY_HARDENING_ENABLED", "true"):
        errors.append("SECURITY_HARDENING_ENABLED must be true in production")
    if not truthy("ENFORCE_HTTPS", "true"):
        errors.append("ENFORCE_HTTPS must be true in production")
    if not truthy("REJECT_UNTRUSTED_PROXY_HEADERS", "true"):
        errors.append("REJECT_UNTRUSTED_PROXY_HEADERS must be true in production")
    if not truthy("REQUIRE_SIGNED_WEBHOOKS", "true"):
        errors.append("REQUIRE_SIGNED_WEBHOOKS must be true in production")
    if not truthy("SECURITY_RATE_LIMIT_ENABLED", "true"):
        errors.append("SECURITY_RATE_LIMIT_ENABLED must be true in production")
    rate_limit_backend = os.getenv("RATE_LIMIT_BACKEND", "").strip().lower()
    if rate_limit_backend in {"", "memory", "local", "inprocess", "in-process"}:
        errors.append("RATE_LIMIT_BACKEND must be redis, valkey, upstash, or gateway in production")
    elif rate_limit_backend in {"redis", "valkey", "upstash"}:
        if not (os.getenv("RATE_LIMIT_REDIS_URL") or os.getenv("REDIS_URL")):
            errors.append("RATE_LIMIT_REDIS_URL or REDIS_URL is required for distributed rate limiting")
    elif rate_limit_backend == "gateway":
        if not truthy("RATE_LIMIT_GATEWAY_ENFORCED"):
            errors.append("RATE_LIMIT_GATEWAY_ENFORCED must be true when RATE_LIMIT_BACKEND=gateway")
    else:
        errors.append("RATE_LIMIT_BACKEND must be one of: redis, valkey, upstash, gateway")
    if int_env("RATE_LIMIT_MEMORY_MAX_BUCKETS", 10000) < 100:
        errors.append("RATE_LIMIT_MEMORY_MAX_BUCKETS must be >= 100 for bounded in-process fallback")
    if int_env("MAX_REQUEST_BODY_BYTES", 2 * 1024 * 1024) > 10 * 1024 * 1024:
        errors.append("MAX_REQUEST_BODY_BYTES must be <= 10MiB in production")
    if int_env("MAX_WEBHOOK_BODY_BYTES", 1024 * 1024) > 5 * 1024 * 1024:
        errors.append("MAX_WEBHOOK_BODY_BYTES must be <= 5MiB in production")
    if int_env("AUTH_RATE_LIMIT_MAX_REQUESTS", int_env("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", 5)) > 10:
        errors.append("AUTH_RATE_LIMIT_MAX_REQUESTS must be <= 10 in production")
    if int_env("HSTS_MAX_AGE_SECONDS", 63072000) < 31536000:
        errors.append("HSTS_MAX_AGE_SECONDS must be at least 31536000")
    csp = os.getenv("CONTENT_SECURITY_POLICY", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
    if "default-src" not in csp or "frame-ancestors" not in csp:
        errors.append("CONTENT_SECURITY_POLICY must include default-src and frame-ancestors")
    if truthy("TRUST_PROXY_HEADERS", "true") and not os.getenv("TRUSTED_PROXY_IPS"):
        errors.append("TRUSTED_PROXY_IPS is required when TRUST_PROXY_HEADERS is enabled")
    if truthy("WAOS_REQUIRE_WHATSAPP_PRODUCTION", "true") and not os.getenv("META_APP_SECRET"):
        errors.append("META_APP_SECRET is required when WhatsApp production mode is enabled")
    if truthy("WAOS_REQUIRE_PAYMENT_PRODUCTION") and not (os.getenv("STRIPE_SECRET_KEY") or os.getenv("MERCADOPAGO_ACCESS_TOKEN")):
        errors.append("payment production mode requires STRIPE_SECRET_KEY or MERCADOPAGO_ACCESS_TOKEN")
    if truthy("WAOS_REQUIRE_OBSERVABILITY") and not (os.getenv("SENTRY_DSN") or truthy("OTEL_EXPORT_ENABLED") or os.getenv("DATADOG_API_KEY") or os.getenv("NEW_RELIC_LICENSE_KEY")):
        errors.append("observability is required: configure SENTRY_DSN, OTEL_EXPORT_ENABLED, DATADOG_API_KEY, or NEW_RELIC_LICENSE_KEY")

    if errors:
        print("production preflight failed:", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        raise SystemExit(1)
    print("production preflight ok")


if __name__ == "__main__":
    main()
