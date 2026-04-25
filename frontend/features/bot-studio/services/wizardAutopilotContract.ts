export const AI_DESCRIPTION_MAX_LENGTH = 4000;
export const AUTOPILOT_MIN_AUTOFIX_ROUNDS = 1;
export const AUTOPILOT_MAX_AUTOFIX_ROUNDS = 2;
export const AUTOPILOT_DEFAULT_AUTOFIX_ROUNDS = AUTOPILOT_MAX_AUTOFIX_ROUNDS;

export type WizardAiIntensity = "balanced" | "aggressive" | "conservative" | "savage";

export type NormalizedWizardAiPayload = {
  organizationId: string;
  botId: string | null;
  verticalId: string | null;
  subvertical: string | null;
  primaryObjective: string | null;
  userDescription: string;
  intensity: WizardAiIntensity;
  existingAnswers: Record<string, unknown>;
};

export type NormalizedWizardAiAutopilotPayload = NormalizedWizardAiPayload & {
  maxAutofixRounds: number;
  autoApply: boolean;
};

export function asPlainRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function textValue(value: unknown) {
  return typeof value === "string" ? value.trim() : String(value ?? "").trim();
}

function optionalTextValue(value: unknown) {
  const next = textValue(value);
  return next ? next : null;
}

function pick(body: Record<string, unknown>, snakeKey: string, camelKey: string) {
  return body[snakeKey] ?? body[camelKey];
}

export function normalizeAiDescription(value: unknown) {
  return textValue(value).slice(0, AI_DESCRIPTION_MAX_LENGTH);
}

export function clampAutofixRounds(value: unknown) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return AUTOPILOT_DEFAULT_AUTOFIX_ROUNDS;
  return Math.max(AUTOPILOT_MIN_AUTOFIX_ROUNDS, Math.min(AUTOPILOT_MAX_AUTOFIX_ROUNDS, Math.trunc(parsed)));
}

export function parseAutopilotBoolean(value: unknown) {
  if (value === true) return true;
  if (value === false) return false;
  if (typeof value === "string") return value.trim().toLowerCase() === "true";
  if (typeof value === "number") return value === 1;
  return false;
}

export function normalizeWizardAiIntensity(value: unknown, fallback: WizardAiIntensity): WizardAiIntensity {
  const candidate = textValue(value).toLowerCase();
  if (candidate === "balanced" || candidate === "aggressive" || candidate === "conservative" || candidate === "savage") {
    return candidate;
  }
  return fallback;
}

export function normalizeWizardAiProxyPayload(bodyInput: unknown, fallbackIntensity: WizardAiIntensity = "balanced"): NormalizedWizardAiPayload {
  const body = asPlainRecord(bodyInput);
  return {
    organizationId: textValue(pick(body, "organization_id", "organizationId")),
    botId: optionalTextValue(pick(body, "bot_id", "botId")),
    verticalId: optionalTextValue(pick(body, "vertical_id", "verticalId")),
    subvertical: optionalTextValue(body.subvertical),
    primaryObjective: optionalTextValue(pick(body, "primary_objective", "primaryObjective")),
    userDescription: normalizeAiDescription(pick(body, "user_description", "userDescription")),
    intensity: normalizeWizardAiIntensity(body.intensity, fallbackIntensity),
    existingAnswers: asPlainRecord(pick(body, "existing_answers", "existingAnswers")),
  };
}

export function normalizeWizardAiAutopilotProxyPayload(bodyInput: unknown): NormalizedWizardAiAutopilotPayload {
  const body = asPlainRecord(bodyInput);
  return {
    ...normalizeWizardAiProxyPayload(body, "aggressive"),
    maxAutofixRounds: clampAutofixRounds(pick(body, "max_autofix_rounds", "maxAutofixRounds")),
    autoApply: parseAutopilotBoolean(pick(body, "auto_apply", "autoApply")),
  };
}

export function hasRequiredAutopilotScope(payload: Pick<NormalizedWizardAiPayload, "organizationId">) {
  return Boolean(payload.organizationId);
}
