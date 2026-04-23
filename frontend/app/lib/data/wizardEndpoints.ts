export type WizardBlueprintPathRequest = {
  organizationId: string;
  verticalId: string;
  subvertical?: string | null;
  primaryObjective?: string | null;
  botId?: string | null;
};

export const WIZARD_API_PREFIX = "/api/v1/onboarding/wizard";

function appendIfPresent(params: URLSearchParams, key: string, value: unknown) {
  const rendered = String(value || "").trim();
  if (rendered) params.set(key, rendered);
}

export function buildWizardBackendBasePath(wizardId: string) {
  return `${WIZARD_API_PREFIX}/${encodeURIComponent(wizardId)}`;
}

export function buildWizardStepBackendPath(wizardId: string, stepKey: string) {
  return `${buildWizardBackendBasePath(wizardId)}/steps/${encodeURIComponent(stepKey)}`;
}

export function buildWizardDryRunBackendPath(wizardId: string) {
  return `${buildWizardBackendBasePath(wizardId)}/dry-run`;
}

export function buildWizardApplyBackendPath(wizardId: string) {
  return `${buildWizardBackendBasePath(wizardId)}/apply`;
}

export function buildWizardBlueprintBackendPath(request: WizardBlueprintPathRequest) {
  const params = new URLSearchParams();
  appendIfPresent(params, "organization_id", request.organizationId);
  appendIfPresent(params, "vertical_id", request.verticalId);
  appendIfPresent(params, "subvertical", request.subvertical);
  appendIfPresent(params, "primary_objective", request.primaryObjective);
  appendIfPresent(params, "bot_id", request.botId);
  const query = params.toString();
  return `${WIZARD_API_PREFIX}/blueprint${query ? `?${query}` : ""}`;
}
