#!/usr/bin/env python3
from __future__ import annotations

import ast
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"

NODE_CHECKS = [
    "check-local-imports.mjs",
    "check-bot-creation-guardrails.mjs",
    "check-p1-operational-guardrails.mjs",
    "check-critical-flow-guardrails.mjs",
    "check-multitenant-security-guardrails.mjs",
    "check-workflow-runtime-guardrails.mjs",
    "validate-env.mjs",
]

LOCAL_IMPORT_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
LOCAL_IMPORT_IGNORED_DIRS = {"node_modules", ".next", "coverage", "test-results", "playwright-report"}
STATIC_IMPORT_RE = re.compile(r"^\s*(?:import|export)\s+(?:[^'\"]*?\s+from\s+)?['\"]([^'\"]+)['\"]")
DYNAMIC_IMPORT_RE = re.compile(r"\bimport\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")


def _walk_frontend_sources() -> list[Path]:
    files: list[Path] = []
    for path in FRONTEND.rglob("*"):
        if not path.is_file() or path.suffix not in LOCAL_IMPORT_EXTS:
            continue
        if any(part in LOCAL_IMPORT_IGNORED_DIRS for part in path.relative_to(FRONTEND).parts):
            continue
        files.append(path)
    return sorted(files)


def _local_import_candidates(spec: str, from_dir: Path) -> list[Path]:
    if spec.startswith("@/"):
        base = FRONTEND / spec[2:]
    elif spec.startswith("."):
        base = (from_dir / spec).resolve()
    else:
        return []
    candidates = [base]
    candidates.extend(Path(str(base) + ext) for ext in LOCAL_IMPORT_EXTS)
    candidates.extend(base / ("index" + ext) for ext in LOCAL_IMPORT_EXTS)
    return candidates


