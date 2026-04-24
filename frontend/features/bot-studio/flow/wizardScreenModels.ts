import type { BotContract } from "@/app/lib/contracts/bots";
import type { BotStudioWizardStateModel, ObjectiveValue } from "../context/useBotStudioWizardState";
import type {
  CreateApplyViewModel,
  CreateContextActions,
  CreateContextViewModel,
  CreateIdentityViewModel,
  CreateIntegrationsViewModel,
  CreateKnowledgeViewModel,
  CreateOfferViewModel,
  CreateReviewViewModel,
  CreateValidationViewModel,
} from "../context/createScreenTypes";
import type {
  ReconfigureDiffViewModel,
  ReconfigureSelectActions,
  ReconfigureSelectViewModel,
  ReconfigureValidationViewModel,
} from "../reconfigure/reconfigureScreenTypes";
import type { BotStudioFlowProps } from "./types";

export type CreateWizardScreenModels = {
  context: { viewModel: CreateContextViewModel; actions: CreateContextActions };
  identity: { viewModel: CreateIdentityViewModel; actions: BotStudioWizardStateModel["actions"]["basics"] };
  offer: { viewModel: CreateOfferViewModel; actions: BotStudioWizardStateModel["actions"]["catalog"] };
  knowledge: { viewModel: CreateKnowledgeViewModel; actions: BotStudioWizardStateModel["actions"]["knowledge"] };
  integrations: { viewModel: CreateIntegrationsViewModel; actions: BotStudioWizardStateModel["actions"]["integrations"] };
  review: { viewModel: CreateReviewViewModel; actions: BotStudioWizardStateModel["actions"]["launch"] };
  validate: { viewModel: CreateValidationViewModel };
  apply: { viewModel: CreateApplyViewModel };
};

export type ReconfigureWizardScreenModels = {
  select: { viewModel: ReconfigureSelectViewModel; actions: ReconfigureSelectActions };
  diff: { viewModel: ReconfigureDiffViewModel };
  dryRun: { viewModel: ReconfigureValidationViewModel };
  confirm: { viewModel: ReconfigureValidationViewModel };
};

type ScreenSlices = BotStudioWizardStateModel["slices"];

type BuildCreateArgs = {
  props: BotStudioFlowProps;
  actions: BotStudioWizardStateModel["actions"];
  scope: ScreenSlices["scope"];
  basics: ScreenSlices["basics"];
  catalog: ScreenSlices["catalog"];
  knowledge: ScreenSlices["knowledge"];
  integrations: ScreenSlices["integrations"];
  launch: ScreenSlices["launch"];
  preview: ScreenSlices["preview"];
  wizardRuntime: ScreenSlices["wizardRuntime"];
  snapshot: CreateValidationViewModel["validationSnapshot"];
  normalizeObjectiveValue: (value: unknown, fallback: ObjectiveValue) => ObjectiveValue;
};

