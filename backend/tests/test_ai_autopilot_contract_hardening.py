from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.schemas.onboarding import GuidedOnboardingAiAutopilotRequest, GuidedOnboardingAiPrefillRequest
from app.vertical_onboarding_ai_prefill import _bounded_autopilot_autofix_rounds


class AiAutopilotContractHardeningTest(unittest.TestCase):
    def test_autopilot_schema_rejects_invalid_rounds_and_extra_fields(self) -> None:
        with self.assertRaises(ValidationError):
            GuidedOnboardingAiAutopilotRequest(organization_id="org_1", max_autofix_rounds=3)
        with self.assertRaises(ValidationError):
            GuidedOnboardingAiAutopilotRequest(organization_id="org_1", max_autofix_rounds=2, maxAutofixRounds=2)

    def test_autopilot_schema_requires_organization(self) -> None:
        with self.assertRaises(ValidationError):
            GuidedOnboardingAiAutopilotRequest(organization_id="")
        with self.assertRaises(ValidationError):
            GuidedOnboardingAiPrefillRequest(organization_id="")

    def test_runtime_round_bound_is_defensive(self) -> None:
        self.assertEqual(_bounded_autopilot_autofix_rounds(999), 2)
        self.assertEqual(_bounded_autopilot_autofix_rounds(0), 1)
        self.assertEqual(_bounded_autopilot_autofix_rounds("bad"), 2)


if __name__ == "__main__":
    unittest.main()