def _strip_line_comment(line: str) -> str:
    quote = ""
    escaped = False
    for index in range(max(0, len(line) - 1)):
        char = line[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "/" and line[index + 1] == "/":
            return line[:index]
    return line


def _extract_local_import_specs(source: str) -> list[str]:
    specs: list[str] = []
    for raw_line in source.splitlines():
        line = _strip_line_comment(raw_line)
        static_match = STATIC_IMPORT_RE.search(line)
        if static_match:
            specs.append(static_match.group(1))
        specs.extend(match.group(1) for match in DYNAMIC_IMPORT_RE.finditer(line))
    return specs


def run_local_import_check() -> None:
    files = _walk_frontend_sources()
    imports = 0
    errors: list[str] = []
    for file in files:
        source = file.read_text(encoding="utf-8")
        for spec in _extract_local_import_specs(source):
            imports += 1
            candidates = _local_import_candidates(spec, file.parent)
            if candidates and not any(candidate.exists() for candidate in candidates):
                errors.append(f"{file.relative_to(FRONTEND)} -> {spec}")
    if errors:
        print(f"[imports:error] {len(errors)} unresolved local import" + ("" if len(errors) == 1 else "s"), flush=True)
        for error in errors:
            print(" - " + error, flush=True)
        raise SystemExit(1)
    print(f"[imports:ok] {len(files)} JS/TS files scanned; imports={imports}", flush=True)


def run_node_script(script: str, cwd: Path) -> None:
    # Run through a non-interactive shell for stable stdio/process reaping across
    # constrained CI containers where direct node subprocesses can leave pipes open.
    shell_command = './scripts/' + script
    command = ['bash', '-lc', 'cd ' + shlex.quote(str(cwd)) + ' && node ' + shlex.quote(shell_command)]
    print('[gate] node ' + shell_command, flush=True)
    try:
        completed = subprocess.run(
            command,
            cwd='.',
            timeout=int(os.environ.get('WAOS_GATE_STEP_TIMEOUT', '60')),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.output.decode('utf-8', errors='replace') if isinstance(exc.output, bytes) else (exc.output or '')
        if output:
            print(output, end='' if output.endswith('\n') else '\n', flush=True)
        raise SystemExit(f'[gate:fail] {script} timed out') from exc
    if completed.stdout:
        print(completed.stdout, end='' if completed.stdout.endswith('\n') else '\n', flush=True)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def run_artifact_integrity() -> None:
    print("[gate] backend.scripts.check_release_artifact_integrity", flush=True)
    command = [sys.executable, str(ROOT / "backend" / "scripts" / "check_release_artifact_integrity.py")]
    completed = subprocess.run(command, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=60)
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n", flush=True)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def run_source_hardening() -> None:
    print("[gate] backend.scripts.check_release_source_hardening", flush=True)
    command = [sys.executable, str(ROOT / "backend" / "scripts" / "check_release_source_hardening.py")]
    completed = subprocess.run(command, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=60)
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n", flush=True)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

def check_hygiene() -> None:
    required = [
        "backend/app/main.py",
        "backend/app/security.py",
        "backend/app/api/router.py",
        "backend/app/job_idempotency.py",
        "backend/worker.py",
        "frontend/package.json",
        "frontend/app/page.tsx",
        "frontend/app/login/page.tsx",
        "frontend/app/bot-studio/page.tsx",
        "frontend/app/api/ai/route-helpers.ts",
        "scripts/validate_release_in_ci.sh",
        "MULTITENANT_SECURITY_FUZZ_REGISTER_2026-04-26.md",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    if missing:
        for p in missing:
            print("[hygiene:missing]", p, flush=True)
        raise SystemExit(1)
    pages = list((ROOT / "frontend" / "app").glob("**/page.tsx"))
    if len(pages) < 40:
        print(f"[hygiene:fail] frontend_pages={len(pages)}", flush=True)
        raise SystemExit(1)
    print(f"[hygiene:ok] frontend_pages={len(pages)}", flush=True)


def compile_backend() -> None:
    critical = [
        "backend/app/main.py",
        "backend/app/security.py",
        "backend/app/config.py",
        "backend/app/hardening.py",
        "backend/app/job_idempotency.py",
        "backend/app/api/router.py",
        "backend/app/api/dependencies.py",
        "backend/app/api/handlers/webhooks.py",
        "backend/app/api/handlers/telephony.py",
        "backend/app/application/auth_service.py",
        "backend/app/application/bot_creation_workflow_service.py",
        "backend/app/application/bot_service.py",
        "backend/app/application/conversation_service.py",
        "backend/app/application/inbound_service.py",
        "backend/app/application/integration_service.py",
        "backend/app/application/knowledge_ingestion_service.py",
        "backend/app/application/voice_channel_service.py",
        "backend/app/whatsapp.py",
        "backend/app/whatsapp_governance.py",
        "backend/worker.py",
    ]
    total = len(list((ROOT / "backend" / "app").rglob("*.py"))) + 1
    for rel in critical:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"[gate:fail] missing backend critical file {rel}")
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            raise SystemExit(f"[gate:fail] syntax error in {rel}: {exc}") from exc
    print(f"[gate] backend syntax critical files={len(critical)}; backend_python_files={total}", flush=True)


def run_ai_evals() -> None:
    print("[gate] backend.app.ai_evals.run_all", flush=True)
    from backend.app.ai_evals.run_all import main as ai_eval_main

    code = int(ai_eval_main() or 0)
    if code != 0:
        raise SystemExit(code)


def run_frontend_guardrails() -> None:
    missing_node_checks = [script for script in NODE_CHECKS if not (FRONTEND / "scripts" / script).exists()]
    if missing_node_checks:
        raise SystemExit("[gate:fail] missing frontend guardrail scripts: " + ", ".join(missing_node_checks))
    if shutil.which("node") is None:
        raise SystemExit("[gate:fail] node is required to execute frontend guardrails")
    print(f"[gate] frontend guardrails running={len(NODE_CHECKS)}", flush=True)
    for script in NODE_CHECKS:
        run_node_script(script, FRONTEND)
    print(f"[gate] frontend guardrails passed={len(NODE_CHECKS)}", flush=True)


def main() -> int:
    check_hygiene()
    run_artifact_integrity()
    run_source_hardening()
    compile_backend()
    run_frontend_guardrails()
    run_ai_evals()
    print("[gate:ok] deterministic release gate passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
