from __future__ import annotations

import ast
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent

REQ = [
    ROOT / "app" / "main.py",
    ROOT / "app" / "security.py",
    ROOT / "app" / "hardening.py",
    ROOT / "app" / "db.py",
    ROOT / "app" / "migrations.py",
    ROOT / "app" / "world_class.py",
    ROOT / "app" / "world_class_plus.py",
    ROOT / "app" / "verticals.py",
    ROOT / "app" / "vertical_10x.py",
    ROOT / "app" / "vertical_domain_runtime.py",
    ROOT / "app" / "vertical_marketplace_runtime.py",
    ROOT / "app" / "vertical_transactions.py",
    ROOT / "app" / "whatsapp_channel_runtime.py",
    ROOT / "app" / "whatsapp_governance.py",
    ROOT / "app" / "voice_pipeline.py",
    ROOT / "db" / "schema.sql",
    ROOT / "db" / "schema" / "runtime" / "003_voice_channel.sql",
    ROOT / "db" / "schema" / "runtime" / "006_db_runtime_tables.sql",
    ROOT / "db" / "schema" / "platform" / "003_telemetry.sql",
    ROOT / "scripts" / "bootstrap.sh",
    ROOT / "scripts" / "worker_bootstrap.sh",
    ROOT / "scripts" / "preflight_check.py",
    ROOT / "scripts" / "production_smoke.py",
    ROOT / "scripts" / "security_smoke.py",
    REPO / "frontend" / "package.json",
    REPO / "frontend" / "vercel.json",
]
BAD_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".next", "node_modules"}
BAD_SUFFIX = {".pyc", ".pyo"}


