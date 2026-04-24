import type { WizardApplyResult, WizardDryRunResult, WizardInstance } from "../domain/wizardTypes";
import { clientWizardEndpoints } from "./wizardEndpoints";
import { requestWizardJson, type WizardRequestOptions } from "./wizardClient";

export function getWizardRequest(wizardId: string, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardInstance>(clientWizardEndpoints.base(wizardId), {
    method: "GET",
    signal: options.signal,
  });
}

export function startWizardRequest(payload: Record<string, unknown>, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardInstance>(clientWizardEndpoints.start, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
    signal: options.signal,
  });
}

export function saveWizardStepRequest(wizardId: string, stepKey: string, payload: Record<string, unknown>, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardInstance>(clientWizardEndpoints.step(wizardId, stepKey), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payload, expected_revision: options.expectedRevision ?? null }),
    signal: options.signal,
  });
}

export function dryRunWizardRequest(wizardId: string, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardDryRunResult>(clientWizardEndpoints.dryRun(wizardId), {
    method: "POST",
    signal: options.signal,
  });
}

export function applyWizardRequest(wizardId: string, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardApplyResult>(clientWizardEndpoints.apply(wizardId), {
    method: "POST",
    signal: options.signal,
  });
}
