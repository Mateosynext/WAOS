"use client";

import { useEffect, useMemo, useRef } from "react";
import { createLatestWizardReactiveSelectionLoader } from "@/features/bot-studio/services/wizardReactiveData";
import { buildWizardPayloads } from "@/features/bot-studio/services/wizardPayloadBuilders";
import { safeText } from "@/shared/lib/ui";
import { buildBotStudioSummaryViewModel, pickBotSubvertical, pickBotTone, resolveMatchingVertical } from "../shared/botStudioHelpers";
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

function normalizeObjectiveValue(value: unknown, fallback: ObjectiveValue): ObjectiveValue {
  const normalized = String(value || "").trim().toLowerCase();
  return (["agendar", "vender", "calificar", "responder", "reactivar"] as ObjectiveValue[]).includes(normalized as ObjectiveValue)
    ? (normalized as ObjectiveValue)
    : fallback;
}

function hasPatchDelta(current: Record<string, unknown>, next: Record<string, unknown>) {
  return Object.entries(next).some(([key, value]) => current[key] !== value);
}

export function useBotStudioFlowStateModel(
  props: BotStudioFlowProps,
  state: BotStudioWizardStateModel,
  progress: number,
) {
  const {
    scope,
    basics,
    catalog,
    knowledge,
    integrations,
    launch,
    preview,
    wizardRuntime,
  } = state.slices;
  const actions = state.actions;

  const selectedOrganization = useMemo(
    () => props.organizations.find((item) => item.id === scope.selectedOrganizationId) || null,
    [props.organizations, scope.selectedOrganizationId],
  );
  const selectedBot = useMemo(
    () => props.bots.find((item) => item.id === scope.selectedBotId) || null,
    [props.bots, scope.selectedBotId],
  );

  useEffect(() => {
    if (props.routeMode !== "reconfigure" || !selectedBot) return;
    const matchingVertical = resolveMatchingVertical(props.verticals, scope.selectedVerticalId, selectedBot);
    const botSubvertical = pickBotSubvertical(selectedBot, selectedOrganization);
    const nextScope = {
      selectedOrganizationId: selectedBot.organization_id,
      selectedVerticalId: matchingVertical?.id || scope.selectedVerticalId,
      candidateVerticalId: matchingVertical?.id || scope.candidateVerticalId,
      selectedSubvertical: scope.selectedSubvertical || botSubvertical,
      candidateSubvertical: scope.candidateSubvertical || botSubvertical,
      selectedPrimaryObjective: normalizeObjectiveValue(selectedBot.objective || selectedBot.goal, scope.selectedPrimaryObjective),
    };
    const nextBasics = {
      businessName: basics.businessName || safeText(selectedBot.business_name, safeText(selectedOrganization?.name, "Negocio WAOS")),
      botName: basics.botName || safeText(selectedBot.name, "Asistente operativo"),
      tone: basics.tone || pickBotTone(selectedBot),
      language: basics.language || safeText(selectedBot.language, "es"),
      timezone: basics.timezone || safeText(selectedBot.timezone, safeText(selectedOrganization?.timezone, "America/Mexico_City")),
      whatsappNumber: basics.whatsappNumber || safeText(selectedBot.phone_number),
    };
    if (!hasPatchDelta(scope as unknown as Record<string, unknown>, nextScope) && !hasPatchDelta(basics as unknown as Record<string, unknown>, nextBasics)) return;
    state.patchState({ scope: nextScope, basics: nextBasics });
  }, [
    basics.businessName,
    basics.botName,
    basics.language,
    basics.tone,
    basics.timezone,
    basics.whatsappNumber,
    props.routeMode,
    props.verticals,
    scope.candidateSubvertical,
    scope.candidateVerticalId,
    scope.selectedPrimaryObjective,
    scope.selectedSubvertical,
    scope.selectedVerticalId,
    selectedBot,
    selectedOrganization,
  ]);

  const loader = useRef(createLatestWizardReactiveSelectionLoader());
  useEffect(() => {
    if (!scope.selectedOrganizationId || !scope.candidateVerticalId) return;
    actions.preview.setPreviewLoading(true);
    loader.current.load({
      organizationId: scope.selectedOrganizationId,
      verticalId: scope.candidateVerticalId,
      subvertical: scope.candidateSubvertical || scope.selectedSubvertical,
      primaryObjective: scope.selectedPrimaryObjective,
      mode: props.routeMode,
      botId: props.routeMode === "reconfigure" ? scope.selectedBotId : undefined,
    }).then((result) => {
      if (!result) return;
      actions.preview.setBlueprint(result.blueprint);
      actions.preview.setVerticalProfile(result.verticalProfile);
      actions.preview.setPreviewError(result.errors.join(" "));
    }).catch((error) => {
      actions.preview.setPreviewError(error instanceof Error ? error.message : "No se pudo refrescar la preview del paso.");
    }).finally(() => actions.preview.setPreviewLoading(false));
    return () => loader.current.cancel();
  }, [
    props.routeMode,
    scope.candidateSubvertical,
    scope.candidateVerticalId,
    scope.selectedBotId,
    scope.selectedOrganizationId,
    scope.selectedPrimaryObjective,
    scope.selectedSubvertical,
  ]);

  const payloads = useMemo(() => buildWizardPayloads({
    mode: props.routeMode,
    selectedOrganizationId: scope.selectedOrganizationId,
    selectedBotId: scope.selectedBotId,
    selectedVerticalId: scope.selectedVerticalId,
    selectedSubvertical: scope.selectedSubvertical,
    selectedPrimaryObjective: scope.selectedPrimaryObjective,
    selectedOrganization,
    businessName: basics.businessName,
    botName: basics.botName,
    tone: basics.tone,
    language: basics.language,
    timezone: basics.timezone,
    hours: basics.hours,
    whatsappNumber: basics.whatsappNumber,
    servicesText: catalog.servicesText,
    featuredOffersText: catalog.featuredOffersText,
    pricingNotesText: catalog.pricingNotesText,
    primaryCtasText: catalog.primaryCtasText,
    faqText: knowledge.faqText,
    policiesText: knowledge.policiesText,
    knowledgeSourcesText: knowledge.knowledgeSourcesText,
    selectedIntegrationKeys: integrations.selectedIntegrationKeys,
    integrationOptions: preview.blueprint?.setup?.wizard?.recommended_integrations || [],
    escalateWhenText: integrations.escalateWhenText,
    handoffKeywordsText: integrations.handoffKeywordsText,
    handoffSlaText: integrations.handoffSlaText,
    humanDestinationChannelText: integrations.humanDestinationChannelText,
    canSayText: integrations.canSayText,
    cannotSayText: integrations.cannotSayText,
    ruleOverridesText: integrations.ruleOverridesText,
    selectedPlaybookKeys: launch.selectedPlaybookKeys,
    recommendedPlaybooks: preview.blueprint?.setup?.wizard?.recommended_playbooks || [],
    launchNotesText: launch.launchNotesText,
    autopublishKnowledge: launch.autopublishKnowledge,
  }), [
    basics.businessName,
    basics.botName,
    basics.hours,
    basics.language,
    basics.timezone,
    basics.tone,
    basics.whatsappNumber,
    catalog.featuredOffersText,
    catalog.pricingNotesText,
    catalog.primaryCtasText,
    catalog.servicesText,
    integrations.canSayText,
    integrations.cannotSayText,
    integrations.escalateWhenText,
    integrations.handoffKeywordsText,
    integrations.handoffSlaText,
    integrations.humanDestinationChannelText,
    integrations.ruleOverridesText,
    integrations.selectedIntegrationKeys,
    knowledge.faqText,
    knowledge.knowledgeSourcesText,
    knowledge.policiesText,
    launch.autopublishKnowledge,
    launch.launchNotesText,
    launch.selectedPlaybookKeys,
    preview.blueprint,
    props.routeMode,
    scope.selectedBotId,
    scope.selectedOrganizationId,
    scope.selectedPrimaryObjective,
    scope.selectedSubvertical,
    scope.selectedVerticalId,
    selectedOrganization,
  ]);

  const snapshot = useMemo(
    () => wizardRuntime.dryRunResult?.validation_snapshot || wizardRuntime.wizard?.validation_snapshot || props.initialWizard?.validation_snapshot || null,
    [props.initialWizard?.validation_snapshot, wizardRuntime.dryRunResult?.validation_snapshot, wizardRuntime.wizard?.validation_snapshot],
  );

  const createScreens: CreateWizardScreenModels = useMemo(() => ({
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
    validate: {
      viewModel: {
        validationSnapshot: snapshot,
        wizard: wizardRuntime.wizard,
        dryRunResult: wizardRuntime.dryRunResult,
        wizardError: wizardRuntime.wizardError,
      },
    },
    apply: {
      viewModel: {
        validationSnapshot: snapshot,
        wizard: wizardRuntime.wizard,
        dryRunResult: wizardRuntime.dryRunResult,
        wizardError: wizardRuntime.wizardError,
        autopublishKnowledge: launch.autopublishKnowledge,
      },
    },
  }), [
    actions.basics,
    actions.catalog,
    actions.integrations,
    actions.knowledge,
    actions.launch,
    actions.scope,
    basics,
    catalog,
    integrations,
    knowledge,
    launch.autopublishKnowledge,
    launch.launchNotesText,
    launch.selectedPlaybookKeys,
    preview.blueprint,
    preview.previewError,
    preview.previewLoading,
    preview.verticalProfile,
    props.organizations,
    props.strongestVerticals,
    props.verticals,
    scope.candidateSubvertical,
    scope.candidateVerticalId,
    scope.selectedOrganizationId,
    scope.selectedPrimaryObjective,
    scope.selectedSubvertical,
    scope.selectedVerticalId,
    snapshot,
    wizardRuntime.dryRunResult,
    wizardRuntime.wizardError,
    wizardRuntime.wizard,
  ]);

  const reconfigureScreens: ReconfigureWizardScreenModels = useMemo(() => {
    const diffViewModel = {
      selectedBot,
      blueprint: preview.blueprint,
      wizard: wizardRuntime.wizard,
    };
    const validationViewModel = {
      ...diffViewModel,
      validationSnapshot: snapshot,
      dryRunResult: wizardRuntime.dryRunResult,
      wizardError: wizardRuntime.wizardError,
    };
    return {
      select: {
        viewModel: { bots: props.bots, selectedBot },
        actions: { setSelectedBotId: actions.scope.setSelectedBotId },
      },
      diff: { viewModel: diffViewModel },
      dryRun: { viewModel: validationViewModel },
      confirm: { viewModel: validationViewModel },
    };
  }, [actions.scope.setSelectedBotId, preview.blueprint, props.bots, selectedBot, snapshot, wizardRuntime.dryRunResult, wizardRuntime.wizardError, wizardRuntime.wizard]);

  const summary = useMemo(() => buildBotStudioSummaryViewModel({
    routeMode: props.routeMode,
    routeStep: props.routeStep,
    selectedOrganization,
    selectedBot,
    organizations: props.organizations,
    verticals: props.verticals,
    selectedVerticalId: scope.selectedVerticalId,
    selectedSubvertical: scope.selectedSubvertical,
    selectedPrimaryObjective: scope.selectedPrimaryObjective,
    selectedIntegrationKeys: integrations.selectedIntegrationKeys,
    selectedPlaybookKeys: launch.selectedPlaybookKeys,
    servicesText: catalog.servicesText,
    wizard: wizardRuntime.wizard,
    wizardId: wizardRuntime.wizardId,
    blueprint: preview.blueprint,
    snapshot,
    progress,
    businessName: basics.businessName,
    botName: basics.botName,
  }), [
    basics.botName,
    basics.businessName,
    catalog.servicesText,
    integrations.selectedIntegrationKeys,
    launch.selectedPlaybookKeys,
    preview.blueprint,
    progress,
    props.organizations,
    props.routeMode,
    props.routeStep,
    props.verticals,
    scope.selectedPrimaryObjective,
    scope.selectedSubvertical,
    scope.selectedVerticalId,
    selectedBot,
    selectedOrganization,
    snapshot,
    wizardRuntime.wizard,
    wizardRuntime.wizardId,
  ]);

  return { createScreens, payloads, reconfigureScreens, selectedBot, selectedOrganization, snapshot, summary };
}
