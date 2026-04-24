import { useReducer, type Dispatch, type SetStateAction } from "react";
import { safeText } from "@/shared/lib/ui";
import type { BotContract, ReleaseRequestContract } from "@/shared/contracts/bots";
import type { VerticalProfileContract } from "@/shared/contracts/verticals";
import type {
  WizardApplyResult,
  WizardBlueprint,
  WizardDryRunResult,
  WizardInstance,
  WizardMode,
  WizardRecommendedIntegration,
} from "@/features/bot-studio/domain/wizardTypes";
import { resolveWizardInitialStep, type WizardUiActiveStep as ActiveStep } from "@/features/bot-studio/domain/wizardStepFlow";
import { getValidatedWizardRevisionFromWizard } from "@/features/bot-studio/domain/wizardProgressGuards";

export type ObjectiveValue = "agendar" | "vender" | "calificar" | "responder" | "reactivar";
export type CompletionPath = "wizard" | "module";
export type AutosaveState = "idle" | "saving" | "saved" | "error";

const OBJECTIVES: ObjectiveValue[] = ["agendar", "vender", "calificar", "responder", "reactivar"];

export type WizardScopeState = {
  mode: WizardMode;
  selectedBotId: string;
  selectedOrganizationId: string;
  selectedVerticalId: string;
  selectedSubvertical: string;
  candidateVerticalId: string;
  candidateSubvertical: string;
  selectedPrimaryObjective: ObjectiveValue;
  activeStep: ActiveStep;
};

export type WizardBasicsState = {
  businessName: string;
  botName: string;
  tone: string;
  language: string;
  timezone: string;
  hours: string;
  whatsappNumber: string;
};

export type WizardCatalogState = {
  servicesText: string;
  featuredOffersText: string;
  primaryCtasText: string;
  pricingNotesText: string;
};

export type WizardKnowledgeState = {
  faqText: string;
  policiesText: string;
  knowledgeSourcesText: string;
};

export type WizardIntegrationsState = {
  selectedIntegrationKeys: string[];
  escalateWhenText: string;
  handoffKeywordsText: string;
  handoffSlaText: string;
  humanDestinationChannelText: string;
  canSayText: string;
  cannotSayText: string;
  ruleOverridesText: string;
};

export type WizardLaunchState = {
  launchNotesText: string;
  selectedPlaybookKeys: string[];
  autopublishKnowledge: boolean;
};

export type WizardSimulationState = {
  simulationTitle: string;
  simulationScenario: string;
  simulationExpectedAction: string;
  simulationResult: Record<string, unknown> | null;
  simulationRunning: boolean;
  simulationError: string;
};

export type WizardPreviewState = {
  blueprint: WizardBlueprint | null;
  verticalProfile: VerticalProfileContract | null;
  previewLoading: boolean;
  previewError: string;
};

export type WizardRuntimeState = {
  wizardId: string;
  wizard: WizardInstance | null;
  working: boolean;
  wizardError: string;
  applyResult: WizardApplyResult | null;
  dryRunResult: WizardDryRunResult | null;
  reviewConfirmed: boolean;
  validatedWizardRevision: number | null;
};

export type WizardPostApplyState = {
  postApplyBot: BotContract | null;
  postApplyReleases: ReleaseRequestContract[];
  postApplySimulationRuns: Array<Record<string, unknown>>;
  postApplyLoading: boolean;
  postApplyError: string;
  postApplyPath: CompletionPath;
};

export type WizardAutosaveStateSlice = {
  autosaveState: AutosaveState;
  autosaveError: string;
  lastSavedAt: string;
};

export type BotStudioWizardState = {
  scope: WizardScopeState;
  basics: WizardBasicsState;
  catalog: WizardCatalogState;
  knowledge: WizardKnowledgeState;
  integrations: WizardIntegrationsState;
  launch: WizardLaunchState;
  simulation: WizardSimulationState;
  preview: WizardPreviewState;
  wizardRuntime: WizardRuntimeState;
  postApply: WizardPostApplyState;
  autosave: WizardAutosaveStateSlice;
};