def fail(message: str) -> None:
    raise SystemExit(f"production hardened validation failed: {message}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    missing = [str(x.relative_to(REPO)) for x in REQ if not x.exists()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    offenders: list[str] = []
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        rel = Path(dirpath).relative_to(REPO)
        if any(part in BAD_DIRS for part in rel.parts):
            offenders.append(str(rel))
            dirnames[:] = []
            continue
        for name in filenames:
            fp = Path(dirpath) / name
            r = fp.relative_to(REPO)
            if fp.suffix in BAD_SUFFIX or any(part in BAD_DIRS for part in r.parts):
                offenders.append(str(r))
            if len(offenders) >= 20:
                break
        if len(offenders) >= 20:
            break
    if offenders:
        fail("build/cache artifacts must not ship: " + ", ".join(offenders))

    for f in [p for p in REQ if p.suffix == ".py"] + [
        ROOT / "app" / "application" / "auth_service.py",
        ROOT / "app" / "api" / "routers" / "system.py",
        ROOT / "app" / "api" / "handlers" / "webhooks.py",
        ROOT / "app" / "config.py",
        ROOT / "app" / "schema_sql.py",
    ]:
        try:
            ast.parse(read(f), filename=str(f))
        except SyntaxError as exc:
            fail(f"syntax error in {f.relative_to(REPO)}: {exc}")

    hardening = read(ROOT / "app" / "hardening.py")
    for marker in ["waos_security_gate", "rate_limit_exceeded", "Content-Security-Policy", "Strict-Transport-Security", "request_body_too_large"]:
        if marker not in hardening:
            fail(f"hardening control missing: {marker}")
    if "await request.body()" in hardening:
        fail("body limit must use streaming cutoff, not await request.body() full buffering")
    for marker in ["_check_distributed_rate_limit", "redis.asyncio", "_check_in_process_rate_limit", "rate_limit_memory_max_buckets", "rate_limit_backend", "RateLimitBackendUnavailable"]:
        if marker not in hardening:
            fail(f"distributed/bounded rate-limit control missing: {marker}")
    if "defaultdict" in hardening:
        fail("rate limit buckets must not use unbounded defaultdict storage")
    if "_RATE_BUCKETS[key]" in hardening:
        fail("rate limit buckets must be created through bounded eviction helper, not direct key indexing")

    config = read(ROOT / "app" / "config.py")
    for marker in ["security_hardening_enabled", "enforce_https", "require_signed_webhooks", "max_request_body_bytes", "rate_limit_backend", "rate_limit_redis_url", "rate_limit_gateway_enforced"]:
        if marker not in config:
            fail(f"settings hardening control missing: {marker}")
    if 'RATE_LIMIT_BACKEND must be redis, valkey, upstash, or gateway in production' not in config:
        fail("production config must reject in-process-only rate limiting")

    main_py = read(ROOT / "app" / "main.py")
    if "waos_security_gate" not in main_py:
        fail("main.py must install waos_security_gate middleware")
    if "ENABLE_API_DOCS" not in main_py:
        fail("main.py must support disabling API docs")

    preflight = read(ROOT / "scripts" / "preflight_check.py")
    for marker in ["SECURITY_HARDENING_ENABLED", "ENFORCE_HTTPS", "REQUIRE_SIGNED_WEBHOOKS", "WAOS_REQUIRE_OBSERVABILITY", "RATE_LIMIT_BACKEND", "RATE_LIMIT_REDIS_URL", "RATE_LIMIT_GATEWAY_ENFORCED"]:
        if marker not in preflight:
            fail(f"production preflight missing hardened gate {marker}")

    frontend_api = read(REPO / "frontend" / "app" / "lib" / "api.ts")
    for marker in ["recordApiFallback", "frontend.api_fallback", "severity === \"critical\"", "Backend unavailable for critical frontend data"]:
        if marker not in frontend_api:
            fail(f"frontend API fallback hardening missing: {marker}")
    frontend_shared = read(REPO / "frontend" / "app" / "lib" / "data" / "shared.ts")
    for marker in ["fetchArrayState", "fetchRecordState", "recordApiFallback(endpoint, result.error", "ok: false"]:
        if marker not in frontend_shared:
            fail(f"frontend data degradation state missing: {marker}")
    for rel in ["status/page.tsx", "operations/page.tsx", "scheduler/page.tsx", "insights/page.tsx"]:
        page = read(REPO / "frontend" / "app" / rel)
        for marker in ["OperationalDegradedBanner", "hasOperationalFailures", "block"]:
            if marker not in page:
                fail(f"operational dashboard must expose/block degraded backend state: frontend/app/{rel} missing {marker}")
        if "apiFetchOrDefault" in page:
            fail(f"operational dashboard must not fetch critical data through apiFetchOrDefault: frontend/app/{rel}")

    security = read(ROOT / "app" / "security.py")
    if "def get_optional_current_user" not in security:
        fail("security.py must expose get_optional_current_user")
    auth = read(ROOT / "app" / "application" / "auth_service.py")
    if "user_for_token" not in auth:
        fail("auth tokens must include organization memberships")

    webhooks = read(ROOT / "app" / "api" / "handlers" / "webhooks.py")
    if "settings.require_signed_webhooks" not in webhooks or "webhook_secret_missing" not in webhooks:
        fail("WhatsApp webhooks must fail closed when signatures are required")

    system = read(ROOT / "app" / "api" / "routers" / "system.py")
    for sig in ["def system_status(user: CurrentUser", "def runtime_health_panel(user: CurrentUser", "def deploy_checklist(user: CurrentUser"]:
        if sig not in system:
            fail("internal system endpoints must require auth")
    if "_require_super_admin" not in system:
        fail("system runtime endpoints must enforce super admin")

    schema = read(ROOT / "db" / "schema.sql")
    for table in ["users", "organizations", "organization_members", "bots", "bot_versions", "contacts", "conversations", "messages", "outbox_messages", "automation_jobs", "integration_connections"]:
        if f"CREATE TABLE IF NOT EXISTS {table}" not in schema:
            fail(f"schema missing core table {table}")

    db = read(ROOT / "app" / "db.py")
    if "_ensure_index_columns" not in db:
        fail("db.py must guard index migrations against missing columns")

    print("production hardened artifact validation ok")


if __name__ == "__main__":
    main()
