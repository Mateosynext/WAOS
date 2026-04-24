import type { BotContract } from "@/shared/contracts/bots";
import type { WizardBlueprint, WizardDryRunResult, WizardInstance, WizardValidationSnapshot, WizardError } from "../domain/wizardTypes";

export type ReconfigureSelectViewModel = {
  bots: BotContract[];
  selectedBot?: BotContract | null;
};

export type ReconfigureDiffViewModel = {
  selectedBot?: BotContract | null;
  blueprint?: WizardBlueprint | null;
  wizard?: WizardInstance | null;
};

export type ReconfigureValidationViewModel = ReconfigureDiffViewModel & {
  validationSnapshot?: WizardValidationSnapshot | null;
  dryRunResult?: WizardDryRunResult | null;
  wizardError?: WizardError | string | null;
};

export type ReconfigureSelectActions = {
  setSelectedBotId: (value: string) => void;
};

export type ReconfigureWizardViewModel = ReconfigureSelectViewModel & ReconfigureValidationViewModel;
export type ReconfigureWizardActions = ReconfigureSelectActions;
