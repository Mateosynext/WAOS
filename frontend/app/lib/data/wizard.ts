import type { VerticalProfileContract } from "../contracts/verticals";
import { apiFetch, apiFetchOrDefault } from "../api";
import { getVerticalProfile } from "./verticals";
import type {
  WizardApplyResult,
  WizardBlueprint,
  WizardDryRunResult,
  WizardInstance,
  WizardMode,
} from "../../bot-studio/wizard-types";

export type WizardBlueprintRequest = {
  organizationId: string;
  verticalId: string;
  subvertical?: string | null;
  primaryObjective?: string | null;
  botId?: string | null;
};

export type WizardVerticalProfileRequest = {
  organizationId?: string | null;
  verticalId?: string | null;
  subvertical?: string | null;
  botId?: string | null;
  mode?: WizardMode;
};

function appendIfPresent(params: URLSearchParams, key: string, value: unknown) {
  const rendered = String(value || "").trim();
  if (rendered) params.set(key, rendered);
}

export function buildWizardBlueprintBackendPath(request: WizardBlueprintRequest) {
  const params = new URLSearchParams();
  appendIfPresent(params, "organization_id", request.organizationId);
  appendIfPresent(params, "vertical_id", request.verticalId);
  appendIfPresent(params, "subvertical", request.subvertical);
  appendIfPresent(params, "primary_objective", request.primaryObjective);
  appendIfPresent(params, "bot_id", request.botId);
  const query = params.toString();
  return `/api/v1/onboarding/wizard/blueprint${query ? `?${query}` : ""}`;
}

export async function getWizardBlueprint(request: WizardBlueprintRequest): Promise<WizardBlueprint | null> {
  return apiFetchOrDefault<WizardBlueprint | null>(buildWizardBlueprintBackendPath(request), null);
}

export async function getWizardVerticalProfile(request: WizardVerticalProfileRequest): Promise<VerticalProfileContract> {
  return getVerticalProfile(request.verticalId || undefined, request.botId || undefined, request.subvertical || undefined, request.organizationId || undefined);
}

export async function getWizardInstance(wizardId: string): Promise<WizardInstance | null> {
  return apiFetchOrDefault<WizardInstance | null>(`/api/v1/onboarding/wizard/${encodeURIComponent(wizardId)}`, null);
}

export async function startWizard(payload: Record<string, unknown>): Promise<WizardInstance> {
  return apiFetch<WizardInstance>("/api/v1/onboarding/wizard/start", {
    method: "POST",
    body: JSON.stringify(payload || {}),
  });
}

export async function saveWizardStep(wizardId: string, stepKey: string, payload: Record<string, unknown>, options: { expectedRevision?: number | null } = {}): Promise<WizardInstance> {
  return apiFetch<WizardInstance>(`/api/v1/onboarding/wizard/${encodeURIComponent(wizardId)}/steps/${encodeURIComponent(stepKey)}`, {
    method: "POST",
    body: JSON.stringify({ payload, expected_revision: options.expectedRevision ?? null }),
  });
}

export async function runWizardDryRun(wizardId: string): Promise<WizardDryRunResult> {
  return apiFetch<WizardDryRunResult>(`/api/v1/onboarding/wizard/${encodeURIComponent(wizardId)}/dry-run`, {
    method: "POST",
  });
}

export async function applyWizard(wizardId: string): Promise<WizardApplyResult> {
  return apiFetch<WizardApplyResult>(`/api/v1/onboarding/wizard/${encodeURIComponent(wizardId)}/apply`, {
    method: "POST",
  });
}
