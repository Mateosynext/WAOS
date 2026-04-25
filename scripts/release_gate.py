#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
FORBIDDEN_RUNTIME_PATHS = [
    "backend/app/__pycache__",
    "backend/scripts/__pycache__",
    "backend/tests/__pycache__",
    "frontend/.next",
    "frontend/node_modules",
    "frontend/tsconfig.tsbuildinfo",
    "frontend/playwright-report",
    "frontend/test-results",
    ".pytest_cache",
    ".mypy_cache",
]
# Critical route anchor kept explicit so deploy_guard/test_deploy_hardening_guardrails can verify it.
CRITICAL_ONBOARDING_AUTOPILOT_ROUTE = "/api/v1/onboarding/wizard/ai-autopilot"
CRITICAL_BACKEND_ROUTE_TOKENS = [
    '@onboarding_router.post("/wizard/ai-autopilot"',
    '@router.post("/api/v1/ai/bot-autopilot"',
    '@router.get("/api/v1/ai/bot-autopilot/health"',
    '@router.get("/api/v1/ai/workflows/{run_id}"',
    '@router.get("/api/v1/ai/workflows/{run_id}/events"',
    '@router.post("/api/v1/ai/workflows/{run_id}/prepare-apply"',
    '@router.post("/api/v1/ai/workflows/{run_id}/apply"',
    '@router.post("/api/v1/ai/workflows/{run_id}/prepare-canary"',
]
CRITICAL_FRONTEND_PROXY_FILES = [
    "frontend/app/api/ai/bot-autopilot/route.ts",
    "frontend/app/api/ai/bot-autopilot/health/route.ts",
    "frontend/app/api/ai/workflows/[runId]/route.ts",
    "frontend/app/api/ai/workflows/[runId]/events/route.ts",
    "frontend/app/api/ai/workflows/[runId]/prepare-apply/route.ts",
    "frontend/app/api/ai/workflows/[runId]/apply/route.ts",
    "frontend/app/api/ai/workflows/[runId]/prepare-canary/route.ts",
]


def read(path: Path, errors: list[str]) -> str:
    if not path.exists():
        errors.append(f"missing required file: {path.relative_to(ROOT_DIR)}")
        return ""
    return path.read_text(encoding="utf-8")


def check_runtime_clean(errors: list[str]) -> None:
    # Release zips should be source-clean. Remove transient caches that local
    # validation may create, then fail only on artifacts that remain.
    for rel in FORBIDDEN_RUNTIME_PATHS:
        target = ROOT_DIR / rel
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink(missing_ok=True)
    for pattern in ("*.pyc", "*.pyo", "*.tsbuildinfo", ".DS_Store"):
        matches = list(ROOT_DIR.glob(pattern)) + list((ROOT_DIR / "frontend").glob(pattern)) + list((ROOT_DIR / "backend").glob(pattern))
        for path in matches:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        remaining = list(ROOT_DIR.glob(pattern)) + list((ROOT_DIR / "frontend").glob(pattern)) + list((ROOT_DIR / "backend").glob(pattern))
        for path in remaining:
            errors.append(f"runtime/build artifact must not ship: {path.relative_to(ROOT_DIR)}")


def check_critical_routes(errors: list[str]) -> None:
    backend_router = read(ROOT_DIR / "backend/app/api/routers/ai_workflows.py", errors)
    onboarding_router = read(ROOT_DIR / "backend/app/api/routers/onboarding.py", errors)
    combined = backend_router + "\n" + onboarding_router
    for token in CRITICAL_BACKEND_ROUTE_TOKENS:
        if token not in combined:
            errors.append(f"critical backend route token missing: {token}")
    for rel in CRITICAL_FRONTEND_PROXY_FILES:
        content = read(ROOT_DIR / rel, errors)
        if rel.endswith("events/route.ts"):
            if "/api/v1/ai/workflows/" not in content or "/events" not in content:
                errors.append(f"frontend events proxy does not point to backend events route: {rel}")
        elif "bot-autopilot/health" in rel:
            if "/api/v1/ai/bot-autopilot/health" not in content:
                errors.append(f"frontend health proxy target missing in {rel}")
        elif "bot-autopilot/route" in rel:
            if "/api/v1/ai/bot-autopilot" not in content:
                errors.append(f"frontend autopilot proxy target missing in {rel}")
        elif "prepare-apply" in rel and "prepare-apply" not in content:
            errors.append(f"frontend prepare-apply proxy target missing in {rel}")
        elif "prepare-canary" in rel and "prepare-canary" not in content:
            errors.append(f"frontend prepare-canary proxy target missing in {rel}")
        elif "/apply/" in rel and "apply" not in content:
            errors.append(f"frontend apply proxy target missing in {rel}")


def check_env_alignment(errors: list[str]) -> None:
    frontend_env = read(ROOT_DIR / "frontend/.env.production.example", errors)
    for key in [
        "NEXT_PUBLIC_APP_URL=",
        "NEXT_PUBLIC_API_BASE_URL=",
        "API_INTERNAL_URL=",
        "API_BASE_URL=",
        "WAOS_ALLOW_ENV_FALLBACK=false",
        "SECURE_COOKIES=true",
    ]:
        if key not in frontend_env:
            errors.append(f"frontend production env example missing {key}")
    render_yaml = read(ROOT_DIR / "render.yaml", errors)
    backend_render = read(ROOT_DIR / "backend/render.yaml", errors)
    if render_yaml and backend_render and render_yaml != backend_render:
        errors.append("root render.yaml and backend/render.yaml are not identical")
    for key in [
        "OPENAI_MODEL",
        "OPENAI_BASE_URL",
        "OPENAI_TIMEOUT_SECONDS",
        "AUTOPILOT_MAX_AUTOFIX_ROUNDS",
        "AUTO_RUN_MIGRATIONS",
        "PUBLIC_APP_URL",
        "CORS_ALLOWED_ORIGINS",
        "ALLOWED_HOSTS",
    ]:
        if f"key: {key}" not in render_yaml:
            errors.append(f"render.yaml missing env var {key}")


def check_bot_apply_contract(errors: list[str]) -> None:
    router = read(ROOT_DIR / "backend/app/api/routers/ai_workflows.py", errors)
    for token in [
        "apply_guided_onboarding_wizard",
        "actor_user=user",
        "explicit_confirmation_required",
        "readiness_blocked",
        "patch_run_result(uow.conn, run_id, \"bot_id\", bot_id)",
        "apply_result",
    ]:
        if token not in router:
            errors.append(f"bot apply contract token missing: {token}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WAOS release gate for source zips and deploy handoff.")
    parser.add_argument("--profile", choices=["source", "runtime"], default="source")
    args = parser.parse_args(argv)
    errors: list[str] = []
    check_runtime_clean(errors)
    check_critical_routes(errors)
    check_env_alignment(errors)
    check_bot_apply_contract(errors)
    if errors:
        for error in errors:
            print(f"[release-gate:error] {error}", file=sys.stderr)
        return 1
    print(f"[release-gate:ok] {args.profile} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
