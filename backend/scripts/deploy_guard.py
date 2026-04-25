from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MIN_GUNICORN_TIMEOUT_SECONDS = 120
OPENAI_TIMEOUT_SECONDS = 30
AUTOPILOT_MAX_AUTOFIX_ROUNDS = 2
WEB_CONCURRENCY = 3
TRUSTED_PROXY_IPS = "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.1/32,::1/128"


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _read(path: Path, errors: list[str]) -> str:
    if not path.exists():
        errors.append(f"missing required file: {_relative(path)}")
        return ""
    return path.read_text(encoding="utf-8")


def _service_block(render_yaml: str, service_name: str) -> str:
    blocks = re.findall(r"(?ms)^  - type: .*?(?=^  - type:|^databases:|\Z)", render_yaml)
    for block in blocks:
        if re.search(rf"(?m)^    name:\s*{re.escape(service_name)}\s*$", block):
            return block
    return ""


def _env_entry(block: str, key: str) -> str:
    lines = block.splitlines()
    for idx, line in enumerate(lines):
        if line.strip() == f"- key: {key}":
            entry = [line]
            for nxt in lines[idx + 1:]:
                if nxt.strip().startswith("- key: "):
                    break
                entry.append(nxt)
            return "\n".join(entry)
    return ""


def _env_value(block: str, key: str) -> str | None:
    entry = _env_entry(block, key)
    match = re.search(r"(?m)^\s*value:\s*(.*?)\s*$", entry)
    return match.group(1).strip() if match else None


def _env_has_sync_false(block: str, key: str) -> bool:
    return bool(re.search(r"(?m)^\s*sync:\s*false\s*$", _env_entry(block, key)))


def _env_from_service(block: str, key: str, env_key: str | None = None) -> bool:
    entry = _env_entry(block, key)
    if not all(token in entry for token in ["fromService:", "name: waos-api", "type: web"]):
        return False
    expected = env_key or key
    return f"envVarKey: {expected}" in entry


