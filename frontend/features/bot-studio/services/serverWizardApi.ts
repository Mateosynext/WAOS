import type { VerticalProfileContract } from "@/shared/contracts/verticals";
import { apiFetch, apiFetchOrDefault } from "@/shared/server/api";
import { getVerticalProfile } from "@/shared/server/verticals";
import type { WizardApplyResult, WizardBlueprint, WizardDryRunResult, WizardInstance, WizardMode } from "../domain/wizardTypes";
import { serverWizardEndpoints, type WizardPathRequest } from "./wizardEndpoints";

export type WizardBlueprintRequest = Required<Pick<WizardPathRequest, "organizationId" | "verticalId">> & Omit<WizardPathRequest, "organizationId" | "verticalId">;
export type WizardVerticalProfileRequest = WizardPathRequest & { mode?: WizardMode };

const WIZARD_START_TIMEOUT_MS = 30000;
const WIZARD_STEP_TIMEOUT_MS = 20000;
const WIZARD_EXECUTION_TIMEOUT_MS = 45000;

export async function getWizardBlueprint(request: WizardBlueprintRequest): Promise<WizardBlueprint | null> {
  return apiFetchOrDefault<WizardBlueprint | null>(serverWizardEndpoints.blueprint(request), null);
}

export async function getWizardVerticalProfile(request: WizardVerticalProfileRequest): Promise<VerticalProfileContract> {
  return getVerticalProfile(request.verticalId || undefined, request.botId || undefined, request.subvertical || undefined, request.organizationId || undefined);
}

export async function getWizardInstance(wizardId: string): Promise<WizardInstance | null> {
  return apiFetchOrDefault<WizardInstance | null>(serverWizardEndpoints.base(wizardId), null);
}

export async function startWizard(payload: Record<string, unknown>): Promise<WizardInstance> {
  return apiFetch<WizardInstance>(serverWizardEndpoints.start, {
    method: "POST",
    body: JSON.stringify(payload || {}),
    timeoutMs: WIZARD_START_TIMEOUT_MS,
  });
}

export async function saveWizardStep(wizardId: string, stepKey: string, payload: Record<string, unknown>, options: { expectedRevision?: number | null } = {}): Promise<WizardInstance> {
  return apiFetch<WizardInstance>(serverWizardEndpoints.step(wizardId, stepKey), {
    method: "POST",
    body: JSON.stringify({ payload, expected_revision: options.expectedRevision ?? null }),
    timeoutMs: WIZARD_STEP_TIMEOUT_MS,
  });
}

export async function runWizardDryRun(wizardId: string): Promise<WizardDryRunResult> {
  return apiFetch<WizardDryRunResult>(serverWizardEndpoints.dryRun(wizardId), {
    method: "POST",
    timeoutMs: WIZARD_EXECUTION_TIMEOUT_MS,
  });
}

export async function applyWizard(wizardId: string): Promise<WizardApplyResult> {
  return apiFetch<WizardApplyResult>(serverWizardEndpoints.apply(wizardId), {
    method: "POST",
    timeoutMs: WIZARD_EXECUTION_TIMEOUT_MS,
  });
}
