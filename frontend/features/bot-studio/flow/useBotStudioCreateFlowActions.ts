"use client";

import { canAdvanceAfterCreateSave, getCreateClientIncompleteMessage, getCreateRouteMessage, isCreateStepClientReady, isSnapshotApplyReady } from "../../../app/bot-studio/wizardProgressGuards";
import { applyWizardRequest } from "../../../app/bot-studio/wizardApi";
import type { CreateRouteStep, RouteStep } from "../../../app/bot-studio/flowConfig";
import type { WizardInstance } from "../../../app/bot-studio/wizard-types";
import type { BotStudioFlowActionDeps } from "./flowActionDeps";
import { useBotStudioFlowActionHelpers } from "./useBotStudioFlowActionHelpers";

function keepCreateStepUntilBackendAdvances(
  currentStep: CreateRouteStep,
  saved: WizardInstance,
  nextStep: RouteStep,
  goTo: BotStudioFlowActionDeps["goTo"],
  setBanner: BotStudioFlowActionDeps["setBanner"],
) {
  const result = canAdvanceAfterCreateSave(currentStep, saved);
  if (result.ok) {
    goTo(nextStep, saved);
    return;
  }
  const message = getCreateRouteMessage(result.blockingRoute || currentStep);
  setBanner({ tone: "warning", title: message.title, detail: message.detail });
}

export function useBotStudioCreateFlowActions(deps: BotStudioFlowActionDeps) {
  const { goTo, payloads, props, recordOperationEvent, setBanner, setBusy, snapshot, state } = deps;
  const { runDryRun, saveStep, syncWizard } = useBotStudioFlowActionHelpers(deps);

  return async function handleCreateNext() {
    if (["context", "identity", "offer", "knowledge", "integrations"].includes(props.routeStep) && !isCreateStepClientReady(props.routeStep, state as unknown as Record<string, unknown>)) {
      const message = getCreateClientIncompleteMessage(props.routeStep as CreateRouteStep);
      setBanner({ tone: "warning", title: message.title, detail: message.detail });
      return;
    }
    if (props.routeStep === "context") return void keepCreateStepUntilBackendAdvances("context", await saveStep("vertical_fit", payloads.scope), "identity", goTo, setBanner);
    if (props.routeStep === "identity") return void keepCreateStepUntilBackendAdvances("identity", await saveStep("business_basics", payloads.basics), "offer", goTo, setBanner);
    if (props.routeStep === "offer") return void keepCreateStepUntilBackendAdvances("offer", await saveStep("catalog_offer", payloads.catalog), "knowledge", goTo, setBanner);
    if (props.routeStep === "knowledge") return void keepCreateStepUntilBackendAdvances("knowledge", await saveStep("knowledge_seed", payloads.knowledge), "integrations", goTo, setBanner);
    if (props.routeStep === "integrations") return void keepCreateStepUntilBackendAdvances("integrations", await saveStep("integrations_rules", payloads.integrations), "review", goTo, setBanner);
    if (props.routeStep === "review") return void goTo("validate", await saveStep("launch_review", payloads.launchReview));
    if (props.routeStep === "validate") {
      if (!state.dryRunResult) await runDryRun("Ejecutando dry run", "Dry run listo", "Dry run completado con pendientes", "El draft fue validado, pero el gate todavía no permite aplicar. Corrige los pasos marcados y vuelve a validar.");
      if (!isSnapshotApplyReady(snapshot)) {
        const message = getCreateRouteMessage("apply");
        setBanner({ tone: "warning", title: message.title, detail: message.detail });
        return;
      }
      return void goTo("apply", state.wizard);
    }
    if (props.routeStep !== "apply" || !state.wizardId) return;
    if (!isSnapshotApplyReady(snapshot)) {
      const message = getCreateRouteMessage("apply");
      setBanner({ tone: "warning", title: message.title, detail: message.detail });
      return;
    }
    setBusy("Aplicando cambios");
    recordOperationEvent("wizard.apply.started", { mode: props.routeMode }, state.wizardId);
    const result = await applyWizardRequest(state.wizardId);
    state.setApplyResult(result);
    if (result.wizard) syncWizard(result.wizard);
    recordOperationEvent("wizard.apply.completed", { mode: props.routeMode, status: result.wizard?.status || null }, result.wizard?.id || state.wizardId);
    goTo("success", result.wizard);
  };
}
