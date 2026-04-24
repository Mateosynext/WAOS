import type { SessionOrganization } from "@/shared/contracts";
import { safeText } from "@/shared/lib/ui";
import type {
  WizardRecommendedIntegration,
  WizardRecommendedPlaybook,
} from "../domain/wizardTypes";

type StartPayload = {
  organization_id: string;
  bot_id?: string;
  vertical_id: string;
  subvertical: string;
  business_name: string;
  bot_name: string;
  tone: string;
  language: string;
  timezone: string;
  primary_objective: string;
  hours: string;
  whatsapp_number: string;
};

type ScopePayload = {
  vertical_id: string;
  subvertical: string;
  primary_objective: string;
};

type BasicsPayload = {
  business_name: string;
  bot_name: string;
  tone: string;
  language: string;
  timezone: string;
  hours: string;
  whatsapp_number: string;
};

type CatalogPayload = {
  services: string[];
  featured_offers: string[];
  primary_ctas: Array<{ key: string; label: string; goal: string }>;
  pricing_notes: string[];
};

type KnowledgePayload = {
  faqs: Array<{ q: string; a: string }>;
  policies: string[];
  knowledge_sources: Array<{
    connector_key: string;
    label: string;
    publish_policy: "manual_review";
    required: boolean;
  }>;
};

type IntegrationsPayload = {
  selected_integrations: Array<Partial<WizardRecommendedIntegration> | { provider: string; name: string; integration_key: string; status: string }>;
  escalate_when: string[];
  handoff_keywords: string[];
  expected_handoff_sla: string;
  human_destination_channel: string;
  rule_overrides: Record<string, unknown>;
};

type LaunchReviewPayload = {
  recommended_playbooks: Array<Partial<WizardRecommendedPlaybook> | { key: string; label: string; priority: number; goal: string }>;
  launch_notes: string[];
  autopublish_knowledge: boolean;
};

export type WizardPayloads = {
  start: StartPayload;
  scope: ScopePayload;
  basics: BasicsPayload;
  catalog: CatalogPayload;
  knowledge: KnowledgePayload;
  integrations: IntegrationsPayload;
  launchReview: LaunchReviewPayload;
};

export type BuildWizardPayloadsInput = {
  mode: "create" | "reconfigure";
  selectedOrganizationId: string;
  selectedBotId: string;
  selectedVerticalId: string;
  selectedSubvertical: string;
  selectedPrimaryObjective: string;
  selectedOrganization: SessionOrganization | null;
  businessName: string;
  botName: string;
  tone: string;
  language: string;
  timezone: string;
  hours: string;
  whatsappNumber: string;
  servicesText: string;
  featuredOffersText: string;
  pricingNotesText: string;
  primaryCtasText: string;
  faqText: string;
  policiesText: string;
  knowledgeSourcesText: string;
  selectedIntegrationKeys: string[];
  integrationOptions: WizardRecommendedIntegration[];
  escalateWhenText: string;
  handoffKeywordsText: string;
  handoffSlaText: string;
  humanDestinationChannelText: string;
  canSayText: string;
  cannotSayText: string;
  ruleOverridesText: string;
  selectedPlaybookKeys: string[];
  recommendedPlaybooks: WizardRecommendedPlaybook[];
  launchNotesText: string;
  autopublishKnowledge: boolean;
};

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function normalizeName(value: string) {
  return value.trim().toLowerCase();
}

function parseTextBlock(value: string) {
  return unique(value.split(/\r?\n/).map((item) => item.trim()));
}

function parseFaqBlock(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [question, ...rest] = line.split("|");
      return {
        q: String(question || "").trim(),
        a: rest.join("|").trim(),
      };
    })
    .filter((item) => item.q && item.a);
}

