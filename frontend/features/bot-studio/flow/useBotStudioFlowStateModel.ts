"use client";

import { useEffect, useMemo, useRef } from "react";
import { safeText } from "@/app/lib/ui";
import { buildBotStudioSummaryViewModel, pickBotSubvertical, pickBotTone, resolveMatchingVertical } from "../shared/botStudioHelpers";
import type { BotStudioWizardStateModel } from "../context/useBotStudioWizardState";
import { buildWizardPayloads } from "../services/wizardPayloadBuilders";
import { createLatestWizardReactiveSelectionLoader } from "../services/wizardReactiveData";
import type { BotStudioFlowProps } from "./types";
import {
  buildBlueprintSeedPatch,
  buildReactiveSelectionKey,
  hasBlueprintSeedPatch,
  normalizeObjectiveValue,
} from "./wizardPreviewSeed";
import {
  buildCreateWizardScreenModels,
  buildReconfigureWizardScreenModels,
  type CreateWizardScreenModels,
  type ReconfigureWizardScreenModels,
} from "./wizardScreenModels";

export type { CreateWizardScreenModels, ReconfigureWizardScreenModels } from "./wizardScreenModels";

function hasPatchDelta(current: Record<string, unknown>, next: Record<string, unknown>) {
  return Object.entries(next).some(([key, value]) => current[key] !== value);
}

export function useBotStudioFlowStateModel(
  props: BotStudioFlowProps,
  state: BotStudioWizardStateModel,
  progress: number,
) {
  const { scope, basics, catalog, knowledge, integrations, launch, preview, wizardRuntime } = state.slices;
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
    basics.timezone,
    basics.tone,
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
  const didHydrateInitialPreview = useRef(false);
  const lastInitialPreviewSelectionKey = useRef("");
  const lastLoadedPreviewKey = useRef("");
  const lastSeededPreviewKey = useRef("");

  const initialPreviewSelectionKey = useMemo(() => buildReactiveSelectionKey({
    organizationId: props.initialOrganizationId,
    verticalId: props.initialVerticalId,
    subvertical: props.initialSubvertical,
    primaryObjective: props.initialPrimaryObjective,
    mode: props.routeMode,
    botId: props.initialSelectedBotId,
  }), [
    props.initialOrganizationId,
    props.initialPrimaryObjective,
    props.initialSelectedBotId,
    props.initialSubvertical,
    props.initialVerticalId,
    props.routeMode,
  ]);

  useEffect(() => {
    if (lastInitialPreviewSelectionKey.current === initialPreviewSelectionKey) return;
    lastInitialPreviewSelectionKey.current = initialPreviewSelectionKey;
    didHydrateInitialPreview.current = false;
  }, [initialPreviewSelectionKey]);

  useEffect(() => {
    if (!scope.selectedOrganizationId || !scope.candidateVerticalId) return;

    const selectionRequest = {
      organizationId: scope.selectedOrganizationId,
      verticalId: scope.candidateVerticalId,
      subvertical: scope.candidateSubvertical || scope.selectedSubvertical,
      primaryObjective: scope.selectedPrimaryObjective,
      mode: props.routeMode,
      botId: props.routeMode === "reconfigure" ? scope.selectedBotId : undefined,
    };
    const currentPreviewSelectionKey = buildReactiveSelectionKey(selectionRequest);
    const hasInitialPreview = Boolean(props.initialBlueprint || props.initialVerticalProfile);
    const hasLocalPreviewForSameSelection = Boolean(preview.blueprint || preview.verticalProfile) && lastLoadedPreviewKey.current === currentPreviewSelectionKey;

    if (hasLocalPreviewForSameSelection) return;

    if (!didHydrateInitialPreview.current && hasInitialPreview && currentPreviewSelectionKey === initialPreviewSelectionKey) {
      didHydrateInitialPreview.current = true;
      lastLoadedPreviewKey.current = currentPreviewSelectionKey;
      return;
    }

    actions.preview.setPreviewLoading(true);
    loader.current.load(selectionRequest).then((result) => {
      if (!result) return;
      lastLoadedPreviewKey.current = currentPreviewSelectionKey;
      actions.preview.setBlueprint(result.blueprint);
      actions.preview.setVerticalProfile(result.verticalProfile);
      actions.preview.setPreviewError(result.errors.join(" "));
    }).catch((error) => {
      actions.preview.setPreviewError(error instanceof Error ? error.message : "No se pudo refrescar la preview del paso.");
    }).finally(() => actions.preview.setPreviewLoading(false));
    return () => loader.current.cancel();
  }, [
    initialPreviewSelectionKey,
    preview.blueprint,
    preview.verticalProfile,
    props.initialBlueprint,
    props.initialVerticalProfile,
    props.routeMode,
    scope.candidateSubvertical,
    scope.candidateVerticalId,
    scope.selectedBotId,
    scope.selectedOrganizationId,
    scope.selectedPrimaryObjective,
    scope.selectedSubvertical,
  ]);

  useEffect(() => {
    if (!preview.blueprint || !scope.selectedOrganizationId || !scope.candidateVerticalId) return;
    const currentPreviewSelectionKey = buildReactiveSelectionKey({
      organizationId: scope.selectedOrganizationId,
      verticalId: scope.candidateVerticalId,
      subvertical: scope.candidateSubvertical || scope.selectedSubvertical,
      primaryObjective: scope.selectedPrimaryObjective,
      mode: props.routeMode,
      botId: props.routeMode === "reconfigure" ? scope.selectedBotId : undefined,
    });

    if (lastSeededPreviewKey.current === currentPreviewSelectionKey) return;
    const seedPatch = buildBlueprintSeedPatch(preview.blueprint, catalog, knowledge, integrations);
    lastSeededPreviewKey.current = currentPreviewSelectionKey;
    if (hasBlueprintSeedPatch(seedPatch)) state.patchState(seedPatch);
  }, [
    catalog,
    integrations,
    knowledge,
    preview.blueprint,
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
    basics,
    catalog,
    integrations,
    knowledge,
    launch,
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

  const createScreens: CreateWizardScreenModels = useMemo(() => buildCreateWizardScreenModels({
    props,
    actions,
    scope,
    basics,
    catalog,
    knowledge,
    integrations,
    launch,
    preview,
    wizardRuntime,
    snapshot,
    normalizeObjectiveValue,
  }), [actions, basics, catalog, integrations, knowledge, launch, preview, props, scope, snapshot, wizardRuntime]);

  const reconfigureScreens: ReconfigureWizardScreenModels = useMemo(() => buildReconfigureWizardScreenModels({
    props,
    actions,
    selectedBot,
    blueprint: preview.blueprint,
    wizard: wizardRuntime.wizard,
    snapshot,
    dryRunResult: wizardRuntime.dryRunResult,
  }), [actions, preview.blueprint, props, selectedBot, snapshot, wizardRuntime.dryRunResult, wizardRuntime.wizard]);

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