export type StateDomainKey = keyof BotStudioWizardState;
export type DeepPartial<T> = { [K in keyof T]?: T[K] extends Array<unknown> ? T[K] : T[K] extends object ? DeepPartial<T[K]> : T[K] };
export type WizardSetter<T> = (next: SetStateAction<T>) => void;

type SetFieldAction = {
  type: "setField";
  domain: StateDomainKey;
  field: string;
  value: unknown;
};

type PatchAction = {
  type: "patch";
  patch: DeepPartial<BotStudioWizardState>;
};

type Action = SetFieldAction | PatchAction;

const VALIDATION_DIRTY_FIELDS: Partial<Record<StateDomainKey, Set<string>>> = {
  scope: new Set([
    "selectedBotId",
    "selectedOrganizationId",
    "selectedVerticalId",
    "selectedSubvertical",
    "selectedPrimaryObjective",
  ]),
  basics: new Set(["businessName", "botName", "tone", "language", "timezone", "hours", "whatsappNumber"]),
  catalog: new Set(["servicesText", "featuredOffersText", "primaryCtasText", "pricingNotesText"]),
  knowledge: new Set(["faqText", "policiesText", "knowledgeSourcesText"]),
  integrations: new Set([
    "selectedIntegrationKeys",
    "escalateWhenText",
    "handoffKeywordsText",
    "handoffSlaText",
    "humanDestinationChannelText",
    "canSayText",
    "cannotSayText",
    "ruleOverridesText",
  ]),
  launch: new Set(["launchNotesText", "selectedPlaybookKeys", "autopublishKnowledge"]),
};

export type UseBotStudioWizardStateParams = {
  initialSelectedBotId: string;
  initialMode: WizardMode;
  initialOrganizationId: string;
  initialVerticalId: string;
  initialSubvertical: string;
  initialPrimaryObjective: string;
  initialBlueprint: WizardBlueprint | null;
  initialVerticalProfile: VerticalProfileContract | null;
  initialWizardId?: string;
  initialWizard?: WizardInstance | null;
  initialStepOverride?: string;
};

export type WizardScopeActions = {
  setMode: WizardSetter<WizardScopeState["mode"]>;
  setSelectedBotId: WizardSetter<string>;
  setSelectedOrganizationId: WizardSetter<string>;
  setSelectedVerticalId: WizardSetter<string>;
  setSelectedSubvertical: WizardSetter<string>;
  setCandidateVerticalId: WizardSetter<string>;
  setCandidateSubvertical: WizardSetter<string>;
  setSelectedPrimaryObjective: WizardSetter<ObjectiveValue>;
  setActiveStep: WizardSetter<ActiveStep>;
};

export type WizardBasicsActions = {
  setBusinessName: WizardSetter<string>;
  setBotName: WizardSetter<string>;
  setTone: WizardSetter<string>;
  setLanguage: WizardSetter<string>;
  setTimezone: WizardSetter<string>;
  setHours: WizardSetter<string>;
  setWhatsappNumber: WizardSetter<string>;
};

export type WizardCatalogActions = {
  setServicesText: WizardSetter<string>;
  setFeaturedOffersText: WizardSetter<string>;
  setPrimaryCtasText: WizardSetter<string>;
  setPricingNotesText: WizardSetter<string>;
};

export type WizardKnowledgeActions = {
  setFaqText: WizardSetter<string>;
  setPoliciesText: WizardSetter<string>;
  setKnowledgeSourcesText: WizardSetter<string>;
};

export type WizardIntegrationsActions = {
  setSelectedIntegrationKeys: WizardSetter<string[]>;
  setEscalateWhenText: WizardSetter<string>;
  setHandoffKeywordsText: WizardSetter<string>;
  setHandoffSlaText: WizardSetter<string>;
  setHumanDestinationChannelText: WizardSetter<string>;
  setCanSayText: WizardSetter<string>;
  setCannotSayText: WizardSetter<string>;
  setRuleOverridesText: WizardSetter<string>;
};

export type WizardLaunchActions = {
  setLaunchNotesText: WizardSetter<string>;
  setSelectedPlaybookKeys: WizardSetter<string[]>;
  setAutopublishKnowledge: WizardSetter<boolean>;
};

