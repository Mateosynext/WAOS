"use client";

import { applyWizardRequest } from "../../../app/bot-studio/wizardApi";
import { isSnapshotApplyReady } from "../../../app/bot-studio/wizardProgressGuards";
import type { BotStudioFlowActionDeps } from "./flowActionDeps";
import { useBotStudioFlowActionHelpers } from "./useBotStudioFlowActionHelpers";

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
      if (!state.dryRunResult) await runDryRun("Corriendo dry run", "Dry run listo", "Dry run con bloqueos", "La reconfiguración quedó validada pero todavía no puede aplicarse. Revisa el gate antes de confirmar.");
      if (!isSnapshotApplyReady(snapshot)) {
        setBanner({ tone: "warning", title: "Confirmación bloqueada", detail: "La confirmación sigue bloqueada hasta que el dry run quede en verde." });
        return;
      }
      return void goTo("confirm", state.wizard);
    }
    if (props.routeStep !== "confirm" || !state.wizardId) return;
    if (!isSnapshotApplyReady(snapshot)) {
      setBanner({ tone: "warning", title: "Apply bloqueado", detail: "La reconfiguración todavía no tiene un dry run apto para aplicar." });
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
