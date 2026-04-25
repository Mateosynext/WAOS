import { buildStatePatchFromAiPrefill } from "../create/aiPrefillState";
import { autofixWizardWithAiRequest, generateWizardAiPrefillRequest, runWizardAiAutopilotRequest, saveWizardStepRequest, startWizardRequest } from "../services/wizardApi";
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
  CreateValidationActions,
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
  validate: { viewModel: CreateValidationViewModel; actions: CreateValidationActions };
  apply: { viewModel: CreateApplyViewModel };
};

export type ReconfigureWizardScreenModels = {
  select: { viewModel: ReconfigureSelectViewModel; actions: ReconfigureSelectActions };
  diff: { viewModel: ReconfigureDiffViewModel };
  dryRun: { viewModel: ReconfigureValidationViewModel };
  confirm: { viewModel: ReconfigureValidationViewModel };
};

type ScreenSlices = BotStudioWizardStateModel["slices"];

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function readString(record: Record<string, unknown>, key: string, fallback = "") {
  const value = String(record[key] || "").trim();
  return value || fallback;
}

function buildAiWizardStartPayload(result: { answers_patch?: Record<string, unknown> }, scope: ScreenSlices["scope"], payloads: BuildCreateArgs["payloads"]) {
  const answers = asRecord(result.answers_patch);
  const fit = asRecord(answers.vertical_fit);
  const basics = asRecord(answers.business_basics);
  return {
    organization_id: scope.selectedOrganizationId,
    bot_id: scope.selectedBotId || undefined,
    vertical_id: readString(fit, "vertical_id", String(payloads.scope.vertical_id || scope.selectedVerticalId || scope.candidateVerticalId || "")),
    subvertical: readString(fit, "subvertical", String(payloads.scope.subvertical || scope.selectedSubvertical || scope.candidateSubvertical || "")),
    business_name: readString(basics, "business_name", String(payloads.basics.business_name || "Negocio WAOS")),
    bot_name: readString(basics, "bot_name", String(payloads.basics.bot_name || "Asistente operativo WAOS")),
    tone: readString(basics, "tone", String(payloads.basics.tone || "amable")),
    language: readString(basics, "language", String(payloads.basics.language || "es")),
    timezone: readString(basics, "timezone", String(payloads.basics.timezone || "America/Mexico_City")),
    primary_objective: readString(fit, "primary_objective", String(payloads.scope.primary_objective || scope.selectedPrimaryObjective || "agendar")),
    hours: readString(basics, "hours", String(payloads.basics.hours || "")),
    whatsapp_number: readString(basics, "whatsapp_number", String(payloads.basics.whatsapp_number || "")),
    answers,
  };
}