export type WizardSimulationActions = {
  setSimulationTitle: WizardSetter<string>;
  setSimulationScenario: WizardSetter<string>;
  setSimulationExpectedAction: WizardSetter<string>;
  setSimulationResult: WizardSetter<Record<string, unknown> | null>;
  setSimulationRunning: WizardSetter<boolean>;
  setSimulationError: WizardSetter<string>;
};

export type WizardPreviewActions = {
  setBlueprint: WizardSetter<WizardBlueprint | null>;
  setVerticalProfile: WizardSetter<VerticalProfileContract | null>;
  setPreviewLoading: WizardSetter<boolean>;
  setPreviewError: WizardSetter<string>;
};

export type WizardRuntimeActions = {
  setWizardId: WizardSetter<string>;
  setWizard: WizardSetter<WizardInstance | null>;
  setWorking: WizardSetter<boolean>;
  setWizardError: WizardSetter<string>;
  setApplyResult: WizardSetter<WizardApplyResult | null>;
  setDryRunResult: WizardSetter<WizardDryRunResult | null>;
  setReviewConfirmed: WizardSetter<boolean>;
  setValidatedWizardRevision: WizardSetter<number | null>;
};

export type WizardPostApplyActions = {
  setPostApplyBot: WizardSetter<BotContract | null>;
  setPostApplyReleases: WizardSetter<ReleaseRequestContract[]>;
  setPostApplySimulationRuns: WizardSetter<Array<Record<string, unknown>>>;
  setPostApplyLoading: WizardSetter<boolean>;
  setPostApplyError: WizardSetter<string>;
  setPostApplyPath: WizardSetter<CompletionPath>;
};

export type WizardAutosaveActions = {
  setAutosaveState: WizardSetter<AutosaveState>;
  setAutosaveError: WizardSetter<string>;
  setLastSavedAt: WizardSetter<string>;
};

export type BotStudioWizardActions = {
  scope: WizardScopeActions;
  basics: WizardBasicsActions;
  catalog: WizardCatalogActions;
  knowledge: WizardKnowledgeActions;
  integrations: WizardIntegrationsActions;
  launch: WizardLaunchActions;
  simulation: WizardSimulationActions;
  preview: WizardPreviewActions;
  wizardRuntime: WizardRuntimeActions;
  postApply: WizardPostApplyActions;
  autosave: WizardAutosaveActions;
};

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? { ...(value as Record<string, unknown>) } : {};
}

function normalizeObjective(value: unknown): ObjectiveValue {
  const normalized = String(value || "").trim().toLowerCase();
  return OBJECTIVES.includes(normalized as ObjectiveValue) ? (normalized as ObjectiveValue) : "agendar";
}

function readNestedStrings(value: unknown, path: string[]) {
  let current: unknown = value;
  for (const key of path) current = asRecord(current)[key];
  return unique(Array.isArray(current) ? current.map((item) => String(item || "").trim()) : []);
}

function readFaqItems(value: unknown): Array<{ q: string; a: string }> {
  return Array.isArray(value)
    ? value
        .map((item) => {
          const record = asRecord(item);
          return {
            q: String(record.q || "").trim(),
            a: String(record.a || "").trim(),
          };
        })
        .filter((item) => item.q && item.a)
    : [];
}

function textBlockFromList(values: Array<string | null | undefined>) {
  return unique(values).join("\n");
}

function textBlockFromFaqs(items: Array<{ q?: string; a?: string }>) {
  return items
    .map((item) => {
      const q = String(item.q || "").trim();
      const a = String(item.a || "").trim();
      return q && a ? `Q: ${q}\nA: ${a}` : "";
    })
    .filter(Boolean)
    .join("\n\n");
}

function parseJsonObject(value: string) {
  const raw = value.trim();
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed as Record<string, unknown> : {};
  } catch {
    return {};
  }
}

function integrationIdentity(item: Partial<WizardRecommendedIntegration> | string) {
  if (typeof item === "string") return item;
  return safeText(item.integration_key, safeText(item.provider, safeText(item.name, "custom")));
}

