import type { CreateRouteStep, ReconfigureRouteStep, RouteStep } from "./flowConfig";
import { deriveWizardConsistencyRecovery } from "./wizardEnterpriseGuards";
import { resolveWizardInitialStep, type WizardUiActiveStep } from "./wizardStepFlow";
import type { WizardInstance, WizardMode } from "./wizardTypes";

function hasWizardSelection(mode: WizardMode, hasSelectedBot: boolean): boolean {
  return mode === "create" ? true : hasSelectedBot;
}

export function mapRouteStepToWizardUiStep(mode: WizardMode, step: RouteStep): WizardUiActiveStep {
  if (mode === "create") {
    switch (step as CreateRouteStep) {
      case "context":
        return "scope";
      case "identity":
        return "basics";
      case "offer":
        return "offer";
      case "knowledge":
        return "knowledge";
      case "integrations":
        return "integrations";
      case "review":
        return "review";
      case "validate":
        return "dry_run";
      case "apply":
        return "confirm";
      case "success":
        return "publish";
      default:
        return "scope";
    }
  }

  switch (step as ReconfigureRouteStep) {
    case "select":
      return "review";
    case "diff":
      return "review";
    case "dry-run":
      return "dry_run";
    case "confirm":
      return "confirm";
    case "result":
      return "publish";
    default:
      return "review";
  }
}

export function mapWizardUiStepToRouteStep(mode: WizardMode, step: WizardUiActiveStep, hasSelectedBot = false): RouteStep {
  if (mode === "create") {
    switch (step) {
      case "scope":
        return "context";
      case "basics":
        return "identity";
      case "offer":
        return "offer";
      case "knowledge":
        return "knowledge";
      case "integrations":
        return "integrations";
      case "review":
        return "review";
      case "dry_run":
      case "simulate":
        return "validate";
      case "confirm":
        return "apply";
      case "publish":
        return "success";
      default:
        return "context";
    }
  }

  if (step === "dry_run" || step === "simulate") return "dry-run";
  if (step === "confirm" || step === "publish") return step === "confirm" ? "confirm" : "result";
  return hasWizardSelection(mode, hasSelectedBot) ? "diff" : "select";
}

export function getWizardRouteRecovery(args: {
  mode: WizardMode;
  routeStep: RouteStep;
  wizard: WizardInstance | null;
  hasDryRunResult: boolean;
  hasSelectedBot?: boolean;
}) {
  const persistedStep = resolveWizardInitialStep(args.mode, args.wizard || null, undefined);
  const recovery = deriveWizardConsistencyRecovery({
    mode: args.mode,
    activeStep: mapRouteStepToWizardUiStep(args.mode, args.routeStep),
    persistedStep,
    clientAllowedStep: persistedStep,
    wizardStatus: args.wizard?.status,
    hasDryRunResult: args.hasDryRunResult,
    hasAppliedWizard: args.wizard?.status === "applied",
  });

  if (!recovery) return null;

  const nextRouteStep = mapWizardUiStepToRouteStep(args.mode, recovery.step, Boolean(args.hasSelectedBot));
  if (nextRouteStep === args.routeStep) return null;

  return {
    ...recovery,
    routeStep: nextRouteStep,
  };
}
