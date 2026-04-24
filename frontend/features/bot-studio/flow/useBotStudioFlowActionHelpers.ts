"use client";

import { applyWizardRequest, dryRunWizardRequest, saveWizardStepRequest, startWizardRequest } from "@/features/bot-studio/services/wizardApi";
import { normalizeWizardError, wizardErrorToMessage } from "@/features/bot-studio/services/wizardClient";
import { getCurrentWizardRevision, getValidatedWizardRevisionFromWizard, isSnapshotApplyReady } from "@/features/bot-studio/domain/wizardProgressGuards";
import { safeText } from "@/shared/lib/ui";
import type { WizardInstance } from "@/features/bot-studio/domain/wizardTypes";
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
      const wizardError = normalizeWizardError(error);
      const message = wizardErrorToMessage(wizardError);
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
      return null;
    }
    setBusy(busyLabel);
    recordOperationEvent("wizard.dry_run.started", { mode: props.routeMode }, state.wizardId);
    const result = await dryRunWizardRequest(state.wizardId);
    state.setDryRunResult(result);
    if (result.wizard) syncWizard(result.wizard);
    const validatedRevision = getCurrentWizardRevision(result.wizard) ?? getValidatedWizardRevisionFromWizard(result.wizard) ?? getCurrentWizardRevision(state.wizard);
    state.setValidatedWizardRevision(validatedRevision);
    recordOperationEvent("wizard.dry_run.completed", {
      mode: props.routeMode,
      applyReady: Boolean(result.validation_snapshot?.apply_ready || result.wizard?.validation_snapshot?.apply_ready),
      gateStatus: result.validation_snapshot?.gate?.status || result.wizard?.validation_snapshot?.gate?.status || null,
    }, result.wizard?.id || state.wizardId);
    if (isSnapshotApplyReady(result.validation_snapshot || result.wizard?.validation_snapshot || null, { wizardRevision: validatedRevision, validatedWizardRevision: validatedRevision })) {
      setBanner({ tone: "success", title: successTitle, detail: props.routeMode === "create" ? "La validación quedó fresca y el draft ya puede pasar a apply." : "La reconfiguración ya puede pasar a confirmación." });
      return result;
    }
    setBanner({ tone: "warning", title: blockedTitle, detail: blockedDetail });
    return result;
  };

  return { ensureWizard, runDryRun, saveStep, syncWizard };
}
