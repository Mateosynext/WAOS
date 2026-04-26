"use client";

import { useRef } from "react";
import type { BotStudioFlowActionDeps } from "./flowActionDeps";
import { useBotStudioCreateFlowActions } from "./useBotStudioCreateFlowActions";
import { useBotStudioReconfigureFlowActions } from "./useBotStudioReconfigureFlowActions";

export function useBotStudioFlowActions(deps: BotStudioFlowActionDeps) {
  const handleCreateNext = useBotStudioCreateFlowActions(deps);
  const handleReconfigureNext = useBotStudioReconfigureFlowActions(deps);
  const inFlightRef = useRef(false);

  return {
    handleNext: async () => {
      if (inFlightRef.current) return;
      inFlightRef.current = true;
      try {
        deps.setBanner(null);
        if (deps.props.routeMode === "create") await handleCreateNext();
        if (deps.props.routeMode === "reconfigure") await handleReconfigureNext();
      } catch (error) {
        deps.setBanner({ tone: "error", title: "No se pudo continuar", detail: error instanceof Error ? error.message : "La operación falló." });
      } finally {
        inFlightRef.current = false;
        deps.setBusy("");
      }
    },
  };
}
