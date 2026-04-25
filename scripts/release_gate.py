#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

CRITICAL_ROUTE_CONTRACTS = [
    {
        "route": "/api/v1/onboarding/wizard/ai-autopilot",
        "file": "backend/app/api/routers/onboarding.py",
        "tokens": [
            'APIRouter(prefix="/api/v1/onboarding"',
            '@onboarding_router.post("/wizard/ai-autopilot"',
            'def run_guided_wizard_ai_autopilot',
            'ai_autopilot_wizard',
        ],
    },
]

FORBIDDEN_ROOT_ARTIFACTS = [".next", "node_modules", "*.tsbuildinfo"]


def _error(errors: list[str], message: str) -> None:
    errors.append(message)


def check_critical_routes(errors: list[str]) -> None:
    for contract in CRITICAL_ROUTE_CONTRACTS:
        path = ROOT_DIR / contract["file"]
        if not path.exists():
            _error(errors, f"missing critical route source: {contract['file']}")
            continue
        content = path.read_text(encoding="utf-8")
        for token in contract["tokens"]:
            if token not in content:
                _error(errors, f"critical route {contract['route']} is not wired; missing token {token!r} in {contract['file']}")


def check_vertical_fallback_sync(errors: list[str]) -> None:
    index_path = ROOT_DIR / "frontend" / "app" / "lib" / "vertical-fallback" / "index.json"
    profiles_dir = index_path.parent / "profiles"
    if not index_path.exists():
        _error(errors, "missing frontend vertical fallback index.json")
        return
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _error(errors, f"frontend vertical fallback index.json is invalid JSON: {exc}")
        return
    ids = [str(item.get("id") or "") for item in index]
    if len(ids) != len(set(ids)):
        _error(errors, "frontend vertical fallback index has duplicate IDs")
    missing_files = [str(item.get("file")) for item in index if not (profiles_dir.parent / str(item.get("file"))).exists()]
    if missing_files:
        _error(errors, f"frontend vertical fallback index references missing profile files: {', '.join(missing_files)}")
    backend_path = ROOT_DIR / "backend" / "app" / "verticals" / "implementation.py"
    tree = ast.parse(backend_path.read_text(encoding="utf-8"), filename=str(backend_path))
    backend_profiles = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "_VERTICALS" for target in targets):
                backend_profiles = ast.literal_eval(node.value)
                break
    backend_ids = {str(item.get("id")) for item in backend_profiles if item.get("id")}
    frontend_ids = {item for item in ids if item}
    missing_frontend = sorted(backend_ids - frontend_ids)
    extra_frontend = sorted(frontend_ids - backend_ids)
    if missing_frontend or extra_frontend:
        _error(errors, f"vertical fallback ID drift. missing_frontend={missing_frontend}; extra_frontend={extra_frontend}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WAOS release gate")
    parser.add_argument("--profile", default="source", choices=["source"], help="Release validation profile")
    args = parser.parse_args(argv)
    errors: list[str] = []
    check_critical_routes(errors)
    check_vertical_fallback_sync(errors)
    if errors:
        for error in errors:
            print(f"[release-gate:error] {error}", file=sys.stderr)
        return 1
    print(f"[release-gate:ok] {args.profile} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
