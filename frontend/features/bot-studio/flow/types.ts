import type { BotContract, SessionOrganization, VerticalProfileContract } from "../../../app/lib/contracts";
import type { RouteStep } from "../../../app/bot-studio/flowConfig";
import type { WizardBlueprint, WizardInstance, WizardMode } from "../../../app/bot-studio/wizard-types";

export type BotStudioFlowProps = {
  organizations: SessionOrganization[];
  verticals: VerticalProfileContract[];
  strongestVerticals: VerticalProfileContract[];
  bots: BotContract[];
  initialSelectedBotId: string;
  initialMode: WizardMode;
  initialOrganizationId: string;
  initialVerticalId: string;
  initialSubvertical: string;
  initialPrimaryObjective: string;
  initialBlueprint: WizardBlueprint | null;
  initialVerticalProfile: VerticalProfileContract | null;
  initialWizardId?: string;
  initialWizard?: WizardInstance | null;
  initialStepOverride?: string;
  routeMode: WizardMode;
  routeStep: RouteStep;
};

export type BannerTone = "info" | "success" | "warning" | "error";

export type BannerState = {
  tone: BannerTone;
  title: string;
  detail: string;
};
