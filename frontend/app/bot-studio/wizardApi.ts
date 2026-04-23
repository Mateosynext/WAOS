import type { WizardApplyResult, WizardDryRunResult, WizardInstance } from "./wizard-types";
import { buildWizardApplyPath, buildWizardBasePath, buildWizardDryRunPath, buildWizardStepPath, WIZARD_START_PATH } from "../../features/bot-studio/api/wizardEndpoints";

type WizardRequestOptions = {
  signal?: AbortSignal;
  expectedRevision?: number | null;
};

async function requestWizardJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", credentials: "same-origin", ...init });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof payload?.detail === "string" ? payload.detail : `La solicitud falló (${response.status}).`);
  }
  return payload as T;
}

export function getWizardRequest(wizardId: string, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardInstance>(buildWizardBasePath(wizardId), {
    method: "GET",
    signal: options.signal,
  });
}

export function startWizardRequest(payload: Record<string, unknown>, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardInstance>(WIZARD_START_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: options.signal,
  });
}

export function saveWizardStepRequest(wizardId: string, stepKey: string, payload: Record<string, unknown>, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardInstance>(buildWizardStepPath(wizardId, stepKey), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payload, expected_revision: options.expectedRevision ?? null }),
    signal: options.signal,
  });
}

export function dryRunWizardRequest(wizardId: string, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardDryRunResult>(buildWizardDryRunPath(wizardId), {
    method: "POST",
    signal: options.signal,
  });
}

export function applyWizardRequest(wizardId: string, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardApplyResult>(buildWizardApplyPath(wizardId), {
    method: "POST",
    signal: options.signal,
  });
}
