"use client";

import { canAdvanceAfterCreateSave, getCreateClientIncompleteMessage, getCreateRouteMessage, getCurrentWizardRevision, getValidatedWizardRevisionFromWizard, isCreateStepClientReady, isSnapshotApplyReady } from "@/features/bot-studio/domain/wizardProgressGuards";
import { applyWizardRequest } from "@/features/bot-studio/services/wizardApi";
import type { CreateRouteStep, RouteStep } from "@/features/bot-studio/domain/flowConfig";
import type { WizardDryRunResult, WizardInstance } from "@/features/bot-studio/domain/wizardTypes";
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

function getValidationContext(state: BotStudioFlowActionDeps["state"], snapshot: BotStudioFlowActionDeps["snapshot"], dryRunResult?: WizardDryRunResult | null) {
  const wizard = dryRunResult?.wizard || state.wizard;
  return {
    snapshot: dryRunResult?.validation_snapshot || dryRunResult?.wizard?.validation_snapshot || snapshot,
    wizardRevision: getCurrentWizardRevision(wizard),
    validatedWizardRevision: dryRunResult ? (getCurrentWizardRevision(dryRunResult.wizard) ?? getValidatedWizardRevisionFromWizard(dryRunResult.wizard) ?? getCurrentWizardRevision(state.wizard) ?? getValidatedWizardRevisionFromWizard(state.wizard) ?? state.validatedWizardRevision) : state.validatedWizardRevision,
  };
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
      const dryRunResult = state.dryRunResult || await runDryRun("Ejecutando dry run", "Dry run listo", "Dry run completado con pendientes", "El draft fue validado, pero el gate todavía no permite aplicar. Corrige los pasos marcados y vuelve a validar.");
      const validation = getValidationContext(state, snapshot, dryRunResult);
      if (!isSnapshotApplyReady(validation.snapshot, { wizardRevision: validation.wizardRevision, validatedWizardRevision: validation.validatedWizardRevision })) {
        const message = getCreateRouteMessage("apply");
        setBanner({ tone: "warning", title: message.title, detail: message.detail });
        return;
      }
      return void goTo("apply", dryRunResult?.wizard || state.wizard);
    }
    if (props.routeStep !== "apply" || !state.wizardId) return;
    const validation = getValidationContext(state, snapshot, null);
    if (!isSnapshotApplyReady(validation.snapshot, { wizardRevision: validation.wizardRevision, validatedWizardRevision: validation.validatedWizardRevision })) {
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
