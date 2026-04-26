"use client";

import { useRef } from "react";
import { useBotStudioCreateFlowActions } from "../flow/useBotStudioCreateFlowActions";
import { buildWizardRuntimeController } from "../shared/useWizardRuntime";
import type { useWizardRuntime } from "../shared/useWizardRuntime";

export function useCreateFlowController(runtime: ReturnType<typeof useWizardRuntime>) {
  const handleCreateNext = useBotStudioCreateFlowActions(runtime.actionDeps);
  const inFlightRef = useRef(false);
  const handleNext = async () => {
    if (inFlightRef.current || runtime.busy) return;
    inFlightRef.current = true;
    try {
      runtime.setBanner(null);
      await handleCreateNext();
    } catch (error) {
      runtime.setBanner({ tone: "error", title: "No se pudo continuar", detail: error instanceof Error ? error.message : "La operación falló." });
    } finally {
      inFlightRef.current = false;
      runtime.setBusy("");
    }
  };
  return buildWizardRuntimeController(runtime, handleNext);
}
