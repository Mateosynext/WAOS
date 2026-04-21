import { useReducer, type SetStateAction } from "react";
import { safeText } from "../lib/ui";
import type { BotContract, ReleaseRequestContract, VerticalProfileContract } from "../lib/contracts";
import type {
  WizardApplyResult,
  WizardBlueprint,
  WizardDryRunResult,
  WizardInstance,
  WizardMode,
  WizardRecommendedIntegration,
} from "./wizard-types";
import { resolveWizardInitialStep, type WizardUiActiveStep as ActiveStep } from "./wizardStepFlow";

type ObjectiveValue = "agendar" | "vender" | "calificar" | "responder" | "reactivar";
type CompletionPath = "wizard" | "module";
type AutosaveState = "idle" | "saving" | "saved" | "error";

const OBJECTIVES: ObjectiveValue[] = ["agendar", "vender", "calificar", "responder", "reactivar"];

type ScopeState = {
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

type BasicsState = {
  businessName: string;
  botName: string;
  tone: string;
  language: string;
  timezone: string;
  hours: string;
  whatsappNumber: string;
};

type CatalogState = {
  servicesText: string;
  featuredOffersText: string;
  primaryCtasText: string;
  pricingNotesText: string;
};

type KnowledgeState = {
  faqText: string;
  policiesText: string;
  knowledgeSourcesText: string;
};

type IntegrationsState = {
  selectedIntegrationKeys: string[];
  escalateWhenText: string;
  handoffKeywordsText: string;
  handoffSlaText: string;
  humanDestinationChannelText: string;
  canSayText: string;
  cannotSayText: string;
  ruleOverridesText: string;
};

type LaunchState = {
  launchNotesText: string;
  selectedPlaybookKeys: string[];
  autopublishKnowledge: boolean;
};

type SimulationState = {
  simulationTitle: string;
  simulationScenario: string;
  simulationExpectedAction: string;
  simulationResult: Record<string, unknown> | null;
  simulationRunning: boolean;
  simulationError: string;
};

type PreviewState = {
  blueprint: WizardBlueprint | null;
  verticalProfile: VerticalProfileContract | null;
  previewLoading: boolean;
  previewError: string;
};

type WizardRuntimeState = {
  wizardId: string;
  wizard: WizardInstance | null;
  working: boolean;
  wizardError: string;
  applyResult: WizardApplyResult | null;
  dryRunResult: WizardDryRunResult | null;
  reviewConfirmed: boolean;
};

type PostApplyState = {
  postApplyBot: BotContract | null;
  postApplyReleases: ReleaseRequestContract[];
  postApplySimulationRuns: Array<Record<string, unknown>>;
  postApplyLoading: boolean;
  postApplyError: string;
  postApplyPath: CompletionPath;
};

type AutosaveStateSlice = {
  autosaveState: AutosaveState;
  autosaveError: string;
  lastSavedAt: string;
};

type BotStudioWizardState = {
  scope: ScopeState;
  basics: BasicsState;
  catalog: CatalogState;
  knowledge: KnowledgeState;
  integrations: IntegrationsState;
  launch: LaunchState;
  simulation: SimulationState;
  preview: PreviewState;
  wizardRuntime: WizardRuntimeState;
  postApply: PostApplyState;
  autosave: AutosaveStateSlice;
};

type StateDomainKey = keyof BotStudioWizardState;

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

type DeepPartial<T> = { [K in keyof T]?: T[K] extends Array<unknown> ? T[K] : T[K] extends object ? DeepPartial<T[K]> : T[K] };

type Action = SetFieldAction | PatchAction;

type UseBotStudioWizardStateParams = {
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

function reducer(state: BotStudioWizardState, action: Action): BotStudioWizardState {
  switch (action.type) {
    case "setField": {
      return {
        ...state,
        [action.domain]: {
          ...state[action.domain],
          [action.field]: action.value,
        },
      } as BotStudioWizardState;
    }
    case "patch":
      return mergeState(state, action.patch);
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
    } as WizardRuntimeState,
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

export function useBotStudioWizardState(params: UseBotStudioWizardStateParams) {
  const [state, dispatch] = useReducer(reducer, params, createInitialState);

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

  const patchState = (patch: DeepPartial<BotStudioWizardState>) => {
    dispatch({ type: "patch", patch });
  };

  const {
    scope,
    basics,
    catalog,
    knowledge,
    integrations,
    launch,
    simulation,
    preview,
    wizardRuntime,
    postApply,
    autosave,
  } = state;

  return {
    ...scope,
    ...basics,
    ...catalog,
    ...knowledge,
    ...integrations,
    ...launch,
    ...simulation,
    ...preview,
    ...wizardRuntime,
    ...postApply,
    ...autosave,
    patchState,
    setMode: createFieldSetter("scope", "mode", scope.mode),
    setSelectedBotId: createFieldSetter("scope", "selectedBotId", scope.selectedBotId),
    setSelectedOrganizationId: createFieldSetter("scope", "selectedOrganizationId", scope.selectedOrganizationId),
    setSelectedVerticalId: createFieldSetter("scope", "selectedVerticalId", scope.selectedVerticalId),
    setSelectedSubvertical: createFieldSetter("scope", "selectedSubvertical", scope.selectedSubvertical),
    setCandidateVerticalId: createFieldSetter("scope", "candidateVerticalId", scope.candidateVerticalId),
    setCandidateSubvertical: createFieldSetter("scope", "candidateSubvertical", scope.candidateSubvertical),
    setSelectedPrimaryObjective: createFieldSetter("scope", "selectedPrimaryObjective", scope.selectedPrimaryObjective),
    setActiveStep: createFieldSetter("scope", "activeStep", scope.activeStep),
    setBusinessName: createFieldSetter("basics", "businessName", basics.businessName),
    setBotName: createFieldSetter("basics", "botName", basics.botName),
    setTone: createFieldSetter("basics", "tone", basics.tone),
    setLanguage: createFieldSetter("basics", "language", basics.language),
    setTimezone: createFieldSetter("basics", "timezone", basics.timezone),
    setHours: createFieldSetter("basics", "hours", basics.hours),
    setWhatsappNumber: createFieldSetter("basics", "whatsappNumber", basics.whatsappNumber),
    setServicesText: createFieldSetter("catalog", "servicesText", catalog.servicesText),
    setFeaturedOffersText: createFieldSetter("catalog", "featuredOffersText", catalog.featuredOffersText),
    setPrimaryCtasText: createFieldSetter("catalog", "primaryCtasText", catalog.primaryCtasText),
    setPricingNotesText: createFieldSetter("catalog", "pricingNotesText", catalog.pricingNotesText),
    setFaqText: createFieldSetter("knowledge", "faqText", knowledge.faqText),
    setPoliciesText: createFieldSetter("knowledge", "policiesText", knowledge.policiesText),
    setKnowledgeSourcesText: createFieldSetter("knowledge", "knowledgeSourcesText", knowledge.knowledgeSourcesText),
    setSelectedIntegrationKeys: createFieldSetter("integrations", "selectedIntegrationKeys", integrations.selectedIntegrationKeys),
    setEscalateWhenText: createFieldSetter("integrations", "escalateWhenText", integrations.escalateWhenText),
    setHandoffKeywordsText: createFieldSetter("integrations", "handoffKeywordsText", integrations.handoffKeywordsText),
    setHandoffSlaText: createFieldSetter("integrations", "handoffSlaText", integrations.handoffSlaText),
    setHumanDestinationChannelText: createFieldSetter("integrations", "humanDestinationChannelText", integrations.humanDestinationChannelText),
    setCanSayText: createFieldSetter("integrations", "canSayText", integrations.canSayText),
    setCannotSayText: createFieldSetter("integrations", "cannotSayText", integrations.cannotSayText),
    setRuleOverridesText: createFieldSetter("integrations", "ruleOverridesText", integrations.ruleOverridesText),
    setLaunchNotesText: createFieldSetter("launch", "launchNotesText", launch.launchNotesText),
    setSelectedPlaybookKeys: createFieldSetter("launch", "selectedPlaybookKeys", launch.selectedPlaybookKeys),
    setAutopublishKnowledge: createFieldSetter("launch", "autopublishKnowledge", launch.autopublishKnowledge),
    setSimulationTitle: createFieldSetter("simulation", "simulationTitle", simulation.simulationTitle),
    setSimulationScenario: createFieldSetter("simulation", "simulationScenario", simulation.simulationScenario),
    setSimulationExpectedAction: createFieldSetter("simulation", "simulationExpectedAction", simulation.simulationExpectedAction),
    setSimulationResult: createFieldSetter("simulation", "simulationResult", simulation.simulationResult),
    setSimulationRunning: createFieldSetter("simulation", "simulationRunning", simulation.simulationRunning),
    setSimulationError: createFieldSetter("simulation", "simulationError", simulation.simulationError),
    setBlueprint: createFieldSetter("preview", "blueprint", preview.blueprint),
    setVerticalProfile: createFieldSetter("preview", "verticalProfile", preview.verticalProfile),
    setPreviewLoading: createFieldSetter("preview", "previewLoading", preview.previewLoading),
    setPreviewError: createFieldSetter("preview", "previewError", preview.previewError),
    setWizardId: createFieldSetter("wizardRuntime", "wizardId", wizardRuntime.wizardId),
    setWizard: createFieldSetter("wizardRuntime", "wizard", wizardRuntime.wizard),
    setWorking: createFieldSetter("wizardRuntime", "working", wizardRuntime.working),
    setWizardError: createFieldSetter("wizardRuntime", "wizardError", wizardRuntime.wizardError),
    setApplyResult: createFieldSetter("wizardRuntime", "applyResult", wizardRuntime.applyResult),
    setDryRunResult: createFieldSetter("wizardRuntime", "dryRunResult", wizardRuntime.dryRunResult),
    setReviewConfirmed: createFieldSetter("wizardRuntime", "reviewConfirmed", wizardRuntime.reviewConfirmed),
    setPostApplyBot: createFieldSetter("postApply", "postApplyBot", postApply.postApplyBot),
    setPostApplyReleases: createFieldSetter("postApply", "postApplyReleases", postApply.postApplyReleases),
    setPostApplySimulationRuns: createFieldSetter("postApply", "postApplySimulationRuns", postApply.postApplySimulationRuns),
    setPostApplyLoading: createFieldSetter("postApply", "postApplyLoading", postApply.postApplyLoading),
    setPostApplyError: createFieldSetter("postApply", "postApplyError", postApply.postApplyError),
    setPostApplyPath: createFieldSetter("postApply", "postApplyPath", postApply.postApplyPath),
    setAutosaveState: createFieldSetter("autosave", "autosaveState", autosave.autosaveState),
    setAutosaveError: createFieldSetter("autosave", "autosaveError", autosave.autosaveError),
    setLastSavedAt: createFieldSetter("autosave", "lastSavedAt", autosave.lastSavedAt),
  };
}
