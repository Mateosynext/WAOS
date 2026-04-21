import type { WizardApplyResult, WizardDryRunResult, WizardInstance } from "./wizard-types";

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
  return requestWizardJson<WizardInstance>(`/api/onboarding/wizard/${encodeURIComponent(wizardId)}`, {
    method: "GET",
    signal: options.signal,
  });
}

export function startWizardRequest(payload: Record<string, unknown>, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardInstance>("/api/onboarding/wizard/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: options.signal,
  });
}

export function saveWizardStepRequest(wizardId: string, stepKey: string, payload: Record<string, unknown>, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardInstance>(`/api/onboarding/wizard/${encodeURIComponent(wizardId)}/steps/${stepKey}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payload, expected_revision: options.expectedRevision ?? null }),
    signal: options.signal,
  });
}

export function dryRunWizardRequest(wizardId: string, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardDryRunResult>(`/api/onboarding/wizard/${encodeURIComponent(wizardId)}/dry-run`, {
    method: "POST",
    signal: options.signal,
  });
}

export function applyWizardRequest(wizardId: string, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardApplyResult>(`/api/onboarding/wizard/${encodeURIComponent(wizardId)}/apply`, {
    method: "POST",
    signal: options.signal,
  });
}
