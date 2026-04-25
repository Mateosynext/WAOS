import type { DeepPartial, BotStudioWizardState, ObjectiveValue } from "../context/useBotStudioWizardState";
import type { WizardAiPrefillResult } from "../services/wizardApi";

const OBJECTIVES = new Set(["agendar", "vender", "calificar", "responder", "reactivar"]);

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function text(value: unknown, fallback = "") {
  const rendered = String(value || "").trim();
  return rendered || fallback;
}

function unique(values: unknown[]) {
  const seen = new Set<string>();
  const result: string[] = [];
  values.forEach((value) => {
    const item = text(value);
    if (!item || seen.has(item.toLowerCase())) return;
    seen.add(item.toLowerCase());
    result.push(item);
  });
  return result;
}

function textBlock(values: unknown[]) {
  return unique(values).join("\n");
}

function faqBlock(values: unknown[]) {
  return values
    .map((item) => {
      const record = asRecord(item);
      const q = text(record.q || record.question || record.label);
      const a = text(record.a || record.answer || record.response);
      return q && a ? `${q} | ${a}` : "";
    })
    .filter(Boolean)
    .join("\n");
}

function ctaLabel(item: unknown) {
  if (typeof item === "string") return item;
  const record = asRecord(item);
  return text(record.label || record.name || record.key || record.goal);
}

function sourceLabel(item: unknown) {
  if (typeof item === "string") return item;
  const record = asRecord(item);
  return text(record.label || record.connector_key || record.provider || record.name);
}

function integrationKey(item: unknown) {
  if (typeof item === "string") return item;
  const record = asRecord(item);
  return text(record.integration_key || record.provider || record.name || record.connector_key);
}

function playbookKey(item: unknown) {
  if (typeof item === "string") return item;
  const record = asRecord(item);
  return text(record.key || record.label || record.name);
}

function objective(value: unknown): ObjectiveValue {
  const candidate = text(value).toLowerCase();
  return OBJECTIVES.has(candidate) ? candidate as ObjectiveValue : "agendar";
}

export function buildStatePatchFromAiPrefill(result: WizardAiPrefillResult): DeepPartial<BotStudioWizardState> {
  const answers = asRecord(result.answers_patch);
  const fit = asRecord(answers.vertical_fit);
  const basics = asRecord(answers.business_basics);
  const catalog = asRecord(answers.catalog_offer);
  const knowledge = asRecord(answers.knowledge_seed);
  const integrations = asRecord(answers.integrations_rules);
  const launch = asRecord(answers.launch_review);
  const rules = asRecord(integrations.rule_overrides);

  return {
    scope: {
      selectedVerticalId: text(fit.vertical_id),
      candidateVerticalId: text(fit.vertical_id),
      selectedSubvertical: text(fit.subvertical),
      candidateSubvertical: text(fit.subvertical),
      selectedPrimaryObjective: objective(fit.primary_objective),
    },
    basics: {
      businessName: text(basics.business_name),
      botName: text(basics.bot_name),
      tone: text(basics.tone),
      language: text(basics.language, "es"),
      timezone: text(basics.timezone, "America/Mexico_City"),
      hours: text(basics.hours),
      whatsappNumber: text(basics.whatsapp_number),
    },
    catalog: {
      servicesText: textBlock(asArray(catalog.services)),
      featuredOffersText: textBlock(asArray(catalog.featured_offers)),
      primaryCtasText: textBlock(asArray(catalog.primary_ctas).map(ctaLabel)),
      pricingNotesText: textBlock(asArray(catalog.pricing_notes)),
    },
    knowledge: {
      faqText: faqBlock(asArray(knowledge.faqs)),
      policiesText: textBlock(asArray(knowledge.policies)),
      knowledgeSourcesText: textBlock(asArray(knowledge.knowledge_sources).map(sourceLabel)),
    },
    integrations: {
      selectedIntegrationKeys: unique(asArray(integrations.selected_integrations).map(integrationKey)),
      escalateWhenText: textBlock(asArray(integrations.escalate_when)),
      handoffKeywordsText: textBlock(asArray(integrations.handoff_keywords)),
      handoffSlaText: text(integrations.expected_handoff_sla),
      humanDestinationChannelText: text(integrations.human_destination_channel),
      canSayText: textBlock(asArray(rules.can_say)),
      cannotSayText: textBlock(asArray(rules.cannot_say)),
      ruleOverridesText: JSON.stringify(rules, null, 2),
    },
    launch: {
      launchNotesText: textBlock(asArray(launch.launch_notes)),
      selectedPlaybookKeys: unique(asArray(launch.recommended_playbooks).map(playbookKey)),
      autopublishKnowledge: launch.autopublish_knowledge !== false,
    },
    wizardRuntime: {
      dryRunResult: null,
      applyResult: null,
      reviewConfirmed: false,
      validatedWizardRevision: null,
    },
  };
}
