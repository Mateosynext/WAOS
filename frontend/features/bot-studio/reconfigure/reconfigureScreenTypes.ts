import type { BotContract } from "@/app/lib/contracts/bots";
import type { WizardBlueprint, WizardDryRunResult, WizardInstance, WizardValidationSnapshot } from "../domain/wizardTypes";

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
};

export type ReconfigureSelectActions = {
  setSelectedBotId: (value: string) => void;
};

export type ReconfigureWizardViewModel = ReconfigureSelectViewModel & ReconfigureValidationViewModel;
export type ReconfigureWizardActions = ReconfigureSelectActions;
