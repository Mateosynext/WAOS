"use client";

import type { BotStudioFlowActionDeps } from "./flowActionDeps";
import { useBotStudioCreateFlowActions } from "./useBotStudioCreateFlowActions";
import { useBotStudioReconfigureFlowActions } from "./useBotStudioReconfigureFlowActions";

export function useBotStudioFlowActions(deps: BotStudioFlowActionDeps) {
  const handleCreateNext = useBotStudioCreateFlowActions(deps);
  const handleReconfigureNext = useBotStudioReconfigureFlowActions(deps);

  return {
    handleNext: async () => {
      try {
        deps.setBanner(null);
        if (deps.props.routeMode === "create") await handleCreateNext();
        if (deps.props.routeMode === "reconfigure") await handleReconfigureNext();
      } catch (error) {
        deps.setBanner({ tone: "error", title: "No se pudo continuar", detail: error instanceof Error ? error.message : "La operación falló." });
      } finally {
        deps.setBusy("");
      }
    },
  };
}
