"use client";

import { useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { buildBotStudioHref, getFlowSteps, getNextRouteStep, getPreviousRouteStep, getStepMeta, type RouteStep } from "@/features/bot-studio/domain/flowConfig";
import { buildWizardAwareRouteQuery } from "@/features/bot-studio/domain/navigationState";
import { getCurrentWizardRevision, getValidatedWizardRevisionFromWizard, isCreateStepClientReady, isSnapshotApplyReady } from "@/features/bot-studio/domain/wizardProgressGuards";
import { useBotStudioWizardState } from "../context/useBotStudioWizardState";
import type { WizardValidationSnapshot } from "@/features/bot-studio/domain/wizardTypes";
import type { BotStudioFlowProps } from "./types";

export function useBotStudioFlowNavigation(
  props: BotStudioFlowProps,
  state: ReturnType<typeof useBotStudioWizardState>,
  snapshot: WizardValidationSnapshot | null,
) {
  const router = useRouter();
  const flowSteps = getFlowSteps(props.routeMode);
  const currentIndex = flowSteps.findIndex((item) => item.key === props.routeStep);
  const currentStepMeta = getStepMeta(props.routeMode, props.routeStep);
  const progress = ((currentIndex + 1) / flowSteps.length) * 100;

  const buildRouteQuery = useCallback((wizardIdOverride?: string | null) => buildWizardAwareRouteQuery({
    wizardId: state.wizardId,
    botId: props.routeMode === "reconfigure" ? state.selectedBotId : undefined,
    organizationId: state.selectedOrganizationId,
    verticalId: state.selectedVerticalId,
    subvertical: state.selectedSubvertical,
    primaryObjective: state.selectedPrimaryObjective,
  }, wizardIdOverride), [
    props.routeMode,
    state.selectedBotId,
    state.selectedOrganizationId,
    state.selectedPrimaryObjective,
    state.selectedSubvertical,
    state.selectedVerticalId,
    state.wizardId,
  ]);

  const goTo = useCallback((step: RouteStep, wizard?: { id: string } | null) => {
    router.push(buildBotStudioHref(props.routeMode, step, buildRouteQuery(wizard?.id)));
  }, [buildRouteQuery, props.routeMode, router]);

  const prev = getPreviousRouteStep(props.routeMode, props.routeStep);
  const createPrimaryTestIds: Partial<Record<RouteStep, string>> = {
    context: "save-scope",
    identity: "save-basics",
    offer: "save-offer",
    knowledge: "save-knowledge",
    integrations: "save-integrations",
    review: "save-review",
    validate: state.dryRunResult ? "continue-to-apply" : "run-dry-run",
    apply: "apply-wizard",
  };
  const reconfigurePrimaryTestIds: Partial<Record<RouteStep, string>> = {
    select: "prepare-reconfigure",
    diff: "continue-diff",
    "dry-run": state.dryRunResult ? "continue-confirmation" : "run-dry-run",
    confirm: "apply-wizard",
  };

  const primaryTestId = props.routeMode === "create" ? createPrimaryTestIds[props.routeStep] : reconfigurePrimaryTestIds[props.routeStep];
  const primaryLabel = props.routeMode === "create"
    ? props.routeStep === "validate"
      ? (state.dryRunResult ? "Continuar a apply" : "Ejecutar dry run")
      : props.routeStep === "apply"
        ? "Aplicar cambios"
        : props.routeStep === "success"
          ? ""
          : `Continuar a ${getStepMeta(props.routeMode, getNextRouteStep(props.routeMode, props.routeStep) || props.routeStep)?.label}`
    : props.routeStep === "dry-run"
      ? (state.dryRunResult ? "Continuar a confirmar" : "Ejecutar dry run")
      : props.routeStep === "confirm"
        ? "Aplicar reconfiguración"
        : props.routeStep === "result"
          ? ""
          : `Continuar a ${getStepMeta(props.routeMode, getNextRouteStep(props.routeMode, props.routeStep) || props.routeStep)?.label}`;

  const primaryDisabled = useMemo(() => {
    const freshness = { wizardRevision: getCurrentWizardRevision(state.wizard), validatedWizardRevision: state.validatedWizardRevision ?? getValidatedWizardRevisionFromWizard(state.wizard) };
    if (props.routeMode === "create") {
      if (["context", "identity", "offer", "knowledge", "integrations"].includes(props.routeStep)) {
        return !isCreateStepClientReady(props.routeStep, state as unknown as Record<string, unknown>);
      }
      if (props.routeStep === "validate" && state.dryRunResult) return !isSnapshotApplyReady(snapshot, freshness);
      if (props.routeStep === "apply") return !isSnapshotApplyReady(snapshot, freshness);
      return false;
    }
    if (props.routeStep === "select") return !state.selectedBotId;
    if (props.routeStep === "dry-run" && state.dryRunResult) return !isSnapshotApplyReady(snapshot, freshness);
    if (props.routeStep === "confirm") return !isSnapshotApplyReady(snapshot, freshness);
    return false;
  }, [props.routeMode, props.routeStep, snapshot, state]);

  return { currentIndex, currentStepMeta, flowSteps, goTo, prev, primaryDisabled, primaryLabel, primaryTestId, progress };
}
