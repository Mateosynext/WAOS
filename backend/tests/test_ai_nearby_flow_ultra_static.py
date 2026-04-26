from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


def test_legacy_wizard_apply_requires_explicit_confirmation_everywhere():
    schemas = read("backend/app/schemas/onboarding.py")
    router = read("backend/app/api/routers/onboarding.py")
    service = read("backend/app/application/onboarding_service.py")
    commands = read("backend/app/application/onboarding_handlers/commands.py")
    client_api = read("frontend/features/bot-studio/services/wizardApi.ts")
    server_api = read("frontend/app/lib/data/wizard.ts")

    assert "class GuidedOnboardingWizardApplyRequest" in schemas
    assert "confirm: bool = False" in schemas
    assert "payload: GuidedOnboardingWizardApplyRequest" in router
    assert "payload=payload" in service
    assert "explicit_confirmation_required" in commands
    assert 'JSON.stringify({ confirm: true })' in client_api
    assert 'JSON.stringify({ confirm: true })' in server_api


def test_nearby_wizard_ids_use_shared_defensive_normalizers():
    contract = read("frontend/features/bot-studio/services/wizardAutopilotContract.ts")
    client_api = read("frontend/features/bot-studio/services/wizardApi.ts")
    server_api = read("frontend/app/lib/data/wizard.ts")
    schemas = read("backend/app/schemas/onboarding.py")

    assert "export function normalizeOptionalWizardId" in contract
    assert "export function normalizeRequiredWizardScope" in contract
    assert "normalizeOptionalWizardId(request.botId)" in client_api
    assert "normalizeOptionalWizardId(request.verticalId)" in client_api
    assert "normalizeRequiredWizardScope(request.organizationId)" in client_api
    assert "normalizeOptionalWizardId(request.botId)" in server_api
    assert "normalizeRequiredWizardScope(request.organizationId)" in server_api
    assert 'class GuidedOnboardingWizardStartRequest' in schemas
    assert '@field_validator("organization_id", "bot_id", "vertical_id", "subvertical", "primary_objective", mode="before")' in schemas


def test_nearby_bot_studio_actions_are_busy_and_double_submit_guarded():
    runtime = read("frontend/features/bot-studio/shared/useWizardRuntime.ts")
    create = read("frontend/features/bot-studio/create/useCreateFlowController.ts")
    reconfigure = read("frontend/features/bot-studio/reconfigure/useReconfigureFlowController.ts")
    generic = read("frontend/features/bot-studio/flow/useBotStudioFlowActions.ts")
    ai_setup = read("frontend/features/bot-studio/create/AiSetupAssistant.tsx")

    assert "primaryDisabled: Boolean(runtime.busy) || runtime.navigation.primaryDisabled" in runtime
    assert "inFlightRef.current || runtime.busy" in create
    assert "inFlightRef.current || runtime.busy" in reconfigure
    assert "if (inFlightRef.current) return" in generic
    assert "Selecciona una organización e industria antes de generar con IA" in ai_setup
    assert "Selecciona una organización e industria antes de aplicar el wizard" in ai_setup
