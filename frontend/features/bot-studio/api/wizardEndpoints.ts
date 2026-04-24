export {
  CLIENT_WIZARD_API_PREFIX,
  clientWizardEndpoints,
  buildWizardApplyPath as buildWizardPathWithPrefix,
  buildWizardBasePath as buildWizardBasePathWithPrefix,
  buildWizardBlueprintPath as buildWizardBlueprintPathWithPrefix,
  buildWizardDryRunPath as buildWizardDryRunPathWithPrefix,
  buildWizardStepPath as buildWizardStepPathWithPrefix,
  buildWizardVerticalProfilePath as buildWizardVerticalProfilePathWithPrefix,
  buildWizardVerticalsPath as buildWizardVerticalsPathWithPrefix,
  type WizardPathRequest,
} from "../services/wizardEndpoints";
import { CLIENT_WIZARD_API_PREFIX, clientWizardEndpoints } from "../services/wizardEndpoints";

export const WIZARD_START_PATH = clientWizardEndpoints.start;
export const WIZARD_BLUEPRINT_PATH = `${CLIENT_WIZARD_API_PREFIX}/blueprint`;
export const WIZARD_VERTICAL_PROFILE_PATH = `${CLIENT_WIZARD_API_PREFIX}/vertical-profile`;
export const WIZARD_VERTICALS_PATH = `${CLIENT_WIZARD_API_PREFIX}/verticals`;

export function buildWizardBasePath(wizardId: string) {
  return clientWizardEndpoints.base(wizardId);
}

export function buildWizardStepPath(wizardId: string, stepKey: string) {
  return clientWizardEndpoints.step(wizardId, stepKey);
}

export function buildWizardDryRunPath(wizardId: string) {
  return clientWizardEndpoints.dryRun(wizardId);
}

export function buildWizardApplyPath(wizardId: string) {
  return clientWizardEndpoints.apply(wizardId);
}