function mergeState(state: BotStudioWizardState, patch: DeepPartial<BotStudioWizardState>): BotStudioWizardState {
  const nextState = { ...state } as BotStudioWizardState;
  for (const domain of Object.keys(patch) as StateDomainKey[]) {
    nextState[domain] = {
      ...state[domain],
      ...(patch[domain] || {}),
    } as never;
  }
  return nextState;
}

function serializedEquality(left: unknown, right: unknown): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

function hasValidatedRuntime(state: BotStudioWizardState): boolean {
  return Boolean(state.wizardRuntime.dryRunResult || state.wizardRuntime.validatedWizardRevision !== null);
}

function shouldInvalidateValidationForField(state: BotStudioWizardState, domain: StateDomainKey, field: string, value: unknown): boolean {
  if (!hasValidatedRuntime(state)) return false;
  if (!VALIDATION_DIRTY_FIELDS[domain]?.has(field)) return false;
  return !serializedEquality((state[domain] as Record<string, unknown>)[field], value);
}

function shouldInvalidateValidationForPatch(state: BotStudioWizardState, patch: DeepPartial<BotStudioWizardState>): boolean {
  if (!hasValidatedRuntime(state)) return false;
  for (const domain of Object.keys(patch) as StateDomainKey[]) {
    const dirtyFields = VALIDATION_DIRTY_FIELDS[domain];
    if (!dirtyFields) continue;
    const domainPatch = patch[domain] as Record<string, unknown> | undefined;
    if (!domainPatch) continue;
    for (const field of Object.keys(domainPatch)) {
      if (!dirtyFields.has(field)) continue;
      if (!serializedEquality((state[domain] as Record<string, unknown>)[field], domainPatch[field])) return true;
    }
  }
  return false;
}

function invalidateValidation(state: BotStudioWizardState): BotStudioWizardState {
  if (!hasValidatedRuntime(state)) return state;
  return {
    ...state,
    wizardRuntime: {
      ...state.wizardRuntime,
      dryRunResult: null,
      applyResult: null,
      reviewConfirmed: false,
      validatedWizardRevision: null,
    },
  };
}

function reducer(state: BotStudioWizardState, action: Action): BotStudioWizardState {
  switch (action.type) {
    case "setField": {
      const baseState = {
        ...state,
        [action.domain]: {
          ...state[action.domain],
          [action.field]: action.value,
        },
      } as BotStudioWizardState;
      return shouldInvalidateValidationForField(state, action.domain, action.field, action.value) ? invalidateValidation(baseState) : baseState;
    }
    case "patch": {
      const baseState = mergeState(state, action.patch);
      return shouldInvalidateValidationForPatch(state, action.patch) ? invalidateValidation(baseState) : baseState;
    }
    default:
      return state;
  }
}

