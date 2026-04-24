import type { SessionOrganization } from "@/shared/contracts/auth";
import type { BotContract } from "@/shared/contracts/bots";
import type { VerticalProfileContract } from "@/shared/contracts/verticals";
import type { RouteStep, CreateRouteStep } from "@/features/bot-studio/domain/flowConfig";
import type { WizardBlueprint, WizardInstance, WizardMode, WizardRecommendedIntegration, WizardRecommendedPlaybook, WizardValidationSnapshot } from "@/features/bot-studio/domain/wizardTypes";
import { getCreateRouteMessage } from "@/features/bot-studio/domain/wizardProgressGuards";
import { safeText } from "@/shared/lib/ui";

export function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? { ...(value as Record<string, unknown>) } : {};
}

export function readNestedString(value: unknown, path: string[], fallback = "") {
  let current: unknown = value;
  for (const key of path) current = asRecord(current)[key];
  const result = String(current || "").trim();
  return result || fallback;
}

export function pickBotSubvertical(bot?: BotContract | null, organization?: SessionOrganization | null) {
  const draft = asRecord(bot?.config_draft);
  return String(draft.selected_subvertical || draft.subvertical || organization?.subvertical || "").trim();
}

export function pickBotTone(bot?: BotContract | null) {
  return readNestedString(bot?.config_draft, ["personality", "tone"], safeText(bot?.tone, "amable"));
}

export function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

export function textLines(value: string) {
  return unique(String(value || "").split(/\r?\n/).map((item) => item.trim()));
}

export function readinessToneFromGate(status: string | undefined): "success" | "warning" | "danger" {
  if (String(status || "").trim().toLowerCase() === "green") return "success";
  if (String(status || "").trim().toLowerCase() === "red") return "danger";
  return "warning";
}

export function resolveMatchingVertical(verticals: VerticalProfileContract[], selectedVerticalId: string, selectedBot: BotContract | null) {
  return verticals.find((item) => item.id === selectedVerticalId)
    || verticals.find((item) => item.name.toLowerCase() === safeText(selectedBot?.vertical).trim().toLowerCase())
    || null;
}

function integrationLabel(item: WizardRecommendedIntegration) {
  return item.name || item.provider || item.integration_key || "";
}

function playbookLabel(item: WizardRecommendedPlaybook) {
  return item.label || item.key || "";
}

export type BotStudioSummaryInput = {
  routeMode: WizardMode;
  routeStep: RouteStep;
  selectedOrganization: SessionOrganization | null;
  selectedBot: BotContract | null;
  organizations: SessionOrganization[];
  verticals: VerticalProfileContract[];
  selectedVerticalId: string;
  selectedSubvertical: string;
  selectedPrimaryObjective: string;
  selectedIntegrationKeys: string[];
  selectedPlaybookKeys: string[];
  servicesText: string;
  wizard: WizardInstance | null;
  wizardId: string;
  blueprint: WizardBlueprint | null;
  snapshot: WizardValidationSnapshot | null;
  progress: number;
  businessName: string;
  botName: string;
};

export function buildBotStudioSummaryViewModel(input: BotStudioSummaryInput) {
  const organizationForSummary = input.selectedOrganization || input.organizations.find((item) => item.id === input.selectedBot?.organization_id) || null;
  const summaryIndustry = input.routeMode === "create"
    ? safeText(input.verticals.find((item) => item.id === input.selectedVerticalId)?.name, "")
    : safeText(input.selectedVerticalId ? input.verticals.find((item) => item.id === input.selectedVerticalId)?.name : input.selectedBot?.vertical, "");
  const summaryOperation = input.routeMode === "create" ? safeText(input.selectedSubvertical, "") : safeText(input.selectedSubvertical || pickBotSubvertical(input.selectedBot, organizationForSummary), "");
  const summaryObjective = input.routeMode === "create" ? safeText(input.selectedPrimaryObjective, "") : safeText(input.selectedPrimaryObjective || input.selectedBot?.objective || input.selectedBot?.goal, "");
  const summaryBusinessName = input.routeMode === "create" ? safeText(input.businessName, "") : safeText(input.businessName || input.selectedBot?.business_name, "");
  const summaryAssistantName = input.routeMode === "create" ? safeText(input.botName, "") : safeText(input.botName || input.selectedBot?.name, "");
  const recommendedChannels = unique([
    ...input.selectedIntegrationKeys,
    ...((input.blueprint?.setup?.wizard?.recommended_integrations || []).map(integrationLabel)),
  ]);
  const seededServices = unique([...(textLines(input.servicesText)), ...(input.blueprint?.setup?.services || [])]);
  const createdTemplates = unique([
    ...input.selectedPlaybookKeys,
    ...((input.blueprint?.setup?.wizard?.recommended_playbooks || []).map(playbookLabel)),
  ]);
  const summaryRisks = unique([
    ...((input.snapshot?.warnings || []).map((item) => item.label || item.detail || "")),
    ...(input.wizard?.diagnostics?.required_steps_pending || []).map((item) => getCreateRouteMessage(({
      vertical_fit: "context",
      business_basics: "identity",
      catalog_offer: "offer",
      knowledge_seed: "knowledge",
      integrations_rules: "integrations",
      launch_review: "review",
    }[item] || "review") as CreateRouteStep).title),
    !input.selectedOrganization ? "Falta organización" : "",
    !input.selectedVerticalId ? "Falta industria confirmada" : "",
    !input.selectedSubvertical ? "Falta tipo de operación" : "",
  ]);
  const readinessScore = input.snapshot?.exit_score?.value || input.wizard?.progress_percent || Math.round(input.progress);
  const readinessLabel = safeText(input.snapshot?.exit_score?.label, safeText(input.snapshot?.gate?.label, input.wizardId ? "En progreso" : "Borrador inicial"));
  const readinessTone = readinessToneFromGate(input.snapshot?.gate?.status);
  return {
    organizationName: safeText(organizationForSummary?.name, input.selectedBot?.organization_id || ""),
    industry: summaryIndustry,
    operationType: summaryOperation,
    objective: summaryObjective,
    businessName: summaryBusinessName,
    assistantName: summaryAssistantName,
    recommendedChannels,
    seededServices,
    createdTemplates,
    readinessScore,
    readinessLabel,
    readinessTone,
    risks: summaryRisks,
  };
}
