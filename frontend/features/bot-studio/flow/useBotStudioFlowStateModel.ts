"use client";

import { useEffect, useMemo, useRef } from "react";
import { createLatestWizardReactiveSelectionLoader } from "../../../app/bot-studio/wizardReactiveData";
import { buildWizardPayloads } from "../../../app/bot-studio/wizardPayloadBuilders";
import { safeText } from "../../../app/lib/ui";
import { buildBotStudioSummaryViewModel, pickBotSubvertical, pickBotTone, resolveMatchingVertical } from "../shared/botStudioHelpers";
import { useBotStudioWizardState } from "../context/useBotStudioWizardState";
import type { BotStudioFlowProps } from "./types";

export function useBotStudioFlowStateModel(
  props: BotStudioFlowProps,
  state: ReturnType<typeof useBotStudioWizardState>,
  progress: number,
) {
  const selectedOrganization = useMemo(
    () => props.organizations.find((item) => item.id === state.selectedOrganizationId) || null,
    [props.organizations, state.selectedOrganizationId],
  );
  const selectedBot = useMemo(
    () => props.bots.find((item) => item.id === state.selectedBotId) || null,
    [props.bots, state.selectedBotId],
  );

  useEffect(() => {
    if (props.routeMode !== "reconfigure" || !selectedBot) return;
    const matchingVertical = resolveMatchingVertical(props.verticals, state.selectedVerticalId, selectedBot);
    state.patchState({
      scope: {
        selectedOrganizationId: selectedBot.organization_id,
        selectedVerticalId: matchingVertical?.id || state.selectedVerticalId,
        candidateVerticalId: matchingVertical?.id || state.candidateVerticalId,
        selectedSubvertical: state.selectedSubvertical || pickBotSubvertical(selectedBot, selectedOrganization),
        candidateSubvertical: state.candidateSubvertical || pickBotSubvertical(selectedBot, selectedOrganization),
        selectedPrimaryObjective: state.selectedPrimaryObjective || safeText(selectedBot.objective || selectedBot.goal, "agendar"),
      },
      basics: {
        businessName: state.businessName || safeText(selectedBot.business_name, safeText(selectedOrganization?.name, "Negocio WAOS")),
        botName: state.botName || safeText(selectedBot.name, "Asistente operativo"),
        tone: state.tone || pickBotTone(selectedBot),
        language: state.language || safeText(selectedBot.language, "es"),
        timezone: state.timezone || safeText(selectedBot.timezone, safeText(selectedOrganization?.timezone, "America/Mexico_City")),
        whatsappNumber: state.whatsappNumber || safeText(selectedBot.phone_number),
      },
    });
  }, [props.routeMode, props.verticals, selectedBot, selectedOrganization]);

  const loader = useRef(createLatestWizardReactiveSelectionLoader());
  useEffect(() => {
    if (!state.selectedOrganizationId || !state.candidateVerticalId) return;
    state.setPreviewLoading(true);
    loader.current.load({
      organizationId: state.selectedOrganizationId,
      verticalId: state.candidateVerticalId,
      subvertical: state.candidateSubvertical || state.selectedSubvertical,
      primaryObjective: state.selectedPrimaryObjective,
      mode: props.routeMode,
      botId: props.routeMode === "reconfigure" ? state.selectedBotId : undefined,
    }).then((result) => {
      if (!result) return;
      state.setBlueprint(result.blueprint);
      state.setVerticalProfile(result.verticalProfile);
      state.setPreviewError(result.errors.join(" "));
    }).catch((error) => {
      state.setPreviewError(error instanceof Error ? error.message : "No se pudo refrescar la preview del paso.");
    }).finally(() => state.setPreviewLoading(false));
    return () => loader.current.cancel();
  }, [
    props.routeMode,
    state.candidateSubvertical,
    state.candidateVerticalId,
    state.selectedBotId,
    state.selectedOrganizationId,
    state.selectedPrimaryObjective,
    state.selectedSubvertical,
  ]);

  const payloads = useMemo(() => buildWizardPayloads({
    mode: props.routeMode,
    selectedOrganizationId: state.selectedOrganizationId,
    selectedBotId: state.selectedBotId,
    selectedVerticalId: state.selectedVerticalId,
    selectedSubvertical: state.selectedSubvertical,
    selectedPrimaryObjective: state.selectedPrimaryObjective,
    selectedOrganization,
    businessName: state.businessName,
    botName: state.botName,
    tone: state.tone,
    language: state.language,
    timezone: state.timezone,
    hours: state.hours,
    whatsappNumber: state.whatsappNumber,
    servicesText: state.servicesText,
    featuredOffersText: state.featuredOffersText,
    pricingNotesText: state.pricingNotesText,
    primaryCtasText: state.primaryCtasText,
    faqText: state.faqText,
    policiesText: state.policiesText,
    knowledgeSourcesText: state.knowledgeSourcesText,
    selectedIntegrationKeys: state.selectedIntegrationKeys,
    integrationOptions: state.blueprint?.setup?.wizard?.recommended_integrations || [],
    escalateWhenText: state.escalateWhenText,
    handoffKeywordsText: state.handoffKeywordsText,
    handoffSlaText: state.handoffSlaText,
    humanDestinationChannelText: state.humanDestinationChannelText,
    canSayText: state.canSayText,
    cannotSayText: state.cannotSayText,
    ruleOverridesText: state.ruleOverridesText,
    selectedPlaybookKeys: state.selectedPlaybookKeys,
    recommendedPlaybooks: state.blueprint?.setup?.wizard?.recommended_playbooks || [],
    launchNotesText: state.launchNotesText,
    autopublishKnowledge: state.autopublishKnowledge,
  }), [props.routeMode, selectedOrganization, state]);

  const snapshot = state.dryRunResult?.validation_snapshot || state.wizard?.validation_snapshot || props.initialWizard?.validation_snapshot || null;
  const createState = {
    ...state,
    organizations: props.organizations,
    verticals: props.verticals,
    strongestVerticals: props.strongestVerticals,
    validationSnapshot: snapshot,
  };
  const reconfigureState = {
    bots: props.bots,
    selectedBot,
    blueprint: state.blueprint,
    validationSnapshot: snapshot,
    dryRunResult: state.dryRunResult,
    wizard: state.wizard,
  };
  const summary = buildBotStudioSummaryViewModel({
    routeMode: props.routeMode,
    routeStep: props.routeStep,
    selectedOrganization,
    selectedBot,
    organizations: props.organizations,
    verticals: props.verticals,
    selectedVerticalId: state.selectedVerticalId,
    selectedSubvertical: state.selectedSubvertical,
    selectedPrimaryObjective: state.selectedPrimaryObjective,
    selectedIntegrationKeys: state.selectedIntegrationKeys,
    selectedPlaybookKeys: state.selectedPlaybookKeys,
    servicesText: state.servicesText,
    wizard: state.wizard,
    wizardId: state.wizardId,
    blueprint: state.blueprint,
    snapshot,
    progress,
    businessName: state.businessName,
    botName: state.botName,
  } as any);

  return { createState, payloads, reconfigureState, selectedBot, selectedOrganization, snapshot, summary };
}