function parseJsonObject(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return {};
  try {
    const parsed = JSON.parse(trimmed);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

function integrationIdentity(item: Partial<WizardRecommendedIntegration> | string) {
  if (typeof item === "string") return item;
  return String(item.provider || item.integration_key || item.name || "").trim();
}

export function buildStartPayload(input: BuildWizardPayloadsInput): StartPayload {
  const { mode, selectedOrganizationId, selectedBotId, selectedVerticalId, selectedSubvertical, selectedOrganization, businessName, botName, tone, language, timezone, selectedPrimaryObjective, hours, whatsappNumber } = input;
  return {
    organization_id: selectedOrganizationId,
    bot_id: mode === "reconfigure" ? selectedBotId || undefined : undefined,
    vertical_id: selectedVerticalId,
    subvertical: selectedSubvertical,
    business_name: businessName || selectedOrganization?.name || "Negocio WAOS",
    bot_name: botName || (selectedOrganization?.name ? `Asistente operativo ${selectedOrganization.name}` : "Asistente operativo WAOS"),
    tone: tone || "amable",
    language: language || "es",
    timezone: timezone || selectedOrganization?.timezone || "America/Mexico_City",
    primary_objective: selectedPrimaryObjective,
    hours,
    whatsapp_number: whatsappNumber,
  };
}

export function buildScopePayload(input: BuildWizardPayloadsInput): ScopePayload {
  return {
    vertical_id: input.selectedVerticalId,
    subvertical: input.selectedSubvertical,
    primary_objective: input.selectedPrimaryObjective,
  };
}

export function buildBasicsPayload(input: BuildWizardPayloadsInput): BasicsPayload {
  const { selectedOrganization, businessName, botName, tone, language, timezone, hours, whatsappNumber } = input;
  return {
    business_name: businessName || selectedOrganization?.name || "Negocio WAOS",
    bot_name: botName || (selectedOrganization?.name ? `Asistente operativo ${selectedOrganization.name}` : "Asistente operativo WAOS"),
    tone: tone || "amable",
    language: language || "es",
    timezone: timezone || selectedOrganization?.timezone || "America/Mexico_City",
    hours,
    whatsapp_number: whatsappNumber,
  };
}

export function buildCatalogPayload(input: BuildWizardPayloadsInput): CatalogPayload {
  const ctaItems = parseTextBlock(input.primaryCtasText).map((label, index) => ({
    key: `cta_${index + 1}`,
    label,
    goal: index === 0 ? input.selectedPrimaryObjective : "support",
  }));
  return {
    services: parseTextBlock(input.servicesText),
    featured_offers: parseTextBlock(input.featuredOffersText),
    primary_ctas: ctaItems,
    pricing_notes: parseTextBlock(input.pricingNotesText),
  };
}

export function buildKnowledgePayload(input: BuildWizardPayloadsInput): KnowledgePayload {
  const sourceItems = parseTextBlock(input.knowledgeSourcesText).map((label) => ({
    connector_key: normalizeName(label).replace(/[^a-z0-9]+/g, "_"),
    label,
    publish_policy: "manual_review" as const,
    required: false,
  }));
  return {
    faqs: parseFaqBlock(input.faqText),
    policies: parseTextBlock(input.policiesText),
    knowledge_sources: sourceItems,
  };
}

export function buildIntegrationsPayload(input: BuildWizardPayloadsInput): IntegrationsPayload {
  const mergedOverrides = {
    can_say: parseTextBlock(input.canSayText),
    cannot_say: parseTextBlock(input.cannotSayText),
    ...parseJsonObject(input.ruleOverridesText),
  };
  return {
    selected_integrations: input.selectedIntegrationKeys.map((item) => {
      const matched = input.integrationOptions.find((option) => integrationIdentity(option) === item);
      return matched || { provider: item, name: item, integration_key: item, status: "planned" };
    }),
    escalate_when: parseTextBlock(input.escalateWhenText),
    handoff_keywords: parseTextBlock(input.handoffKeywordsText),
    expected_handoff_sla: input.handoffSlaText.trim() || "20 minutos",
    human_destination_channel: input.humanDestinationChannelText.trim() || "Equipo humano / operaciones",
    rule_overrides: mergedOverrides,
  };
}

export function buildLaunchReviewPayload(input: BuildWizardPayloadsInput): LaunchReviewPayload {
  return {
    recommended_playbooks: input.selectedPlaybookKeys.map((key) => {
      const matched = input.recommendedPlaybooks.find((item) => (item.key || item.label) === key);
      return matched || { key, label: key, priority: 99, goal: "launch" };
    }),
    launch_notes: parseTextBlock(input.launchNotesText),
    autopublish_knowledge: input.autopublishKnowledge,
  };
}

export function buildWizardPayloads(input: BuildWizardPayloadsInput): WizardPayloads {
  return {
    start: buildStartPayload(input),
    scope: buildScopePayload(input),
    basics: buildBasicsPayload(input),
    catalog: buildCatalogPayload(input),
    knowledge: buildKnowledgePayload(input),
    integrations: buildIntegrationsPayload(input),
    launchReview: buildLaunchReviewPayload(input),
  };
}

export function summarizeSelectedIntegrations(items: Array<Partial<WizardRecommendedIntegration> | string>) {
  return unique(items.map((item) => typeof item === "string" ? item : safeText(item.name, safeText(item.provider, safeText(item.integration_key, "custom")))));
}
