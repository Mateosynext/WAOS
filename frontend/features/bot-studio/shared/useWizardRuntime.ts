"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { getFlowSteps, type RouteStep } from "@/features/bot-studio/domain/flowConfig";
import { canEnterWizardRoute, getCurrentWizardRevision, getValidatedWizardRevisionFromWizard, isWizardValidationFresh } from "@/features/bot-studio/domain/wizardProgressGuards";
import { getWizardRouteRecovery } from "@/features/bot-studio/domain/wizardFlowRecovery";
import type { BotStudioWizardStateModel } from "../context/useBotStudioWizardState";
import { useBotStudioFlowNavigation } from "../flow/useBotStudioFlowNavigation";
import { useBotStudioFlowStateModel } from "../flow/useBotStudioFlowStateModel";
import { useBotStudioFlowTelemetry } from "../flow/useBotStudioFlowTelemetry";
import type { BotStudioFlowActionDeps } from "../flow/flowActionDeps";
import type { BannerState, BotStudioFlowProps } from "../flow/types";

type HandleNext = () => Promise<void>;

export type WizardRuntimeController = {
  banner: BannerState | null;
  busy: string;
  currentIndex: number;
  currentStepMeta: ReturnType<typeof useBotStudioFlowNavigation>["currentStepMeta"];
  createScreens: ReturnType<typeof useBotStudioFlowStateModel>["createScreens"];
  flowSteps: ReturnType<typeof useBotStudioFlowNavigation>["flowSteps"];
  goTo: ReturnType<typeof useBotStudioFlowNavigation>["goTo"];
  handleNext: HandleNext;
  prev: ReturnType<typeof useBotStudioFlowNavigation>["prev"];
  primaryDisabled: boolean;
  primaryLabel: string;
  primaryTestId: string | undefined;
  progress: number;
  reconfigureScreens: ReturnType<typeof useBotStudioFlowStateModel>["reconfigureScreens"];
  summary: ReturnType<typeof useBotStudioFlowStateModel>["summary"];
};

export function useWizardRuntime(props: BotStudioFlowProps, state: BotStudioWizardStateModel) {
  const [banner, setBanner] = useState<BannerState | null>(null);
  const [busy, setBusy] = useState("");
  const flowSteps = getFlowSteps(props.routeMode);
  const currentIndex = flowSteps.findIndex((item) => item.key === props.routeStep);
  const progressBase = ((currentIndex + 1) / flowSteps.length) * 100;
  const stateModel = useBotStudioFlowStateModel(props, state, progressBase);
  const telemetry = useBotStudioFlowTelemetry(props, state);
  const navigation = useBotStudioFlowNavigation(props, state, stateModel.snapshot);
  const lastRedirectRef = useRef("");

  const actionDeps: BotStudioFlowActionDeps = useMemo(() => ({
    props,
    state,
    payloads: stateModel.payloads,
    snapshot: stateModel.snapshot,
    goTo: navigation.goTo,
    setBanner,
    setBusy,
    recordOperationEvent: telemetry.recordOperationEvent,
    recordAutosaveResult: telemetry.recordAutosaveResult,
  }), [navigation.goTo, props, state, stateModel.payloads, stateModel.snapshot, telemetry.recordAutosaveResult, telemetry.recordOperationEvent]);

  useEffect(() => {
    const activeWizard = state.wizard || props.initialWizard || null;
    const redirectOnce = (targetStep: RouteStep, wizard?: { id: string } | null) => {
      const redirectKey = `${props.routeMode}:${props.routeStep}:${targetStep}:${wizard?.id || ""}`;
      if (lastRedirectRef.current === redirectKey) return;
      lastRedirectRef.current = redirectKey;
      navigation.goTo(targetStep, wizard);
    };
    const routeGuard = canEnterWizardRoute({
      mode: props.routeMode,
      routeStep: props.routeStep,
      state: state as unknown as Record<string, unknown>,
      selectedBotId: state.selectedBotId || stateModel.selectedBot?.id,
      wizard: activeWizard,
      snapshot: stateModel.snapshot,
      validatedWizardRevision: state.validatedWizardRevision ?? getValidatedWizardRevisionFromWizard(activeWizard),
      hasAppliedWizard: Boolean(state.applyResult?.wizard),
    });
    if (!routeGuard.ok) {
      setBanner({ tone: "warning", title: "Ruta inválida", detail: `${routeGuard.title}. ${routeGuard.detail}` });
      if (routeGuard.blockingRoute !== props.routeStep) redirectOnce(routeGuard.blockingRoute, activeWizard);
      return;
    }

    const currentWizardRevision = getCurrentWizardRevision(activeWizard);
    const hasFreshDryRun = Boolean(state.dryRunResult || getValidatedWizardRevisionFromWizard(activeWizard)) && isWizardValidationFresh({ wizardRevision: currentWizardRevision, validatedWizardRevision: state.validatedWizardRevision ?? getValidatedWizardRevisionFromWizard(activeWizard) });
    const recovery = getWizardRouteRecovery({
      mode: props.routeMode,
      routeStep: props.routeStep,
      wizard: activeWizard,
      hasDryRunResult: hasFreshDryRun,
      hasSelectedBot: Boolean(state.selectedBotId || stateModel.selectedBot?.id),
    });
    if (!recovery) {
      lastRedirectRef.current = "";
      return;
    }
    setBanner({ tone: "warning", title: "Ruta recuperada", detail: recovery.message });
    redirectOnce(recovery.routeStep, activeWizard);
  }, [navigation.goTo, props.initialWizard, props.routeMode, props.routeStep, state, stateModel.selectedBot?.id, stateModel.snapshot]);

  return { actionDeps, banner, busy, navigation, setBanner, setBusy, stateModel };
}

export function buildWizardRuntimeController(runtime: ReturnType<typeof useWizardRuntime>, handleNext: HandleNext): WizardRuntimeController {
  return {
    banner: runtime.banner,
    busy: runtime.busy,
    currentIndex: runtime.navigation.currentIndex,
    currentStepMeta: runtime.navigation.currentStepMeta,
    createScreens: runtime.stateModel.createScreens,
    flowSteps: runtime.navigation.flowSteps,
    goTo: runtime.navigation.goTo,
    handleNext,
    prev: runtime.navigation.prev,
    primaryDisabled: Boolean(runtime.busy) || runtime.navigation.primaryDisabled,
    primaryLabel: runtime.navigation.primaryLabel,
    primaryTestId: runtime.navigation.primaryTestId,
    progress: runtime.navigation.progress,
    reconfigureScreens: runtime.stateModel.reconfigureScreens,
    summary: runtime.stateModel.summary,
  };
}
