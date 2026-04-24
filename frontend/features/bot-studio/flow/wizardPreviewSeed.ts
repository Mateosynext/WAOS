import { safeText } from "@/app/lib/ui";
import type {
  BotStudioWizardState,
  DeepPartial,
  ObjectiveValue,
  WizardCatalogState,
  WizardIntegrationsState,
  WizardKnowledgeState,
} from "../context/useBotStudioWizardState";
import type { WizardBlueprint, WizardRecommendedIntegration } from "../domain/wizardTypes";
import type { BotStudioFlowProps } from "./types";

export function normalizeObjectiveValue(value: unknown, fallback: ObjectiveValue): ObjectiveValue {
  const normalized = String(value || "").trim().toLowerCase();
  return (["agendar", "vender", "calificar", "responder", "reactivar"] as ObjectiveValue[]).includes(normalized as ObjectiveValue)
    ? (normalized as ObjectiveValue)
    : fallback;
}

function normalizeSelectionParam(value: unknown) {
  const raw = String(value ?? "").trim();
  const normalized = raw.toLowerCase();
  return raw && raw !== "-" && normalized !== "null" && normalized !== "undefined" && normalized !== "nan" ? raw : "";
}

type ReactiveSelectionKeyInput = {
  organizationId?: string | null;
  verticalId?: string | null;
  subvertical?: string | null;
  primaryObjective?: string | null;
  mode: BotStudioFlowProps["routeMode"];
  botId?: string | null;
};

export function buildReactiveSelectionKey(input: ReactiveSelectionKeyInput) {
  return JSON.stringify({
    organizationId: normalizeSelectionParam(input.organizationId),
    verticalId: normalizeSelectionParam(input.verticalId),
    subvertical: normalizeSelectionParam(input.subvertical),
    primaryObjective: normalizeObjectiveValue(input.primaryObjective, "agendar"),
    mode: input.mode,
    botId: input.mode === "reconfigure" ? normalizeSelectionParam(input.botId) : "",
  });
}

function uniqueStrings(values: Array<unknown>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function textBlockFromList(values: Array<unknown>) {
  return uniqueStrings(values).join("\n");
}

function textBlockFromFaqs(items: Array<{ q?: string; a?: string }> | undefined) {
  return (items || [])
    .map((item) => {
      const q = String(item.q || "").trim();
      const a = String(item.a || "").trim();
      return q && a ? `${q} | ${a}` : "";
    })
    .filter(Boolean)
    .join("\n");
}

function readNestedStrings(value: unknown, path: string[]) {
  let current: unknown = value;
  for (const key of path) current = asRecord(current)[key];
  return uniqueStrings(Array.isArray(current) ? current : []);
}

function integrationIdentity(item: Partial<WizardRecommendedIntegration> | string) {
  if (typeof item === "string") return item;
  return safeText(item.integration_key, safeText(item.provider, safeText(item.name, "custom")));
}

function hasCatalogSeed(catalog: WizardCatalogState) {
  return Boolean(
    catalog.servicesText.trim()
      || catalog.featuredOffersText.trim()
      || catalog.primaryCtasText.trim()
      || catalog.pricingNotesText.trim(),
  );
}

function hasKnowledgeSeed(knowledge: WizardKnowledgeState) {
  return Boolean(
    knowledge.faqText.trim()
      || knowledge.policiesText.trim()
      || knowledge.knowledgeSourcesText.trim(),
  );
}

function hasIntegrationSeed(integrations: WizardIntegrationsState) {
  return Boolean(
    integrations.selectedIntegrationKeys.length
      || integrations.escalateWhenText.trim()
      || integrations.handoffKeywordsText.trim()
      || integrations.handoffSlaText.trim()
      || integrations.humanDestinationChannelText.trim()
      || integrations.canSayText.trim()
      || integrations.cannotSayText.trim()
      || integrations.ruleOverridesText.trim(),
  );
}

export function buildBlueprintSeedPatch(
  blueprint: WizardBlueprint,
  catalog: WizardCatalogState,
  knowledge: WizardKnowledgeState,
  integrations: WizardIntegrationsState,
): DeepPartial<BotStudioWizardState> {
  const setup = blueprint.setup;
  const wizard = setup?.wizard;
  const patch: DeepPartial<BotStudioWizardState> = {};

  if (!hasCatalogSeed(catalog)) {
    patch.catalog = {
      servicesText: textBlockFromList(setup?.services || []),
      featuredOffersText: textBlockFromList(wizard?.featured_offers || []),
      primaryCtasText: textBlockFromList((wizard?.recommended_ctas || []).map((item) => item.label || item.key || item.goal || "")),
      pricingNotesText: textBlockFromList(wizard?.pricing_notes || []),
    };
  }

  if (!hasKnowledgeSeed(knowledge)) {
    patch.knowledge = {
      faqText: textBlockFromFaqs(setup?.faqs),
      policiesText: textBlockFromList(wizard?.policies || []),
      knowledgeSourcesText: textBlockFromList((wizard?.knowledge_sources || []).map((item) => {
        const record = asRecord(item);
        return safeText(record.label, safeText(record.connector_key, safeText(record.provider)));
      })),
    };
  }

  if (!hasIntegrationSeed(integrations)) {
    patch.integrations = {
      selectedIntegrationKeys: uniqueStrings((wizard?.recommended_integrations || []).map(integrationIdentity)),
      escalateWhenText: textBlockFromList(readNestedStrings(setup, ["rules", "escalate_when"])),
      handoffKeywordsText: "",
      handoffSlaText: safeText(setup?.handoff?.expected_sla, "20 minutos"),
      humanDestinationChannelText: safeText(setup?.handoff?.destination_channel, "Equipo humano / operaciones"),
      canSayText: textBlockFromList(readNestedStrings(wizard?.rule_overrides, ["can_say"])),
      cannotSayText: textBlockFromList(readNestedStrings(wizard?.rule_overrides, ["cannot_say"])),
      ruleOverridesText: wizard?.rule_overrides ? JSON.stringify(wizard.rule_overrides, null, 2) : "{}",
    };
  }

  return patch;
}

export function hasBlueprintSeedPatch(patch: DeepPartial<BotStudioWizardState>) {
  return Boolean(patch.catalog || patch.knowledge || patch.integrations);
}