export function buildCreateWizardScreenModels(args: BuildCreateArgs): CreateWizardScreenModels {
  const { props, actions, scope, basics, catalog, knowledge, integrations, launch, preview, wizardRuntime, snapshot, normalizeObjectiveValue } = args;

  return {
    context: {
      viewModel: {
        organizations: props.organizations,
        verticals: props.verticals,
        strongestVerticals: props.strongestVerticals,
        selectedOrganizationId: scope.selectedOrganizationId,
        selectedVerticalId: scope.selectedVerticalId,
        selectedSubvertical: scope.selectedSubvertical,
        candidateVerticalId: scope.candidateVerticalId,
        candidateSubvertical: scope.candidateSubvertical,
        selectedPrimaryObjective: scope.selectedPrimaryObjective,
        blueprint: preview.blueprint,
        verticalProfile: preview.verticalProfile,
        previewLoading: preview.previewLoading,
        previewError: preview.previewError,
      },
      actions: {
        setSelectedOrganizationId: actions.scope.setSelectedOrganizationId,
        setSelectedPrimaryObjective: (value) => actions.scope.setSelectedPrimaryObjective(normalizeObjectiveValue(value, scope.selectedPrimaryObjective)),
        setCandidateVerticalId: actions.scope.setCandidateVerticalId,
        setSelectedVerticalId: actions.scope.setSelectedVerticalId,
        setCandidateSubvertical: actions.scope.setCandidateSubvertical,
        setSelectedSubvertical: actions.scope.setSelectedSubvertical,
      },
    },
    identity: { viewModel: basics, actions: actions.basics },
    offer: { viewModel: catalog, actions: actions.catalog },
    knowledge: { viewModel: knowledge, actions: actions.knowledge },
    integrations: {
      viewModel: {
        blueprint: preview.blueprint,
        selectedIntegrationKeys: integrations.selectedIntegrationKeys,
        escalateWhenText: integrations.escalateWhenText,
        handoffKeywordsText: integrations.handoffKeywordsText,
        handoffSlaText: integrations.handoffSlaText,
        humanDestinationChannelText: integrations.humanDestinationChannelText,
        canSayText: integrations.canSayText,
        cannotSayText: integrations.cannotSayText,
        ruleOverridesText: integrations.ruleOverridesText,
      },
      actions: actions.integrations,
    },
    review: {
      viewModel: {
        organizations: props.organizations,
        verticals: props.verticals,
        strongestVerticals: props.strongestVerticals,
        selectedOrganizationId: scope.selectedOrganizationId,
        selectedVerticalId: scope.selectedVerticalId,
        selectedSubvertical: scope.selectedSubvertical,
        candidateVerticalId: scope.candidateVerticalId,
        candidateSubvertical: scope.candidateSubvertical,
        selectedPrimaryObjective: scope.selectedPrimaryObjective,
        blueprint: preview.blueprint,
        verticalProfile: preview.verticalProfile,
        previewLoading: preview.previewLoading,
        previewError: preview.previewError,
        servicesText: catalog.servicesText,
        featuredOffersText: catalog.featuredOffersText,
        primaryCtasText: catalog.primaryCtasText,
        pricingNotesText: catalog.pricingNotesText,
        faqText: knowledge.faqText,
        policiesText: knowledge.policiesText,
        knowledgeSourcesText: knowledge.knowledgeSourcesText,
        selectedIntegrationKeys: integrations.selectedIntegrationKeys,
        selectedPlaybookKeys: launch.selectedPlaybookKeys,
        launchNotesText: launch.launchNotesText,
        autopublishKnowledge: launch.autopublishKnowledge,
      },
      actions: actions.launch,
    },
    validate: { viewModel: { validationSnapshot: snapshot, wizard: wizardRuntime.wizard, dryRunResult: wizardRuntime.dryRunResult } },
    apply: { viewModel: { validationSnapshot: snapshot, wizard: wizardRuntime.wizard, dryRunResult: wizardRuntime.dryRunResult, autopublishKnowledge: launch.autopublishKnowledge } },
  };
}

type BuildReconfigureArgs = {
  props: BotStudioFlowProps;
  actions: BotStudioWizardStateModel["actions"];
  selectedBot: BotContract | null;
  blueprint: ScreenSlices["preview"]["blueprint"];
  wizard: ScreenSlices["wizardRuntime"]["wizard"];
  snapshot: ReconfigureValidationViewModel["validationSnapshot"];
  dryRunResult: ScreenSlices["wizardRuntime"]["dryRunResult"];
};

export function buildReconfigureWizardScreenModels(args: BuildReconfigureArgs): ReconfigureWizardScreenModels {
  const { props, actions, selectedBot, blueprint, wizard, snapshot, dryRunResult } = args;
  const diffViewModel = { selectedBot, blueprint, wizard };
  const validationViewModel = { ...diffViewModel, validationSnapshot: snapshot, dryRunResult };

  return {
    select: { viewModel: { bots: props.bots, selectedBot }, actions: { setSelectedBotId: actions.scope.setSelectedBotId } },
    diff: { viewModel: diffViewModel },
    dryRun: { viewModel: validationViewModel },
    confirm: { viewModel: validationViewModel },
  };
}
