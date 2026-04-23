"use client";

import { useEffect, useMemo, useState } from "react";
import { getFlowSteps } from "../../../app/bot-studio/flowConfig";
import { getWizardRouteRecovery } from "../../../app/bot-studio/wizardFlowRecovery";
import { useBotStudioWizardState } from "../context/useBotStudioWizardState";
import { useBotStudioFlowActions } from "./useBotStudioFlowActions";
import { useBotStudioFlowNavigation } from "./useBotStudioFlowNavigation";
import { useBotStudioFlowStateModel } from "./useBotStudioFlowStateModel";
import { useBotStudioFlowTelemetry } from "./useBotStudioFlowTelemetry";
import type { BannerState, BotStudioFlowProps } from "./types";

export function useBotStudioFlowController(props: BotStudioFlowProps, state: ReturnType<typeof useBotStudioWizardState>) {
  const [banner, setBanner] = useState<BannerState | null>(null);
  const [busy, setBusy] = useState("");
  const flowSteps = getFlowSteps(props.routeMode);
  const currentIndex = flowSteps.findIndex((item) => item.key === props.routeStep);
  const progress = ((currentIndex + 1) / flowSteps.length) * 100;
  const stateModel = useBotStudioFlowStateModel(props, state, progress);
  const telemetry = useBotStudioFlowTelemetry(props, state);
  const navigation = useBotStudioFlowNavigation(props, state, stateModel.snapshot);
  const actionDeps = useMemo(() => ({
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
  const actions = useBotStudioFlowActions(actionDeps);

  useEffect(() => {
    const recovery = getWizardRouteRecovery({
      mode: props.routeMode,
      routeStep: props.routeStep,
      wizard: state.wizard || props.initialWizard || null,
      hasDryRunResult: Boolean(state.dryRunResult || stateModel.snapshot),
      hasSelectedBot: Boolean(state.selectedBotId || stateModel.selectedBot?.id),
    });
    if (!recovery) return;
    setBanner({ tone: "warning", title: "Ruta recuperada", detail: recovery.message });
    navigation.goTo(recovery.routeStep, state.wizard || props.initialWizard || null);
  }, [navigation.goTo, props.initialWizard, props.routeMode, props.routeStep, state.dryRunResult, state.selectedBotId, state.wizard, stateModel.selectedBot?.id, stateModel.snapshot]);

  return { banner, busy, currentIndex: navigation.currentIndex, currentStepMeta: navigation.currentStepMeta, createState: stateModel.createState, flowSteps: navigation.flowSteps, goTo: navigation.goTo, handleNext: actions.handleNext, prev: navigation.prev, primaryDisabled: navigation.primaryDisabled, primaryLabel: navigation.primaryLabel, primaryTestId: navigation.primaryTestId, progress: navigation.progress, reconfigureState: stateModel.reconfigureState, summary: stateModel.summary };
}
