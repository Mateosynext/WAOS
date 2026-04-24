export type WizardPathRequest = {
  organizationId?: string | null;
  verticalId?: string | null;
  subvertical?: string | null;
  primaryObjective?: string | null;
  botId?: string | null;
};

export const CLIENT_WIZARD_API_PREFIX = "/api/onboarding/wizard";
export const SERVER_WIZARD_API_PREFIX = "/api/v1/onboarding/wizard";

function encodeSegment(value: string) {
  return encodeURIComponent(value);
}

function appendIfPresent(params: URLSearchParams, key: string, value: unknown) {
  const rendered = String(value || "").trim();
  if (rendered) params.set(key, rendered);
}

function withQuery(path: string, request: WizardPathRequest) {
  const params = new URLSearchParams();
  appendIfPresent(params, "organization_id", request.organizationId);
  appendIfPresent(params, "vertical_id", request.verticalId);
  appendIfPresent(params, "subvertical", request.subvertical);
  appendIfPresent(params, "primary_objective", request.primaryObjective);
  appendIfPresent(params, "bot_id", request.botId);
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export function buildWizardBasePath(prefix: string, wizardId: string) {
  return `${prefix}/${encodeSegment(wizardId)}`;
}

export function buildWizardStepPath(prefix: string, wizardId: string, stepKey: string) {
  return `${buildWizardBasePath(prefix, wizardId)}/steps/${encodeSegment(stepKey)}`;
}

export function buildWizardDryRunPath(prefix: string, wizardId: string) {
  return `${buildWizardBasePath(prefix, wizardId)}/dry-run`;
}

export function buildWizardApplyPath(prefix: string, wizardId: string) {
  return `${buildWizardBasePath(prefix, wizardId)}/apply`;
}

export function buildWizardBlueprintPath(prefix: string, request: WizardPathRequest) {
  return withQuery(`${prefix}/blueprint`, request);
}

export function buildWizardVerticalProfilePath(prefix: string, request: WizardPathRequest) {
  return withQuery(`${prefix}/vertical-profile`, request);
}

export function buildWizardVerticalsPath(prefix: string) {
  return `${prefix}/verticals`;
}

export const clientWizardEndpoints = {
  prefix: CLIENT_WIZARD_API_PREFIX,
  start: `${CLIENT_WIZARD_API_PREFIX}/start`,
  blueprint: (request: WizardPathRequest) => buildWizardBlueprintPath(CLIENT_WIZARD_API_PREFIX, request),
  verticalProfile: (request: WizardPathRequest) => buildWizardVerticalProfilePath(CLIENT_WIZARD_API_PREFIX, request),
  verticals: () => buildWizardVerticalsPath(CLIENT_WIZARD_API_PREFIX),
  base: (wizardId: string) => buildWizardBasePath(CLIENT_WIZARD_API_PREFIX, wizardId),
  step: (wizardId: string, stepKey: string) => buildWizardStepPath(CLIENT_WIZARD_API_PREFIX, wizardId, stepKey),
  dryRun: (wizardId: string) => buildWizardDryRunPath(CLIENT_WIZARD_API_PREFIX, wizardId),
  apply: (wizardId: string) => buildWizardApplyPath(CLIENT_WIZARD_API_PREFIX, wizardId),
};

export const serverWizardEndpoints = {
  prefix: SERVER_WIZARD_API_PREFIX,
  start: `${SERVER_WIZARD_API_PREFIX}/start`,
  blueprint: (request: WizardPathRequest) => buildWizardBlueprintPath(SERVER_WIZARD_API_PREFIX, request),
  verticalProfile: (request: WizardPathRequest) => buildWizardVerticalProfilePath(SERVER_WIZARD_API_PREFIX, request),
  verticals: () => buildWizardVerticalsPath(SERVER_WIZARD_API_PREFIX),
  base: (wizardId: string) => buildWizardBasePath(SERVER_WIZARD_API_PREFIX, wizardId),
  step: (wizardId: string, stepKey: string) => buildWizardStepPath(SERVER_WIZARD_API_PREFIX, wizardId, stepKey),
  dryRun: (wizardId: string) => buildWizardDryRunPath(SERVER_WIZARD_API_PREFIX, wizardId),
  apply: (wizardId: string) => buildWizardApplyPath(SERVER_WIZARD_API_PREFIX, wizardId),
};
