import type { WizardInstance, WizardMode } from "./wizardTypes";

export type WizardUiActiveStep = "scope" | "basics" | "offer" | "knowledge" | "integrations" | "review" | "dry_run" | "confirm" | "simulate" | "publish";

const UI_STEPS: WizardUiActiveStep[] = ["scope", "basics", "offer", "knowledge", "integrations", "review", "dry_run", "confirm", "simulate", "publish"];
const CREATE_FLOW_STEPS: WizardUiActiveStep[] = ["scope", "basics", "offer", "knowledge", "integrations", "review", "publish"];
const BACKEND_TO_UI_STEP: Record<string, WizardUiActiveStep> = {
  vertical_fit: "scope",
  business_basics: "basics",
  catalog_offer: "offer",
  knowledge_seed: "knowledge",
  integrations_rules: "integrations",
  launch_review: "review",
  applied: "review",
};
const CREATE_AUTOSAVE_STEP_KEYS: Record<WizardUiActiveStep, string[]> = {
  scope: ["vertical_fit"],
  basics: ["vertical_fit", "business_basics"],
  offer: ["vertical_fit", "business_basics", "catalog_offer"],
  knowledge: ["vertical_fit", "business_basics", "catalog_offer", "knowledge_seed"],
  integrations: ["vertical_fit", "business_basics", "catalog_offer", "knowledge_seed", "integrations_rules"],
  review: ["vertical_fit", "business_basics", "catalog_offer", "knowledge_seed", "integrations_rules", "launch_review"],
  dry_run: ["vertical_fit", "business_basics", "catalog_offer", "knowledge_seed", "integrations_rules", "launch_review"],
  confirm: ["vertical_fit", "business_basics", "catalog_offer", "knowledge_seed", "integrations_rules", "launch_review"],
  simulate: ["vertical_fit", "business_basics", "catalog_offer", "knowledge_seed", "integrations_rules", "launch_review"],
  publish: ["vertical_fit", "business_basics", "catalog_offer", "knowledge_seed", "integrations_rules", "launch_review"],
};

function stepRank(step: WizardUiActiveStep): number {
  return UI_STEPS.indexOf(step);
}

function compareSteps(left: WizardUiActiveStep, right: WizardUiActiveStep): number {
  return stepRank(left) - stepRank(right);
}

function isCreateFlowStep(step: WizardUiActiveStep): boolean {
  return CREATE_FLOW_STEPS.includes(step);
}

function resolveBackendWizardStep(wizard?: WizardInstance | null): WizardUiActiveStep | null {
  const current = String(wizard?.current_step || "").trim().toLowerCase();
  return BACKEND_TO_UI_STEP[current] || null;
}

function clampExplicitStep(mode: WizardMode, wizard: WizardInstance | null | undefined, explicit: WizardUiActiveStep | null): WizardUiActiveStep | null {
  if (!explicit) return null;
  if (wizard?.status === "applied") return explicit;
  if (mode !== "create") return explicit;
  const backendStep = resolveBackendWizardStep(wizard);
  if (!backendStep || !isCreateFlowStep(explicit) || !isCreateFlowStep(backendStep)) return explicit;
  return compareSteps(explicit, backendStep) > 0 ? backendStep : explicit;
}

export function normalizeWizardUiStep(value: unknown): WizardUiActiveStep | null {
  const normalized = String(value || "").trim().toLowerCase();
  return UI_STEPS.includes(normalized as WizardUiActiveStep) ? (normalized as WizardUiActiveStep) : null;
}

export function resolveWizardInitialStep(mode: WizardMode, wizard?: WizardInstance | null, stepOverride?: string): WizardUiActiveStep {
  const explicit = clampExplicitStep(mode, wizard, normalizeWizardUiStep(stepOverride));
  if (explicit) return explicit;
  if (wizard?.status === "applied") return "publish";
  const backendStep = resolveBackendWizardStep(wizard);
  if (backendStep) return backendStep;
  if (mode === "reconfigure") return "review";
  return "scope";
}

export function getCreateAutosaveStepKeys(activeStep: WizardUiActiveStep): string[] {
  return [...(CREATE_AUTOSAVE_STEP_KEYS[activeStep] || CREATE_AUTOSAVE_STEP_KEYS.scope)];
}
