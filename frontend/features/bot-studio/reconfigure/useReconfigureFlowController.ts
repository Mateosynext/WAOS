"use client";

import { normalizeWizardError, wizardErrorToMessage } from "../services/wizardClient";
import { useBotStudioReconfigureFlowActions } from "../flow/useBotStudioReconfigureFlowActions";
import { buildWizardRuntimeController } from "../shared/useWizardRuntime";
import type { useWizardRuntime } from "../shared/useWizardRuntime";

export function useReconfigureFlowController(runtime: ReturnType<typeof useWizardRuntime>) {
  const handleReconfigureNext = useBotStudioReconfigureFlowActions(runtime.actionDeps);
  const handleNext = async () => {
    try {
      runtime.setBanner(null);
      runtime.actionDeps.state.setWizardError("");
      await handleReconfigureNext();
    } catch (error) {
      const wizardError = normalizeWizardError(error);
      runtime.actionDeps.state.setWizardError(wizardErrorToMessage(wizardError));
      runtime.setBanner({ tone: "error", title: "No se pudo continuar", detail: wizardErrorToMessage(wizardError) });
    } finally {
      runtime.setBusy("");
    }
  };
  return buildWizardRuntimeController(runtime, handleNext);
}
