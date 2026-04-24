import type { SessionOrganization } from "@/shared/contracts/auth";
import type { BotContract } from "@/shared/contracts/bots";
import type { VerticalProfileContract } from "@/shared/contracts/verticals";
import type { RouteStep } from "@/features/bot-studio/domain/flowConfig";
import type { WizardBlueprint, WizardInstance, WizardMode } from "@/features/bot-studio/domain/wizardTypes";

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