function createInitialState(params: UseBotStudioWizardStateParams): BotStudioWizardState {
  const {
    initialSelectedBotId,
    initialMode,
    initialOrganizationId,
    initialVerticalId,
    initialSubvertical,
    initialPrimaryObjective,
    initialBlueprint,
    initialVerticalProfile,
    initialWizardId,
    initialWizard,
    initialStepOverride,
  } = params;

  const wizardAnswers = initialWizard?.answers || {};
  const initialWizardBasics = asRecord(wizardAnswers.business_basics);
  const initialWizardFit = asRecord(wizardAnswers.vertical_fit);
  const initialCatalog = asRecord(wizardAnswers.catalog_offer);
  const initialKnowledge = asRecord(wizardAnswers.knowledge_seed);
  const initialIntegrations = asRecord(wizardAnswers.integrations_rules);
  const initialLaunch = asRecord(wizardAnswers.launch_review);

  const initialConfirmedVerticalId = String(initialWizardFit.vertical_id || initialWizard?.vertical_id || "");
  const initialConfirmedSubvertical = String(initialWizardFit.subvertical || initialWizard?.subvertical || "");
  const initialCandidateVerticalId = String(initialConfirmedVerticalId || initialVerticalId || "");
  const initialCandidateSubvertical = String(initialConfirmedSubvertical || initialSubvertical || "");

  return {
    scope: {
      mode: initialMode,
      selectedBotId: initialSelectedBotId || String(initialWizard?.bot_id || ""),
      selectedOrganizationId: String(initialWizard?.organization_id || initialOrganizationId || ""),
      selectedVerticalId: initialConfirmedVerticalId,
      selectedSubvertical: initialConfirmedSubvertical,
      candidateVerticalId: initialCandidateVerticalId,
      candidateSubvertical: initialCandidateSubvertical,
      selectedPrimaryObjective: normalizeObjective(initialWizardFit.primary_objective || initialPrimaryObjective),
      activeStep: resolveWizardInitialStep(initialMode, initialWizard || null, initialStepOverride),
    },
    basics: {
      businessName: String(initialWizardBasics.business_name || initialWizard?.business_name || ""),
      botName: String(initialWizardBasics.bot_name || initialWizard?.bot_name || ""),
      tone: String(initialWizardBasics.tone || initialWizard?.tone || "amable"),
      language: String(initialWizardBasics.language || initialWizard?.language || "es"),
      timezone: String(initialWizardBasics.timezone || initialWizard?.timezone || "America/Mexico_City"),
      hours: String(initialWizardBasics.hours || ""),
      whatsappNumber: String(initialWizardBasics.whatsapp_number || ""),
    },
    catalog: {
      servicesText: textBlockFromList(Array.isArray(initialCatalog.services) ? initialCatalog.services.map((item) => String(item || "")) : initialBlueprint?.setup?.services || []),
      featuredOffersText: textBlockFromList(Array.isArray(initialCatalog.featured_offers) ? initialCatalog.featured_offers.map((item) => String(item || "")) : initialBlueprint?.setup?.wizard?.featured_offers || []),
      primaryCtasText: textBlockFromList(Array.isArray(initialCatalog.primary_ctas)
        ? initialCatalog.primary_ctas.map((item) => safeText(asRecord(item).label, String(item || "")))
        : (initialBlueprint?.setup?.wizard?.recommended_ctas || []).map((item) => item.label || item.key || item.goal || "")),
      pricingNotesText: textBlockFromList(Array.isArray(initialCatalog.pricing_notes) ? initialCatalog.pricing_notes.map((item) => String(item || "")) : initialBlueprint?.setup?.wizard?.pricing_notes || []),
    },
    knowledge: {
      faqText: textBlockFromFaqs(readFaqItems(initialKnowledge.faqs || initialBlueprint?.setup?.faqs || [])),
      policiesText: textBlockFromList(Array.isArray(initialKnowledge.policies) ? initialKnowledge.policies.map((item) => String(item || "")) : initialBlueprint?.setup?.wizard?.policies || []),
      knowledgeSourcesText: textBlockFromList(Array.isArray(initialKnowledge.knowledge_sources)
        ? initialKnowledge.knowledge_sources.map((item) => safeText(asRecord(item).label, safeText(asRecord(item).connector_key, String(item || ""))))
        : (initialBlueprint?.setup?.wizard?.knowledge_sources || []).map((item) => safeText(item.label, safeText(item.connector_key, safeText(item.provider))))),
    },
    integrations: {
      selectedIntegrationKeys: unique(Array.isArray(initialIntegrations.selected_integrations)
        ? initialIntegrations.selected_integrations.map((item) => integrationIdentity(item as Partial<WizardRecommendedIntegration>))
        : (initialBlueprint?.setup?.wizard?.recommended_integrations || []).map(integrationIdentity)),
      escalateWhenText: textBlockFromList(Array.isArray(initialIntegrations.escalate_when) ? initialIntegrations.escalate_when.map((item) => String(item || "")) : readNestedStrings(initialBlueprint?.setup, ["rules", "escalate_when"])),
      handoffKeywordsText: textBlockFromList(Array.isArray(initialIntegrations.handoff_keywords) ? initialIntegrations.handoff_keywords.map((item) => String(item || "")) : []),
      handoffSlaText: String(initialIntegrations.expected_handoff_sla || safeText(initialBlueprint?.setup?.handoff?.expected_sla, "20 minutos")),
      humanDestinationChannelText: String(initialIntegrations.human_destination_channel || safeText(initialBlueprint?.setup?.handoff?.destination_channel, "Equipo humano / operaciones")),
      canSayText: textBlockFromList(readNestedStrings(initialIntegrations, ["rule_overrides", "can_say"])),
      cannotSayText: textBlockFromList(readNestedStrings(initialIntegrations, ["rule_overrides", "cannot_say"])),
      ruleOverridesText: JSON.stringify(parseJsonObject(String(initialIntegrations.rule_overrides ? JSON.stringify(initialIntegrations.rule_overrides) : "")), null, 2),
    },
    launch: {
      launchNotesText: textBlockFromList(Array.isArray(initialLaunch.launch_notes)
        ? initialLaunch.launch_notes.map((item) => String(item || ""))
        : initialBlueprint?.setup?.wizard?.launch_notes || []),
      selectedPlaybookKeys: unique(
        Array.isArray(initialLaunch.recommended_playbooks)
          ? initialLaunch.recommended_playbooks.map((item) => safeText(asRecord(item).key, safeText(asRecord(item).label, String(item || ""))))
          : (initialBlueprint?.setup?.wizard?.recommended_playbooks || []).map((item) => item.key || item.label || ""),
      ),
      autopublishKnowledge: Boolean(initialLaunch.autopublish_knowledge ?? initialBlueprint?.setup?.wizard?.autopublish_knowledge ?? true),
    },
    simulation: {
      simulationTitle: "Validación guiada del wizard",
      simulationScenario: "Hola, quiero precio y también saber si pueden agendarme esta semana.",
      simulationExpectedAction: "",
      simulationResult: null,
      simulationRunning: false,
      simulationError: "",
    },
    preview: {
      blueprint: initialBlueprint,
      verticalProfile: initialVerticalProfile,
      previewLoading: false,
      previewError: "",
    },
    wizardRuntime: {
      wizardId: initialWizardId || initialWizard?.id || "",
      wizard: initialWizard || null,
      working: false,
      wizardError: "",
      applyResult: null,
      dryRunResult: null,
      reviewConfirmed: false,
      validatedWizardRevision: getValidatedWizardRevisionFromWizard(initialWizard),
    },
    postApply: {
      postApplyBot: null,
      postApplyReleases: [],
      postApplySimulationRuns: [],
      postApplyLoading: false,
      postApplyError: "",
      postApplyPath: "wizard",
    },
    autosave: {
      autosaveState: initialWizardId || initialWizard?.id ? "saved" : "idle",
      autosaveError: "",
      lastSavedAt: String(initialWizard?.updated_at || ""),
    },
  };
}

