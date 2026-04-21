import type { VerticalProfileContract } from "../lib/contracts";
import { safeText } from "../lib/ui";
import type { WizardBlueprint, WizardSubverticalProfile } from "../bot-studio/wizard-types";

export type ReactiveVerticalPreviewModel = {
  subverticalProfiles: WizardSubverticalProfile[];
  subverticalOptions: string[];
  activeSubverticalProfile: WizardSubverticalProfile | null;
  previewVerticalName: string;
  previewVerticalProblem: string;
  previewSubverticalName: string;
  previewPromise: string;
  previewIntegrations: string;
  previewPlaybooks: string;
  previewTemplates: string;
  previewQuestions: string;
  previewServiceBundle: string;
  previewTone: string;
};

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

export function normalizeName(value: string) {
  return value.trim().toLowerCase();
}

function summarize(values: Array<string | null | undefined>, fallback: string, limit = 4) {
  const cleaned = unique(values).slice(0, limit);
  return cleaned.length ? cleaned.join(" · ") : fallback;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? { ...(value as Record<string, unknown>) } : {};
}

function readNestedString(value: unknown, path: string[], fallback = "") {
  let current: unknown = value;
  for (const key of path) current = asRecord(current)[key];
  const result = String(current || "").trim();
  return result || fallback;
}

export function pickSubverticalOptions(blueprint: WizardBlueprint | null, catalogVertical?: VerticalProfileContract | null) {
  return unique([
    blueprint?.selected_subvertical?.name,
    blueprint?.setup?.wizard?.selected_subvertical,
    ...(blueprint?.profile?.recommended_subverticals || []),
    ...(blueprint?.profile?.subverticals || []),
    catalogVertical?.selected_subvertical?.name,
    ...(catalogVertical?.recommended_subverticals || []),
    ...(catalogVertical?.subvertical_profiles || []).map((item) => item.name),
    ...(catalogVertical?.subverticals || []),
  ]);
}

export function buildSubverticalProfiles(verticalProfile: VerticalProfileContract | null, blueprint: WizardBlueprint | null): WizardSubverticalProfile[] {
  if (verticalProfile?.subvertical_profiles?.length) return verticalProfile.subvertical_profiles as WizardSubverticalProfile[];
  return pickSubverticalOptions(blueprint, verticalProfile).map((name) => ({
    id: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
    name,
  } as WizardSubverticalProfile));
}

export function resolveActiveSubverticalProfile(args: {
  selectedSubvertical: string;
  verticalProfile: VerticalProfileContract | null;
  blueprint: WizardBlueprint | null;
  subverticalProfiles: WizardSubverticalProfile[];
}) {
  const selected = normalizeName(args.selectedSubvertical);
  const match = (value?: string | null) => normalizeName(String(value || "")) === selected;
  if (!selected) return null;
  return args.verticalProfile?.selected_subvertical && match(args.verticalProfile.selected_subvertical.name)
    ? args.verticalProfile.selected_subvertical as WizardSubverticalProfile
    : args.subverticalProfiles.find((item) => match(item.name)) || null;
}

export function pickRecommendedIntegrations(blueprint: WizardBlueprint | null, catalogVertical?: VerticalProfileContract | null) {
  const fromBlueprint = unique((blueprint?.setup?.wizard?.recommended_integrations || []).map((item) => item.name || item.provider || item.integration_key));
  return fromBlueprint.length ? fromBlueprint : unique(catalogVertical?.recommended_integrations || []);
}

export function pickPlaybooks(blueprint: WizardBlueprint | null, catalogVertical?: VerticalProfileContract | null) {
  const fromBlueprint = unique((blueprint?.setup?.wizard?.recommended_playbooks || []).map((item) => item.label));
  return fromBlueprint.length ? fromBlueprint : unique(catalogVertical?.flows || []);
}

export function pickTemplateLabels(blueprint: WizardBlueprint | null, activeSubverticalProfile: WizardSubverticalProfile | null, activeVerticalProfile: VerticalProfileContract | null) {
  const setupTemplates = Array.isArray(asRecord(blueprint?.setup).response_templates)
    ? asRecord(blueprint?.setup).response_templates as Array<Record<string, unknown>>
    : [];
  return unique([
    ...setupTemplates.map((item) => String(item.title || item.template_key || item.key || "").trim()),
    ...(activeSubverticalProfile?.templates || []).map((item) => String(item.title || item.template_key || item.key || item.name || "").trim()),
    ...((asRecord(activeVerticalProfile?.pipeline).templates || []) as Array<Record<string, unknown>>).map((item) => String(item.title || item.template_key || item.key || item.name || "").trim()),
  ]);
}

export function isSelectedSubverticalValid(selectedSubvertical: string, subverticalOptions: string[]) {
  return Boolean(selectedSubvertical) && subverticalOptions.some((item) => normalizeName(item) === normalizeName(selectedSubvertical));
}

export function buildReactiveVerticalPreviewModel(args: {
  selectedSubvertical: string;
  verticalProfile: VerticalProfileContract | null;
  blueprint: WizardBlueprint | null;
  activeCatalogVertical: VerticalProfileContract | null;
}): ReactiveVerticalPreviewModel {
  const subverticalProfiles = buildSubverticalProfiles(args.verticalProfile, args.blueprint);
  const subverticalOptions = unique([
    ...subverticalProfiles.map((item) => item.name),
    ...pickSubverticalOptions(args.blueprint, args.verticalProfile),
  ]);
  const activeSubverticalProfile = resolveActiveSubverticalProfile({
    selectedSubvertical: args.selectedSubvertical,
    verticalProfile: args.verticalProfile,
    blueprint: args.blueprint,
    subverticalProfiles,
  });
  const previewVerticalName = safeText(args.blueprint?.profile?.name, safeText(args.verticalProfile?.name, safeText(args.activeCatalogVertical?.name, "Vertical")));
  const previewVerticalProblem = safeText(args.blueprint?.profile?.problem, safeText(args.verticalProfile?.problem, safeText(args.activeCatalogVertical?.description, "Selecciona industria y tipo de operación para ver el preview operativo.")));
  const previewSubverticalName = safeText(activeSubverticalProfile?.name, safeText(args.blueprint?.setup?.wizard?.selected_subvertical || args.selectedSubvertical, "Sin subvertical fija"));
  return {
    subverticalProfiles,
    subverticalOptions,
    activeSubverticalProfile,
    previewVerticalName,
    previewVerticalProblem,
    previewSubverticalName,
    previewPromise: safeText(activeSubverticalProfile?.promise, previewVerticalProblem),
    previewIntegrations: summarize(pickRecommendedIntegrations(args.blueprint, args.verticalProfile), "Sin integraciones sugeridas visibles"),
    previewPlaybooks: summarize(pickPlaybooks(args.blueprint, args.verticalProfile), "Sin playbooks visibles"),
    previewTemplates: summarize(pickTemplateLabels(args.blueprint, activeSubverticalProfile, args.verticalProfile), "Sin templates visibles"),
    previewQuestions: summarize(activeSubverticalProfile?.qualification_questions || [], "Sin preguntas sugeridas visibles"),
    previewServiceBundle: summarize(activeSubverticalProfile?.service_bundle || [], "Sin bundle de servicios visible"),
    previewTone: readNestedString(args.blueprint?.setup, ["personality", "tone"], safeText(args.verticalProfile?.short_name, "según defaults de industria")),
  };
}
