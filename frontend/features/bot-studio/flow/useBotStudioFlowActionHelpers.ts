"use client";

import { applyWizardRequest, dryRunWizardRequest, saveWizardStepRequest, startWizardRequest } from "../../../app/bot-studio/wizardApi";
import { isSnapshotApplyReady } from "../../../app/bot-studio/wizardProgressGuards";
import { safeText } from "../../../app/lib/ui";
import type { WizardInstance } from "../../../app/bot-studio/wizard-types";
import type { BotStudioFlowActionDeps } from "./flowActionDeps";

export function useBotStudioFlowActionHelpers(deps: BotStudioFlowActionDeps) {
  const { payloads, props, recordAutosaveResult, recordOperationEvent, setBanner, setBusy, state } = deps;

  const syncWizard = (wizard: WizardInstance) => {
    state.setWizard(wizard);
    state.setWizardId(wizard.id);
    state.setAutosaveState("saved");
    state.setAutosaveError("");
    state.setWizardError("");
    state.setLastSavedAt(safeText(wizard.updated_at, new Date().toISOString()));
  };

  const ensureWizard = async () => {
    if (state.wizardId && state.wizard) return state.wizard;
    const started = await startWizardRequest(payloads.start);
    syncWizard(started);
    return started;
  };

  const saveStep = async (stepKey: string, payload: Record<string, unknown>) => {
    const ensured = await ensureWizard();
    const startedAt = Date.now();
    state.setAutosaveState("saving");
    state.setAutosaveError("");
    recordOperationEvent("wizard.step.save.started", { stepKey }, ensured.id);
    try {
      const saved = await saveWizardStepRequest(ensured.id, stepKey, payload, { expectedRevision: ensured.wizard_revision ?? null });
      syncWizard(saved);
      recordAutosaveResult("success", Date.now() - startedAt, Array.isArray(saved.step_runs) ? saved.step_runs.length : 0, saved.id);
      recordOperationEvent("wizard.step.save.succeeded", { stepKey, currentStep: saved.current_step || null, wizardRevision: saved.wizard_revision ?? null }, saved.id);
      return saved;
    } catch (error) {
      const message = error instanceof Error ? error.message : "No se pudo guardar el paso.";
      state.setAutosaveState("error");
      state.setAutosaveError(message);
      state.setWizardError(message);
      recordAutosaveResult("error", Date.now() - startedAt, 0, ensured.id);
      recordOperationEvent("wizard.step.save.failed", { stepKey, message }, ensured.id);
      throw error;
    }
  };

  const runDryRun = async (busyLabel: string, successTitle: string, blockedTitle: string, blockedDetail: string) => {
    if (!state.wizardId) {
      setBanner({ tone: "warning", title: "Wizard incompleto", detail: "Guarda los pasos anteriores antes de correr la validación." });
      return;
    }
    setBusy(busyLabel);
    recordOperationEvent("wizard.dry_run.started", { mode: props.routeMode }, state.wizardId);
    const result = await dryRunWizardRequest(state.wizardId);
    state.setDryRunResult(result);
    if (result.wizard) syncWizard(result.wizard);
    recordOperationEvent("wizard.dry_run.completed", {
      mode: props.routeMode,
      applyReady: Boolean(result.validation_snapshot?.apply_ready || result.wizard?.validation_snapshot?.apply_ready),
      gateStatus: result.validation_snapshot?.gate?.status || result.wizard?.validation_snapshot?.gate?.status || null,
    }, result.wizard?.id || state.wizardId);
    if (isSnapshotApplyReady(result.validation_snapshot || result.wizard?.validation_snapshot || null)) {
      setBanner({ tone: "success", title: successTitle, detail: props.routeMode === "create" ? "La validación quedó fresca y el draft ya puede pasar a apply." : "La reconfiguración ya puede pasar a confirmación." });
      return;
    }
    setBanner({ tone: "warning", title: blockedTitle, detail: blockedDetail });
  };

  return { ensureWizard, runDryRun, saveStep, syncWizard };
}
