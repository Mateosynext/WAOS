from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def test_legacy_wizard_autopilot_has_same_id_normalizers_as_command_center():
    contract = read("frontend/features/bot-studio/services/wizardAutopilotContract.ts")
    schema = read("backend/app/schemas/onboarding.py")
    assistant = read("frontend/features/bot-studio/create/AiSetupAssistant.tsx")
    assert "requiredScopeTextValue" in contract
    assert "optionalTextValue(record[key])" in contract
    assert '"[object Object]"' not in contract
    assert "_clean_id_like" in schema
    assert "field_validator" in schema
    assert "GuidedOnboardingAiAutopilotRequest" in schema
    assert "MIN_AI_DESCRIPTION_LENGTH" in assistant
    assert "setInterval" not in assistant

def test_ops_runs_empty_org_list_does_not_return_all_tenant_runs():
    persistence = read("backend/app/ai_workflows/persistence.py")
    assert "if organization_ids is not None" in persistence
    assert "if not cleaned_org_ids:" in persistence
    assert "return []" in persistence
