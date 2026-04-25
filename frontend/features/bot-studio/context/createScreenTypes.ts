import type { SessionOrganization } from "@/app/lib/contracts/auth";
import type { VerticalProfileContract } from "@/app/lib/contracts/verticals";
import type { WizardAiIntensity, WizardAiPrefillResult } from "../services/wizardApi";
import type { WizardBlueprint, WizardDryRunResult, WizardInstance, WizardValidationSnapshot } from "@/features/bot-studio/domain/wizardTypes";

export type WizardSetter<T> = (next: T | ((previous: T) => T)) => void;

export type CreateContextViewModel = {
  organizations: SessionOrganization[];
  verticals: VerticalProfileContract[];
  strongestVerticals: VerticalProfileContract[];
  selectedOrganizationId: string;
  selectedVerticalId: string;
  selectedSubvertical: string;
  candidateVerticalId: string;
  candidateSubvertical: string;
  selectedPrimaryObjective: string;
  blueprint: WizardBlueprint | null;
  verticalProfile: VerticalProfileContract | null;
  previewLoading: boolean;
  previewError: string;
};

export type CreateIdentityViewModel = {
  businessName: string;
  botName: string;
  tone: string;
  language: string;
  timezone: string;
  hours: string;
  whatsappNumber: string;
};

export type CreateOfferViewModel = {
  servicesText: string;
  featuredOffersText: string;
  primaryCtasText: string;
  pricingNotesText: string;
};

export type CreateKnowledgeViewModel = {
  faqText: string;
  policiesText: string;
  knowledgeSourcesText: string;
};

export type CreateIntegrationsViewModel = {
  blueprint: WizardBlueprint | null;
  selectedIntegrationKeys: string[];
  escalateWhenText: string;
  handoffKeywordsText: string;
  handoffSlaText: string;
  humanDestinationChannelText: string;
  canSayText: string;
  cannotSayText: string;
  ruleOverridesText: string;
};

export type CreateReviewViewModel = CreateContextViewModel & CreateOfferViewModel & CreateKnowledgeViewModel & {
  selectedIntegrationKeys: string[];
  selectedPlaybookKeys: string[];
  launchNotesText: string;
  autopublishKnowledge: boolean;
};

export type CreateValidationViewModel = {
  aiAutofixRunning?: boolean;
  validationSnapshot?: WizardValidationSnapshot | null;
  wizard?: WizardInstance | null;
  dryRunResult?: WizardDryRunResult | null;
};

export type CreateValidationActions = {
  autofixWithAi: () => Promise<Record<string, unknown>>;
};

export type CreateApplyViewModel = CreateValidationViewModel & {
  autopublishKnowledge: boolean;
};

export type CreateContextActions = {
  generateAiPrefill: (input: { userDescription: string; intensity: WizardAiIntensity }) => Promise<WizardAiPrefillResult>;
  runAiAutopilot: (input: { userDescription: string; intensity: WizardAiIntensity }) => Promise<WizardAiPrefillResult>;
  applyAiPrefill: (result: WizardAiPrefillResult) => Promise<void>;
  setSelectedOrganizationId: (value: string) => void;
  setSelectedPrimaryObjective: (value: string) => void;
  setCandidateVerticalId: (value: string) => void;
  setSelectedVerticalId: (value: string) => void;
  setCandidateSubvertical: (value: string) => void;
  setSelectedSubvertical: (value: string) => void;
};

export type CreateIdentityActions = {
  setBusinessName: (value: string) => void;
  setBotName: (value: string) => void;
  setTone: (value: string) => void;
  setLanguage: (value: string) => void;
  setTimezone: (value: string) => void;
  setWhatsappNumber: (value: string) => void;
  setHours: (value: string) => void;
};

export type CreateOfferActions = {
  setServicesText: (value: string) => void;
  setFeaturedOffersText: (value: string) => void;
  setPrimaryCtasText: (value: string) => void;
  setPricingNotesText: (value: string) => void;
};

export type CreateKnowledgeActions = {
  setFaqText: (value: string) => void;
  setPoliciesText: (value: string) => void;
  setKnowledgeSourcesText: (value: string) => void;
};

export type CreateIntegrationsActions = {
  setSelectedIntegrationKeys: WizardSetter<string[]>;
  setEscalateWhenText: (value: string) => void;
  setHandoffKeywordsText: (value: string) => void;
  setHandoffSlaText: (value: string) => void;
  setHumanDestinationChannelText: (value: string) => void;
  setCanSayText: (value: string) => void;
  setCannotSayText: (value: string) => void;
  setRuleOverridesText: (value: string) => void;
};

export type CreateReviewActions = {
  setSelectedPlaybookKeys: WizardSetter<string[]>;
  setLaunchNotesText: (value: string) => void;
  setAutopublishKnowledge: WizardSetter<boolean>;
};

export type CreateWizardViewModel = CreateReviewViewModel & CreateIdentityViewModel & CreateIntegrationsViewModel & CreateValidationViewModel & CreateApplyViewModel;
export type CreateWizardActions = CreateContextActions & CreateIdentityActions & CreateOfferActions & CreateKnowledgeActions & CreateIntegrationsActions & CreateReviewActions;
