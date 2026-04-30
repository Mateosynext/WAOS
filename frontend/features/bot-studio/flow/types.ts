import type { SessionOrganization } from "@/app/lib/contracts/auth";
import type { BotContract } from "@/app/lib/contracts/bots";
import type { VerticalProfileContract } from "@/app/lib/contracts/verticals";
import type { RouteStep } from "@/features/bot-studio/domain/flowConfig";
import type { WizardBlueprint, WizardInstance, WizardMode } from "@/features/bot-studio/domain/wizardTypes";
export type BotStudioLoadWarning = { source: string; message: string };

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
  loadWarnings?: BotStudioLoadWarning[];
  routeMode: WizardMode;
  routeStep: RouteStep;
};

export type BannerTone = "info" | "success" | "warning" | "error";

export type BannerState = {
  tone: BannerTone;
  title: string;
  detail: string;
};
