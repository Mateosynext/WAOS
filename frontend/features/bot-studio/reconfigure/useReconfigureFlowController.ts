"use client";

import { useBotStudioReconfigureFlowActions } from "../flow/useBotStudioReconfigureFlowActions";
import { buildWizardRuntimeController } from "../shared/useWizardRuntime";
import type { useWizardRuntime } from "../shared/useWizardRuntime";

export function useReconfigureFlowController(runtime: ReturnType<typeof useWizardRuntime>) {
  const handleReconfigureNext = useBotStudioReconfigureFlowActions(runtime.actionDeps);
  const handleNext = async () => {
    try {
      runtime.setBanner(null);
      await handleReconfigureNext();
    } catch (error) {
      runtime.setBanner({ tone: "error", title: "No se pudo continuar", detail: error instanceof Error ? error.message : "La operación falló." });
    } finally {
      runtime.setBusy("");
    }
  };
  return buildWizardRuntimeController(runtime, handleNext);
}