function buildActions(state: BotStudioWizardState, dispatch: Dispatch<Action>): BotStudioWizardActions {
  const createFieldSetter = <D extends StateDomainKey, F extends keyof BotStudioWizardState[D]>(
    domain: D,
    field: F,
    current: BotStudioWizardState[D][F],
  ) => (next: SetStateAction<BotStudioWizardState[D][F]>) => {
    const value = typeof next === "function"
      ? (next as (previous: BotStudioWizardState[D][F]) => BotStudioWizardState[D][F])(current)
      : next;
    dispatch({ type: "setField", domain, field: String(field), value });
  };

  return {
    scope: {
      setMode: createFieldSetter("scope", "mode", state.scope.mode),
      setSelectedBotId: createFieldSetter("scope", "selectedBotId", state.scope.selectedBotId),
      setSelectedOrganizationId: createFieldSetter("scope", "selectedOrganizationId", state.scope.selectedOrganizationId),
      setSelectedVerticalId: createFieldSetter("scope", "selectedVerticalId", state.scope.selectedVerticalId),
      setSelectedSubvertical: createFieldSetter("scope", "selectedSubvertical", state.scope.selectedSubvertical),
      setCandidateVerticalId: createFieldSetter("scope", "candidateVerticalId", state.scope.candidateVerticalId),
      setCandidateSubvertical: createFieldSetter("scope", "candidateSubvertical", state.scope.candidateSubvertical),
      setSelectedPrimaryObjective: createFieldSetter("scope", "selectedPrimaryObjective", state.scope.selectedPrimaryObjective),
      setActiveStep: createFieldSetter("scope", "activeStep", state.scope.activeStep),
    },
    basics: {
      setBusinessName: createFieldSetter("basics", "businessName", state.basics.businessName),
      setBotName: createFieldSetter("basics", "botName", state.basics.botName),
      setTone: createFieldSetter("basics", "tone", state.basics.tone),
      setLanguage: createFieldSetter("basics", "language", state.basics.language),
      setTimezone: createFieldSetter("basics", "timezone", state.basics.timezone),
      setHours: createFieldSetter("basics", "hours", state.basics.hours),
      setWhatsappNumber: createFieldSetter("basics", "whatsappNumber", state.basics.whatsappNumber),
    },
    catalog: {
      setServicesText: createFieldSetter("catalog", "servicesText", state.catalog.servicesText),
      setFeaturedOffersText: createFieldSetter("catalog", "featuredOffersText", state.catalog.featuredOffersText),
      setPrimaryCtasText: createFieldSetter("catalog", "primaryCtasText", state.catalog.primaryCtasText),
      setPricingNotesText: createFieldSetter("catalog", "pricingNotesText", state.catalog.pricingNotesText),
    },
    knowledge: {
      setFaqText: createFieldSetter("knowledge", "faqText", state.knowledge.faqText),
      setPoliciesText: createFieldSetter("knowledge", "policiesText", state.knowledge.policiesText),
      setKnowledgeSourcesText: createFieldSetter("knowledge", "knowledgeSourcesText", state.knowledge.knowledgeSourcesText),
    },
    integrations: {
      setSelectedIntegrationKeys: createFieldSetter("integrations", "selectedIntegrationKeys", state.integrations.selectedIntegrationKeys),
      setEscalateWhenText: createFieldSetter("integrations", "escalateWhenText", state.integrations.escalateWhenText),
      setHandoffKeywordsText: createFieldSetter("integrations", "handoffKeywordsText", state.integrations.handoffKeywordsText),
      setHandoffSlaText: createFieldSetter("integrations", "handoffSlaText", state.integrations.handoffSlaText),
      setHumanDestinationChannelText: createFieldSetter("integrations", "humanDestinationChannelText", state.integrations.humanDestinationChannelText),
      setCanSayText: createFieldSetter("integrations", "canSayText", state.integrations.canSayText),
      setCannotSayText: createFieldSetter("integrations", "cannotSayText", state.integrations.cannotSayText),
      setRuleOverridesText: createFieldSetter("integrations", "ruleOverridesText", state.integrations.ruleOverridesText),
    },
    launch: {
      setLaunchNotesText: createFieldSetter("launch", "launchNotesText", state.launch.launchNotesText),
      setSelectedPlaybookKeys: createFieldSetter("launch", "selectedPlaybookKeys", state.launch.selectedPlaybookKeys),
      setAutopublishKnowledge: createFieldSetter("launch", "autopublishKnowledge", state.launch.autopublishKnowledge),
    },
    simulation: {
      setSimulationTitle: createFieldSetter("simulation", "simulationTitle", state.simulation.simulationTitle),
      setSimulationScenario: createFieldSetter("simulation", "simulationScenario", state.simulation.simulationScenario),
      setSimulationExpectedAction: createFieldSetter("simulation", "simulationExpectedAction", state.simulation.simulationExpectedAction),
      setSimulationResult: createFieldSetter("simulation", "simulationResult", state.simulation.simulationResult),
      setSimulationRunning: createFieldSetter("simulation", "simulationRunning", state.simulation.simulationRunning),
      setSimulationError: createFieldSetter("simulation", "simulationError", state.simulation.simulationError),
    },
    preview: {
      setBlueprint: createFieldSetter("preview", "blueprint", state.preview.blueprint),
      setVerticalProfile: createFieldSetter("preview", "verticalProfile", state.preview.verticalProfile),
      setPreviewLoading: createFieldSetter("preview", "previewLoading", state.preview.previewLoading),
      setPreviewError: createFieldSetter("preview", "previewError", state.preview.previewError),
    },
    wizardRuntime: {
      setWizardId: createFieldSetter("wizardRuntime", "wizardId", state.wizardRuntime.wizardId),
      setWizard: createFieldSetter("wizardRuntime", "wizard", state.wizardRuntime.wizard),
      setWorking: createFieldSetter("wizardRuntime", "working", state.wizardRuntime.working),
      setWizardError: createFieldSetter("wizardRuntime", "wizardError", state.wizardRuntime.wizardError),
      setApplyResult: createFieldSetter("wizardRuntime", "applyResult", state.wizardRuntime.applyResult),
      setDryRunResult: createFieldSetter("wizardRuntime", "dryRunResult", state.wizardRuntime.dryRunResult),
      setReviewConfirmed: createFieldSetter("wizardRuntime", "reviewConfirmed", state.wizardRuntime.reviewConfirmed),
      setValidatedWizardRevision: createFieldSetter("wizardRuntime", "validatedWizardRevision", state.wizardRuntime.validatedWizardRevision),
    },
    postApply: {
      setPostApplyBot: createFieldSetter("postApply", "postApplyBot", state.postApply.postApplyBot),
      setPostApplyReleases: createFieldSetter("postApply", "postApplyReleases", state.postApply.postApplyReleases),
      setPostApplySimulationRuns: createFieldSetter("postApply", "postApplySimulationRuns", state.postApply.postApplySimulationRuns),
      setPostApplyLoading: createFieldSetter("postApply", "postApplyLoading", state.postApply.postApplyLoading),
      setPostApplyError: createFieldSetter("postApply", "postApplyError", state.postApply.postApplyError),
      setPostApplyPath: createFieldSetter("postApply", "postApplyPath", state.postApply.postApplyPath),
    },
    autosave: {
      setAutosaveState: createFieldSetter("autosave", "autosaveState", state.autosave.autosaveState),
      setAutosaveError: createFieldSetter("autosave", "autosaveError", state.autosave.autosaveError),
      setLastSavedAt: createFieldSetter("autosave", "lastSavedAt", state.autosave.lastSavedAt),
    },
  };
}

