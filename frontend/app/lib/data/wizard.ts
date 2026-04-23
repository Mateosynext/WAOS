import type { VerticalProfileContract } from "../contracts/verticals";
import { apiFetch, apiFetchOrDefault } from "../api";
import { buildWizardApplyBackendPath, buildWizardBackendBasePath, buildWizardBlueprintBackendPath, buildWizardDryRunBackendPath, buildWizardStepBackendPath, WIZARD_API_PREFIX } from "./wizardEndpoints";
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

const WIZARD_START_TIMEOUT_MS = 30000;
const WIZARD_STEP_TIMEOUT_MS = 20000;
const WIZARD_EXECUTION_TIMEOUT_MS = 45000;

export async function getWizardBlueprint(request: WizardBlueprintRequest): Promise<WizardBlueprint | null> {
  return apiFetchOrDefault<WizardBlueprint | null>(buildWizardBlueprintBackendPath(request), null);
}

export async function getWizardVerticalProfile(request: WizardVerticalProfileRequest): Promise<VerticalProfileContract> {
  return getVerticalProfile(request.verticalId || undefined, request.botId || undefined, request.subvertical || undefined, request.organizationId || undefined);
}

export async function getWizardInstance(wizardId: string): Promise<WizardInstance | null> {
  return apiFetchOrDefault<WizardInstance | null>(buildWizardBackendBasePath(wizardId), null);
}

export async function startWizard(payload: Record<string, unknown>): Promise<WizardInstance> {
  return apiFetch<WizardInstance>(`${WIZARD_API_PREFIX}/start`, {
    method: "POST",
    body: JSON.stringify(payload || {}),
    timeoutMs: WIZARD_START_TIMEOUT_MS,
  });
}

export async function saveWizardStep(wizardId: string, stepKey: string, payload: Record<string, unknown>, options: { expectedRevision?: number | null } = {}): Promise<WizardInstance> {
  return apiFetch<WizardInstance>(buildWizardStepBackendPath(wizardId, stepKey), {
    method: "POST",
    body: JSON.stringify({ payload, expected_revision: options.expectedRevision ?? null }),
    timeoutMs: WIZARD_STEP_TIMEOUT_MS,
  });
}

export async function runWizardDryRun(wizardId: string): Promise<WizardDryRunResult> {
  return apiFetch<WizardDryRunResult>(buildWizardDryRunBackendPath(wizardId), {
    method: "POST",
    timeoutMs: WIZARD_EXECUTION_TIMEOUT_MS,
  });
}

export async function applyWizard(wizardId: string): Promise<WizardApplyResult> {
  return apiFetch<WizardApplyResult>(buildWizardApplyBackendPath(wizardId), {
    method: "POST",
    timeoutMs: WIZARD_EXECUTION_TIMEOUT_MS,
  });
}
