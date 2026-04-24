"use client";

import { applyWizardRequest } from "@/features/bot-studio/services/wizardApi";
import { getCurrentWizardRevision, getValidatedWizardRevisionFromWizard, isSnapshotApplyReady } from "@/features/bot-studio/domain/wizardProgressGuards";
import type { WizardDryRunResult } from "@/features/bot-studio/domain/wizardTypes";
import type { BotStudioFlowActionDeps } from "./flowActionDeps";
import { useBotStudioFlowActionHelpers } from "./useBotStudioFlowActionHelpers";

function getValidationContext(state: BotStudioFlowActionDeps["state"], snapshot: BotStudioFlowActionDeps["snapshot"], dryRunResult?: WizardDryRunResult | null) {
  const wizard = dryRunResult?.wizard || state.wizard;
  return {
    snapshot: dryRunResult?.validation_snapshot || dryRunResult?.wizard?.validation_snapshot || snapshot,
    wizardRevision: getCurrentWizardRevision(wizard),
    validatedWizardRevision: dryRunResult ? (getCurrentWizardRevision(dryRunResult.wizard) ?? getValidatedWizardRevisionFromWizard(dryRunResult.wizard) ?? getCurrentWizardRevision(state.wizard) ?? getValidatedWizardRevisionFromWizard(state.wizard) ?? state.validatedWizardRevision) : state.validatedWizardRevision,
  };
}

export function useBotStudioReconfigureFlowActions(deps: BotStudioFlowActionDeps) {
  const { goTo, props, recordOperationEvent, setBanner, setBusy, snapshot, state } = deps;
  const { ensureWizard, runDryRun, syncWizard } = useBotStudioFlowActionHelpers(deps);

  return async function handleReconfigureNext() {
    if (props.routeStep === "select") {
      if (!state.selectedBotId) {
        setBanner({ tone: "warning", title: "Selecciona un bot", detail: "La reconfiguración necesita un bot explícito antes de seguir." });
        return;
      }
      setBusy("Preparando diff");
      const started = await ensureWizard();
      state.setWizardId(started.id);
      goTo("diff", started);
      return;
    }
    if (props.routeStep === "diff") return void goTo("dry-run", state.wizard);
    if (props.routeStep === "dry-run") {
      if (!state.wizardId) return;
      const dryRunResult = state.dryRunResult || await runDryRun("Corriendo dry run", "Dry run listo", "Dry run con bloqueos", "La reconfiguración quedó validada pero todavía no puede aplicarse. Revisa el gate antes de confirmar.");
      const validation = getValidationContext(state, snapshot, dryRunResult);
      if (!isSnapshotApplyReady(validation.snapshot, { wizardRevision: validation.wizardRevision, validatedWizardRevision: validation.validatedWizardRevision })) {
        setBanner({ tone: "warning", title: "Confirmación bloqueada", detail: "La confirmación sigue bloqueada hasta que el dry run quede en verde y corresponda a la revisión actual." });
        return;
      }
      return void goTo("confirm", dryRunResult?.wizard || state.wizard);
    }
    if (props.routeStep !== "confirm" || !state.wizardId) return;
    const validation = getValidationContext(state, snapshot, null);
    if (!isSnapshotApplyReady(validation.snapshot, { wizardRevision: validation.wizardRevision, validatedWizardRevision: validation.validatedWizardRevision })) {
      setBanner({ tone: "warning", title: "Apply bloqueado", detail: "La reconfiguración todavía no tiene un dry run fresco apto para aplicar." });
      return;
    }
    setBusy("Aplicando reconfiguración");
    recordOperationEvent("wizard.apply.started", { mode: props.routeMode }, state.wizardId);
    const result = await applyWizardRequest(state.wizardId);
    state.setApplyResult(result);
    if (result.wizard) syncWizard(result.wizard);
    recordOperationEvent("wizard.apply.completed", { mode: props.routeMode, status: result.wizard?.status || null }, result.wizard?.id || state.wizardId);
    goTo("result", result.wizard);
  };
}
