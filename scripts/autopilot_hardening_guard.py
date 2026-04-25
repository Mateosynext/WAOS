#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, pattern: str, label: str) -> None:
    text = read(path)
    if not re.search(pattern, text, re.S):
        raise SystemExit(f"[autopilot-guard:fail] {label} missing in {path}")


def forbid(path: str, pattern: str, label: str) -> None:
    text = read(path)
    if re.search(pattern, text, re.S):
        raise SystemExit(f"[autopilot-guard:fail] forbidden {label} in {path}")


def main() -> int:
    require("frontend/features/bot-studio/services/wizardAutopilotContract.ts", r"AUTOPILOT_MAX_AUTOFIX_ROUNDS = 2", "frontend max rounds contract")
    require("frontend/features/bot-studio/services/wizardAutopilotContract.ts", r"parseAutopilotBoolean", "safe boolean parser")
    require("frontend/app/api/onboarding/wizard/ai-autopilot/route.ts", r"readWizardJsonBody", "strict JSON body reader")
    require("frontend/app/api/onboarding/wizard/ai-autopilot/route.ts", r"hasRequiredAutopilotScope", "organization scope validation")
    require("frontend/app/api/onboarding/wizard/route-helpers.ts", r"X-Content-Type-Options", "nosniff header")
    require("frontend/features/bot-studio/create/AiSetupAssistant.tsx", r"maxLength=\{AI_DESCRIPTION_MAX_LENGTH\}", "textarea length guard")
    require("backend/app/schemas/onboarding.py", r"GuidedOnboardingAiAutopilotRequest\(BaseModel\):.*extra=\"forbid\".*organization_id: str = Field\(min_length=1, max_length=120\)", "strict backend autopilot schema")
    require("backend/app/vertical_onboarding_ai_prefill.py", r"def _bounded_autopilot_autofix_rounds", "defensive backend round clamp")
    forbid("frontend/app/api/onboarding/wizard/ai-autopilot/route.ts", r"Boolean\(", "unsafe Boolean coercion")
    forbid("frontend/features/bot-studio/flow/wizardScreenModels.ts", r"maxAutofixRounds:\s*3", "autopilot max rounds 3")
    print("[autopilot-guard:ok] autopilot production hardening checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
