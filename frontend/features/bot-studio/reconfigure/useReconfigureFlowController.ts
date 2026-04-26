"use client";

import { useRef } from "react";
import { useBotStudioReconfigureFlowActions } from "../flow/useBotStudioReconfigureFlowActions";
import { buildWizardRuntimeController } from "../shared/useWizardRuntime";
import type { useWizardRuntime } from "../shared/useWizardRuntime";

export function useReconfigureFlowController(runtime: ReturnType<typeof useWizardRuntime>) {
  const handleReconfigureNext = useBotStudioReconfigureFlowActions(runtime.actionDeps);
  const inFlightRef = useRef(false);
  const handleNext = async () => {
    if (inFlightRef.current || runtime.busy) return;
    inFlightRef.current = true;
    try {
      runtime.setBanner(null);
      await handleReconfigureNext();
    } catch (error) {
      runtime.setBanner({ tone: "error", title: "No se pudo continuar", detail: error instanceof Error ? error.message : "La operación falló." });
    } finally {
      inFlightRef.current = false;
      runtime.setBusy("");
    }
  };
  return buildWizardRuntimeController(runtime, handleNext);
}
