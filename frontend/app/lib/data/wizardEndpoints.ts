export type { WizardPathRequest as WizardBlueprintPathRequest } from "@/features/bot-studio/services/wizardEndpoints";
export { SERVER_WIZARD_API_PREFIX as WIZARD_API_PREFIX, serverWizardEndpoints } from "@/features/bot-studio/services/wizardEndpoints";
import { serverWizardEndpoints } from "@/features/bot-studio/services/wizardEndpoints";
import type { WizardPathRequest } from "@/features/bot-studio/services/wizardEndpoints";

export function buildWizardBackendBasePath(wizardId: string) {
  return serverWizardEndpoints.base(wizardId);
}

export function buildWizardStepBackendPath(wizardId: string, stepKey: string) {
  return serverWizardEndpoints.step(wizardId, stepKey);
}

export function buildWizardDryRunBackendPath(wizardId: string) {
  return serverWizardEndpoints.dryRun(wizardId);
}

export function buildWizardApplyBackendPath(wizardId: string) {
  return serverWizardEndpoints.apply(wizardId);
}

export function buildWizardBlueprintBackendPath(request: WizardPathRequest) {
  return serverWizardEndpoints.blueprint(request);
}
