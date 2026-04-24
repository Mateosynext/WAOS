"use client";

import { useBotStudioCreateFlowActions } from "../flow/useBotStudioCreateFlowActions";
import { buildWizardRuntimeController } from "../shared/useWizardRuntime";
import type { useWizardRuntime } from "../shared/useWizardRuntime";

export function useCreateFlowController(runtime: ReturnType<typeof useWizardRuntime>) {
  const handleCreateNext = useBotStudioCreateFlowActions(runtime.actionDeps);
  const handleNext = async () => {
    try {
      runtime.setBanner(null);
      await handleCreateNext();
    } catch (error) {
      runtime.setBanner({ tone: "error", title: "No se pudo continuar", detail: error instanceof Error ? error.message : "La operación falló." });
    } finally {
      runtime.setBusy("");
    }
  };
  return buildWizardRuntimeController(runtime, handleNext);
}
