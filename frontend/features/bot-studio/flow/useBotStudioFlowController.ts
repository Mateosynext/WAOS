"use client";

import { useBotStudioWizardState } from "../context/useBotStudioWizardState";
import { useCreateFlowController } from "../create/useCreateFlowController";
import { useReconfigureFlowController } from "../reconfigure/useReconfigureFlowController";
import { useWizardRuntime } from "../shared/useWizardRuntime";
import type { BotStudioFlowProps } from "./types";

export function useBotStudioFlowController(props: BotStudioFlowProps, state: ReturnType<typeof useBotStudioWizardState>) {
  const runtime = useWizardRuntime(props, state);
  const createController = useCreateFlowController(runtime);
  const reconfigureController = useReconfigureFlowController(runtime);
  return props.routeMode === "create" ? createController : reconfigureController;
}