export function useBotStudioWizardState(params: UseBotStudioWizardStateParams) {
  const [slices, dispatch] = useReducer(reducer, params, createInitialState);
  const actions = buildActions(slices, dispatch);
  const patchState = (patch: DeepPartial<BotStudioWizardState>) => dispatch({ type: "patch", patch });

  return {
    slices,
    actions,
    patchState,
    ...slices.scope,
    ...slices.basics,
    ...slices.catalog,
    ...slices.knowledge,
    ...slices.integrations,
    ...slices.launch,
    ...slices.simulation,
    ...slices.preview,
    ...slices.wizardRuntime,
    ...slices.postApply,
    ...slices.autosave,
    ...actions.scope,
    ...actions.basics,
    ...actions.catalog,
    ...actions.knowledge,
    ...actions.integrations,
    ...actions.launch,
    ...actions.simulation,
    ...actions.preview,
    ...actions.wizardRuntime,
    ...actions.postApply,
    ...actions.autosave,
  };
}

export type BotStudioWizardStateModel = ReturnType<typeof useBotStudioWizardState>;

export function useWizardScope(model: BotStudioWizardStateModel) {
  return { state: model.slices.scope, actions: model.actions.scope };
}

export function useWizardBasics(model: BotStudioWizardStateModel) {
  return { state: model.slices.basics, actions: model.actions.basics };
}

export function useWizardCatalog(model: BotStudioWizardStateModel) {
  return { state: model.slices.catalog, actions: model.actions.catalog };
}

export function useWizardKnowledge(model: BotStudioWizardStateModel) {
  return { state: model.slices.knowledge, actions: model.actions.knowledge };
}

export function useWizardIntegrations(model: BotStudioWizardStateModel) {
  return { state: model.slices.integrations, actions: model.actions.integrations };
}

export function useWizardRuntime(model: BotStudioWizardStateModel) {
  return { state: model.slices.wizardRuntime, actions: model.actions.wizardRuntime };
}

export function useWizardAutosave(model: BotStudioWizardStateModel) {
  return { state: model.slices.autosave, actions: model.actions.autosave };
}