type BuildCreateArgs = {
  patchState: BotStudioWizardStateModel["patchState"];
  payloads: { scope: Record<string, unknown>; basics: Record<string, unknown>; catalog: Record<string, unknown>; knowledge: Record<string, unknown>; integrations: Record<string, unknown>; launchReview: Record<string, unknown> };
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
  const { props, actions, patchState, payloads, scope, basics, catalog, knowledge, integrations, launch, preview, wizardRuntime, snapshot, normalizeObjectiveValue } = args;

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
        generateAiPrefill: (input) => generateWizardAiPrefillRequest({
          organizationId: scope.selectedOrganizationId,
          botId: scope.selectedBotId || null,
          verticalId: scope.selectedVerticalId || scope.candidateVerticalId || null,
          subvertical: scope.selectedSubvertical || scope.candidateSubvertical || null,
          primaryObjective: scope.selectedPrimaryObjective,
          userDescription: input.userDescription,
          intensity: input.intensity,
          existingAnswers: {
            vertical_fit: payloads.scope,
            business_basics: payloads.basics,
            catalog_offer: payloads.catalog,
            knowledge_seed: payloads.knowledge,
            integrations_rules: payloads.integrations,
            launch_review: payloads.launchReview,
          },
        }),
        runAiAutopilot: async (input) => {
          actions.wizardRuntime.setWizardError("");
          actions.autosave.setAutosaveState("saving");
          try {
            const result = await runWizardAiAutopilotRequest({
              organizationId: scope.selectedOrganizationId,
              botId: scope.selectedBotId || null,
              verticalId: scope.selectedVerticalId || scope.candidateVerticalId || null,
              subvertical: scope.selectedSubvertical || scope.candidateSubvertical || null,
              primaryObjective: scope.selectedPrimaryObjective,
              userDescription: input.userDescription,
              intensity: input.intensity || "savage",
              maxAutofixRounds: 2,
              autoApply: false,
              existingAnswers: {
                vertical_fit: payloads.scope,
                business_basics: payloads.basics,
                catalog_offer: payloads.catalog,
                knowledge_seed: payloads.knowledge,
                integrations_rules: payloads.integrations,
                launch_review: payloads.launchReview,
              },
            });
            patchState(buildStatePatchFromAiPrefill(result));
            const dryRunResult = asRecord(result.dry_run_result);
            const nextWizard = asRecord(dryRunResult.wizard || result.wizard);
            if (Object.keys(nextWizard).length) {
              actions.wizardRuntime.setWizard(nextWizard as ScreenSlices["wizardRuntime"]["wizard"]);
              actions.wizardRuntime.setWizardId(String(nextWizard.id || result.wizard_id || ""));
              const validation = asRecord(asRecord(nextWizard.answers).dry_run_validation);
              const validatedRevision = Number(validation.wizard_revision || nextWizard.wizard_revision || 0);
              if (Number.isFinite(validatedRevision) && validatedRevision > 0) {
                actions.wizardRuntime.setValidatedWizardRevision(validatedRevision);
              }
            }
            if (Object.keys(dryRunResult).length) {
              actions.wizardRuntime.setDryRunResult(dryRunResult as ScreenSlices["wizardRuntime"]["dryRunResult"]);
            }
            actions.autosave.setAutosaveState("saved");
            actions.autosave.setAutosaveError("");
            actions.autosave.setLastSavedAt(new Date().toISOString());
            return result;
          } catch (error) {
            const message = error instanceof Error ? error.message : "No se pudo correr AI Autopilot end-to-end.";
            actions.autosave.setAutosaveState("error");
            actions.autosave.setAutosaveError(message);
            actions.wizardRuntime.setWizardError(message);
            throw error;
          }
        },
        applyAiPrefill: async (result) => {
          const answers = asRecord(result.answers_patch);
          patchState(buildStatePatchFromAiPrefill(result));
          actions.wizardRuntime.setWizardError("");
          actions.autosave.setAutosaveState("saving");
          try {
            let current = await startWizardRequest(buildAiWizardStartPayload(result, scope, payloads));
            for (const stepKey of ["vertical_fit", "business_basics", "catalog_offer", "knowledge_seed", "integrations_rules", "launch_review"]) {
              const payload = asRecord(answers[stepKey]);
              if (!Object.keys(payload).length) continue;
              current = await saveWizardStepRequest(String(current.id || ""), stepKey, payload, { expectedRevision: current.wizard_revision ?? null });
            }
            actions.wizardRuntime.setWizard(current);
            actions.wizardRuntime.setWizardId(String(current.id || ""));
            actions.wizardRuntime.setDryRunResult(null);
            actions.wizardRuntime.setValidatedWizardRevision(null);
            actions.autosave.setAutosaveState("saved");
            actions.autosave.setAutosaveError("");
            actions.autosave.setLastSavedAt(String(current.updated_at || new Date().toISOString()));
          } catch (error) {
            const message = error instanceof Error ? error.message : "No se pudo guardar el setup generado por IA.";
            actions.autosave.setAutosaveState("error");
            actions.autosave.setAutosaveError(message);
            actions.wizardRuntime.setWizardError(message);
            throw error;
          }
        },
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
    validate: { viewModel: { validationSnapshot: snapshot, wizard: wizardRuntime.wizard, dryRunResult: wizardRuntime.dryRunResult }, actions: { autofixWithAi: async () => { if (!wizardRuntime.wizardId) throw new Error("Guarda el wizard antes de usar autofix con IA."); const result = await autofixWizardWithAiRequest(wizardRuntime.wizardId); const dryRunResult = (result.dry_run_result || result) as ScreenSlices["wizardRuntime"]["dryRunResult"]; if (dryRunResult) actions.wizardRuntime.setDryRunResult(dryRunResult); const nextWizard = (result.wizard || (dryRunResult && dryRunResult.wizard) || null) as ScreenSlices["wizardRuntime"]["wizard"]; if (nextWizard) { actions.wizardRuntime.setWizard(nextWizard); actions.wizardRuntime.setWizardId(String(nextWizard.id || wizardRuntime.wizardId)); } return result; } } },
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
