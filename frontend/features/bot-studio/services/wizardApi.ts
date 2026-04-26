import type { WizardApplyResult, WizardDryRunResult, WizardInstance } from "../domain/wizardTypes";
import { clampAutofixRounds, normalizeAiDescription, normalizeOptionalWizardId, normalizeRequiredWizardScope, normalizeWizardAiIntensity } from "./wizardAutopilotContract";
import { buildWizardAiAutofixPath, buildWizardApplyPath, buildWizardBasePath, buildWizardDryRunPath, buildWizardStepPath, WIZARD_AI_AUTOPILOT_PATH, WIZARD_AI_PREFILL_PATH, WIZARD_START_PATH } from "@/features/bot-studio/api/wizardEndpoints";

type WizardRequestOptions = {
  signal?: AbortSignal;
  expectedRevision?: number | null;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function extractWizardErrorMessage(payload: unknown, status: number) {
  const record = asRecord(payload);
  const details = asRecord(record.details || asRecord(record.error).details);
  const errors = Array.isArray(details.errors) ? details.errors : [];
  const first = asRecord(errors[0]);
  const loc = Array.isArray(first.loc) ? first.loc.map((item) => String(item)).join(".") : "";
  const msg = typeof first.msg === "string" ? first.msg : "";
  if (loc && msg) return `${loc}: ${msg}`;
  if (typeof record.detail === "string") return record.detail;
  if (typeof record.message === "string") return record.message;
  return `La solicitud falló (${status}).`;
}


async function requestWizardJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", credentials: "same-origin", ...init });
  const text = await response.text();
  let payload: unknown = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { detail: text || "La solicitud falló (" + response.status + ")." };
  }
  if (!response.ok) {
    throw new Error(extractWizardErrorMessage(payload, response.status));
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm: true }),
    signal: options.signal,
  });
}

export type WizardAiIntensity = "balanced" | "aggressive" | "conservative" | "savage";

export type WizardAiPrefillResult = {
  source?: string;
  intensity?: WizardAiIntensity;
  confidence?: number;
  summary?: string;
  assumptions?: string[];
  requires_user_confirmation?: string[];
  critical_fields?: string[];
  answers_patch?: Record<string, unknown>;
  generated_cards?: Array<{ key?: string; title?: string; items?: unknown[] }>;
  wizard?: Record<string, unknown> | null;
  wizard_id?: string;
  dry_run_result?: Record<string, unknown> | null;
  validation_snapshot?: Record<string, unknown> | null;
  autofix_result?: Record<string, unknown> | null;
  apply_ready?: boolean;
  next_action?: { key?: string; label?: string; detail?: string; blocking_items?: unknown[] };
  blocking_items?: unknown[];
  pipeline?: Array<{ key?: string; label?: string; status?: string }>;
  steps_saved?: string[];
  generated_at?: string;
};

export type WizardAiPrefillRequest = {
  organizationId: string;
  botId?: string | null;
  verticalId?: string | null;
  subvertical?: string | null;
  primaryObjective?: string | null;
  userDescription: string;
  intensity?: WizardAiIntensity;
  existingAnswers?: Record<string, unknown>;
};

function buildWizardAiRequestBody(request: WizardAiPrefillRequest) {
  return {
    organization_id: normalizeRequiredWizardScope(request.organizationId),
    bot_id: normalizeOptionalWizardId(request.botId),
    vertical_id: normalizeOptionalWizardId(request.verticalId),
    subvertical: normalizeOptionalWizardId(request.subvertical),
    primary_objective: normalizeOptionalWizardId(request.primaryObjective),
    user_description: normalizeAiDescription(request.userDescription),
    intensity: normalizeWizardAiIntensity(request.intensity, "balanced"),
    existing_answers: request.existingAnswers || {},
  };
}

export function generateWizardAiPrefillRequest(request: WizardAiPrefillRequest, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardAiPrefillResult>(WIZARD_AI_PREFILL_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildWizardAiRequestBody(request)),
    signal: options.signal,
  });
}

export function runWizardAiAutopilotRequest(request: WizardAiPrefillRequest & { maxAutofixRounds?: number; autoApply?: boolean }, options: WizardRequestOptions = {}) {
  return requestWizardJson<WizardAiPrefillResult>(WIZARD_AI_AUTOPILOT_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...buildWizardAiRequestBody(request),
      max_autofix_rounds: clampAutofixRounds(request.maxAutofixRounds),
      auto_apply: request.autoApply === true,
    }),
    signal: options.signal,
  });
}

export function autofixWizardWithAiRequest(wizardId: string, userDescription = "", options: WizardRequestOptions = {}) {
  return requestWizardJson<Record<string, unknown>>(buildWizardAiAutofixPath(wizardId), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_description: userDescription }),
    signal: options.signal,
  });
}
