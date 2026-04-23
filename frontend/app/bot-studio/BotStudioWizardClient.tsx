"use client";

import type { BotContract, SessionOrganization, VerticalProfileContract } from "../lib/contracts";
import BotStudioFlowClient from "./BotStudioFlowClient";
import { normalizeRouteStep, type RouteStep } from "./flowConfig";
import type { WizardBlueprint, WizardInstance, WizardMode } from "./wizard-types";

export type BotStudioWizardClientProps = {
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
};

export default function BotStudioWizardClient(props: BotStudioWizardClientProps) {
  const routeMode = props.initialMode;
  const routeStep = (normalizeRouteStep(routeMode, props.initialStepOverride) || (routeMode === "reconfigure" ? "select" : "context")) as RouteStep;
  return <BotStudioFlowClient {...props} routeMode={routeMode} routeStep={routeStep} />;
}