def _require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def check_render_yaml(errors: list[str]) -> None:
    root_render = _read(ROOT_DIR / "render.yaml", errors)
    backend_render = _read(BACKEND_DIR / "render.yaml", errors)
    if not root_render or not backend_render:
        return
    _require(root_render == backend_render, errors, "render.yaml and backend/render.yaml drifted; keep both in lockstep or Render may deploy different config.")
    web_block = _service_block(root_render, "waos-api")
    worker_block = _service_block(root_render, "waos-worker")
    _require(bool(web_block), errors, "render.yaml is missing waos-api web service.")
    _require(bool(worker_block), errors, "render.yaml is missing waos-worker service.")
    if not web_block or not worker_block:
        return
    _require(re.search(r"(?m)^    plan:\s*standard\s*$", web_block) is not None, errors, "waos-api must stay on Render plan: standard.")
    _require(re.search(r"(?m)^    plan:\s*starter\s*$", worker_block) is not None, errors, "waos-worker should stay on Render plan: starter for the initial release.")
    _require(_env_has_sync_false(web_block, "OPENAI_API_KEY"), errors, "waos-api OPENAI_API_KEY must be a Render secret with sync: false.")
    _require(_env_value(web_block, "OPENAI_MODEL") == GEMINI_MODEL, errors, f"waos-api OPENAI_MODEL must be {GEMINI_MODEL}.")
    _require(_env_value(web_block, "OPENAI_BASE_URL") == GEMINI_OPENAI_BASE_URL, errors, "waos-api OPENAI_BASE_URL must point to Gemini OpenAI-compatible endpoint.")
    _require(_env_value(web_block, "OPENAI_TIMEOUT_SECONDS") == str(OPENAI_TIMEOUT_SECONDS), errors, "waos-api OPENAI_TIMEOUT_SECONDS must stay at 30.")
    _require(_env_value(web_block, "AUTOPILOT_MAX_AUTOFIX_ROUNDS") == str(AUTOPILOT_MAX_AUTOFIX_ROUNDS), errors, "waos-api AUTOPILOT_MAX_AUTOFIX_ROUNDS must stay at 2.")
    _require(_env_value(web_block, "TRUST_PROXY_HEADERS") == "true", errors, "waos-api TRUST_PROXY_HEADERS must be true on Render so rate limits/logs use real client IPs.")
    _require(_env_value(web_block, "TRUSTED_PROXY_IPS") == TRUSTED_PROXY_IPS, errors, "waos-api TRUSTED_PROXY_IPS must stay pinned to private Render proxy CIDRs, not wildcard trust.")
    _require(_env_value(web_block, "GUNICORN_TIMEOUT_SECONDS") == str(MIN_GUNICORN_TIMEOUT_SECONDS), errors, "waos-api GUNICORN_TIMEOUT_SECONDS must stay at 120 or higher.")
    _require(_env_value(web_block, "WEB_CONCURRENCY") == str(WEB_CONCURRENCY), errors, "waos-api WEB_CONCURRENCY must stay at 3 for agentic pipeline throughput.")
    for key in ["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "OPENAI_TIMEOUT_SECONDS", "AUTOPILOT_MAX_AUTOFIX_ROUNDS"]:
        _require(_env_from_service(worker_block, key), errors, f"waos-worker must inherit {key} from waos-api.")


def check_bootstrap(errors: list[str]) -> None:
    bootstrap = _read(BACKEND_DIR / "scripts" / "bootstrap.sh", errors)
    if not bootstrap:
        return
    _require("python scripts/deploy_guard.py --runtime" in bootstrap, errors, "bootstrap.sh must run deploy_guard.py --runtime before preflight/migrations.")
    _require("export WEB_CONCURRENCY=${WEB_CONCURRENCY:-3}" in bootstrap, errors, "bootstrap.sh default WEB_CONCURRENCY must be 3.")
    _require("export GUNICORN_TIMEOUT_SECONDS=${GUNICORN_TIMEOUT_SECONDS:-120}" in bootstrap, errors, "bootstrap.sh must default GUNICORN_TIMEOUT_SECONDS to 120.")
    _require("--timeout ${GUNICORN_TIMEOUT_SECONDS}" in bootstrap, errors, "gunicorn timeout must use the guarded GUNICORN_TIMEOUT_SECONDS env var.")


def migration_sort_key(path: Path) -> tuple[int, str, str]:
    match = re.match(r"^(\d{3})([a-z]?)_", path.name)
    if not match:
        return (10**9, "", path.name)
    return (int(match.group(1)), match.group(2), path.name)


def check_migrations(errors: list[str]) -> None:
    migrations_dir = BACKEND_DIR / "db" / "migrations"
    names = [path.name for path in sorted(migrations_dir.glob("*.sql"), key=migration_sort_key)]
    _require("005_whatsapp_anti_blocking_guardrails.sql" not in names, errors, "migration 005_whatsapp_anti_blocking_guardrails.sql must stay renamed; use 005b_ to avoid ambiguous 005 ordering.")
    _require("005b_whatsapp_anti_blocking_guardrails.sql" in names, errors, "migration 005b_whatsapp_anti_blocking_guardrails.sql is required.")
    bare_by_number: dict[str, list[str]] = {}
    full_prefixes: set[str] = set()
    for name in names:
        match = re.match(r"^(\d{3})([a-z]?)_", name)
        if not match:
            errors.append(f"migration {name} must start with a 3-digit numeric prefix, optionally followed by a lowercase suffix, e.g. 005b_name.sql")
            continue
        number, suffix = match.groups()
        full_prefix = f"{number}{suffix}"
        if full_prefix in full_prefixes:
            errors.append(f"duplicate migration prefix {full_prefix} detected; rename one migration.")
        full_prefixes.add(full_prefix)
        if not suffix:
            bare_by_number.setdefault(number, []).append(name)
    for number, bare_names in bare_by_number.items():
        if len(bare_names) > 1:
            errors.append(f"multiple bare {number}_ migrations detected: {', '.join(bare_names)}")
    _require(names == sorted(names), errors, "migration filenames must keep deterministic lexical order; avoid names that sort differently from numeric/suffix order.")


def check_code_contracts(errors: list[str]) -> None:
    checks = {
        "app/config.py": ["validate_ai_provider_alignment", "autopilot_max_autofix_rounds", "openai_timeout_seconds", "TRUSTED_PROXY_IPS contains invalid IP/CIDR entry", "trusted_proxy_networks"],
        "app/application/support.py": ["def _is_trusted_proxy_ip", "ipaddress.ip_network"],
        "app/ai_runtime/persistence.py": ["from .persistence_load import load_pipeline_context", "from .persistence_write import"],
        "app/ai_runtime/persistence_load.py": ["def load_pipeline_context"],
        "app/ai_runtime/persistence_write.py": ["def persist_decision_outcome", "def persist_pipeline_artifacts", "def finalize_pipeline_run"],
        "app/ai_runtime/pipeline.py": ["from .persistence_load import load_pipeline_context", "from .persistence_write import"],
        "app/vertical_onboarding_ai_prefill.py": ["settings.openai_timeout_seconds", "settings.autopilot_max_autofix_rounds"],
        "app/schemas/onboarding.py": ["le=2", "autopilot_max_autofix_rounds"],
        "app/application/onboarding_handlers/commands.py": ["settings.autopilot_max_autofix_rounds"],
        "scripts/run_migrations.py": ["list_migrations", "migration_sort_key"],
    }
    for rel, tokens in checks.items():
        content = _read(BACKEND_DIR / rel, errors)
        for token in tokens:
            _require(token in content, errors, f"{rel} must keep deploy hardening token: {token}")


def check_frontend_contracts(errors: list[str]) -> None:
    assistant = _read(ROOT_DIR / "frontend" / "features" / "bot-studio" / "create" / "AiSetupAssistant.tsx", errors)
    if not assistant:
        return
    _require("const AUTOPILOT_PROGRESS_MESSAGES" in assistant, errors, "AiSetupAssistant must expose autopilot progress messages for long-running runs.")
    _require("Detectando industria..." in assistant and "Generando setup completo..." in assistant and "Validando..." in assistant, errors, "AiSetupAssistant progress copy must include industry, generation and validation states.")
    _require("const accept = async () =>" in assistant, errors, "AiSetupAssistant accept-all must be a direct no-arg autopilot action.")
    _require('const wired = await onAutopilot({ userDescription: description, intensity: "savage" });' in assistant, errors, "AiSetupAssistant accept-all must call onAutopilot directly with savage intensity.")
    _require('accept("accept")' not in assistant and "accept('accept')" not in assistant, errors, "AiSetupAssistant must not require generated preview before accept-all autopilot.")
    _require("onClick={accept}" in assistant, errors, "AiSetupAssistant primary buttons must wire directly to accept.")


def check_frontend_env_examples(errors: list[str]) -> None:
    frontend_dir = ROOT_DIR / "frontend"
    canonical = frontend_dir / ".env.production.example"
    content = _read(canonical, errors)
    for deprecated in [frontend_dir / ".env.example", frontend_dir / ".env.vercel.example"]:
        _require(not deprecated.exists(), errors, f"{_relative(deprecated)} is deprecated; keep frontend env documentation canonical in frontend/.env.production.example only.")
    for key in ["NEXT_PUBLIC_APP_URL", "NEXT_PUBLIC_API_BASE_URL", "API_INTERNAL_URL", "API_BASE_URL", "API_TIMEOUT_MS", "API_RETRIES", "SECURE_COOKIES", "WAOS_ALLOW_ENV_FALLBACK"]:
        _require(f"{key}=" in content, errors, f"frontend/.env.production.example must document {key}.")
    _require("canonical source of truth" in content, errors, "frontend/.env.production.example must clearly mark itself as canonical.")


def check_vertical_profile_sync(errors: list[str]) -> None:
    export_script = ROOT_DIR / "backend" / "scripts" / "export_vertical_profiles.py"
    sync_script = ROOT_DIR / "scripts" / "sync-vertical-profiles.sh"
    fallback_loader = ROOT_DIR / "frontend" / "app" / "lib" / "vertical-fallback" / "index.ts"
    release_gate = ROOT_DIR / "scripts" / "release_gate.py"
    _require(export_script.exists(), errors, "backend/scripts/export_vertical_profiles.py is required to sync backend vertical profiles to frontend.")
    _require(sync_script.exists(), errors, "scripts/sync-vertical-profiles.sh is required to refresh frontend vertical fallback data.")
    _require("readFile" in _read(fallback_loader, errors) and "entry.file" in _read(fallback_loader, errors), errors, "frontend vertical fallback loader must be data-driven from index.json profile files.")
    _require("/api/v1/onboarding/wizard/ai-autopilot" in _read(release_gate, errors), errors, "release_gate.py must include the ai-autopilot endpoint as a critical route.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WAOS deploy hardening guardrails")
    parser.add_argument("--runtime", action="store_true", help="Run startup-safe checks only.")
    args = parser.parse_args(argv)
    errors: list[str] = []
    check_bootstrap(errors)
    check_migrations(errors)
    check_code_contracts(errors)
    check_frontend_contracts(errors)
    check_frontend_env_examples(errors)
    check_vertical_profile_sync(errors)
    if not args.runtime:
        check_render_yaml(errors)
    if errors:
        for error in errors:
            print(f"[deploy-guard:error] {error}", file=sys.stderr)
        return 1
    print("[deploy-guard:ok] deploy hardening checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
