#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
REQUIRED_PATHS = [
    "backend/app/main.py", "backend/app/security.py", "backend/app/api/router.py",
    "backend/app/job_idempotency.py", "backend/worker.py", "frontend/package.json",
    "frontend/app/page.tsx", "frontend/app/login/page.tsx", "frontend/app/bot-studio/page.tsx",
    "frontend/app/api/ai/route-helpers.ts", "scripts/validate_release_in_ci.sh",
    "scripts/validate_zip_reproducible.sh", "backend/scripts/check_release_artifact_integrity.py",
    "backend/scripts/normalize_release_permissions.py",
    "MULTITENANT_SECURITY_FUZZ_REGISTER_2026-04-26.md",
]
REQUIRED_SNIPPETS = {
    "backend/app/security.py": ["tenant_context_mismatch", "bot_context_mismatch", "No access to organization"],
    "backend/app/job_idempotency.py": ["INSERT OR IGNORE", "ON CONFLICT (organization_id, action_type, dedupe_key) DO NOTHING"],
    "frontend/app/lib/env.ts": ["API_INTERNAL_URL", "NEXT_PUBLIC_API_BASE_URL", "WAOS_ALLOW_ENV_FALLBACK"],
    "frontend/app/lib/api.ts": ["x-waos-org-id", "x-waos-bot-id"],
    "frontend/app/actions/bots.ts": ["Idempotency-Key", "client_request_id", "/api/v1/bots/creation-workflows"],
    "backend/scripts/check_release_artifact_integrity.py": ["FORBIDDEN_NAMES", "SECRET_PATTERNS", "EXECUTABLE_FILES"],
    "backend/scripts/normalize_release_permissions.py": ["EXECUTABLE_FILES", "os.chmod", "[perms:mode]"],
    "scripts/validate_zip_reproducible.sh": ["validate_release_in_ci.sh", "shipped_artifacts"],
}
def main() -> int:
    errors: list[str] = []
    for rel in REQUIRED_PATHS:
        if not (ROOT / rel).exists():
            errors.append(f"missing required path: {rel}")
    for rel, needles in REQUIRED_SNIPPETS.items():
        path = ROOT / rel
        text = path.read_text(errors="ignore") if path.exists() else ""
        for needle in needles:
            if needle not in text:
                errors.append(f"{rel} missing snippet: {needle}")
    frontend_pages = list((ROOT / "frontend" / "app").glob("**/page.tsx"))
    if len(frontend_pages) < 40:
        errors.append(f"frontend route surface too small: {len(frontend_pages)} page.tsx files")
    if errors:
        print("[hygiene:fail]")
        for err in errors:
            print("-", err)
        return 1
    print(f"[hygiene:ok] required paths/snippets found; frontend_pages={len(frontend_pages)}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
