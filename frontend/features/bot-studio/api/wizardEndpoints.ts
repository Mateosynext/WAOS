export const WIZARD_START_PATH = "/api/onboarding/wizard/start";
export const WIZARD_BLUEPRINT_PATH = "/api/onboarding/wizard/blueprint";
export const WIZARD_VERTICAL_PROFILE_PATH = "/api/onboarding/wizard/vertical-profile";
export const WIZARD_VERTICALS_PATH = "/api/onboarding/wizard/verticals";

export function buildWizardBasePath(wizardId: string) {
  return `/api/onboarding/wizard/${encodeURIComponent(wizardId)}`;
}

export function buildWizardStepPath(wizardId: string, stepKey: string) {
  return `${buildWizardBasePath(wizardId)}/steps/${encodeURIComponent(stepKey)}`;
}

export function buildWizardDryRunPath(wizardId: string) {
  return `${buildWizardBasePath(wizardId)}/dry-run`;
}

export function buildWizardApplyPath(wizardId: string) {
  return `${buildWizardBasePath(wizardId)}/apply`;
}

export const WIZARD_AI_PREFILL_PATH = "/api/onboarding/wizard/ai-prefill";
export const WIZARD_AI_AUTOPILOT_PATH = "/api/onboarding/wizard/ai-autopilot";

export function buildWizardAiAutofixPath(wizardId: string) {
  return `${buildWizardBasePath(wizardId)}/ai-autofix`;
}
