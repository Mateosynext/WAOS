"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import SuccessState from "../components/SuccessState";
import { UiMessage } from "../components/UiMessage";
import { normalizeBot, normalizeReleaseRequest, type BotContract, type ReleaseRequestContract, type SessionOrganization, type VerticalProfileContract } from "../lib/contracts";
import { safeText } from "../lib/ui";
import SubverticalPicker from "./SubverticalPicker";
import VerticalPicker from "./VerticalPicker";
import { useBotStudioWizardState } from "./useBotStudioWizardState";
import { buildWizardPayloads } from "./wizardPayloadBuilders";
import { createLatestWizardReactiveSelectionLoader } from "./wizardReactiveData";
import { applyWizardRequest, dryRunWizardRequest, getWizardRequest, saveWizardStepRequest, startWizardRequest } from "./wizardApi";
import { DiffCard, HandoffPreviewCard, OperationalDiffDomainCard, PackPreviewBlock, StickySummaryRail, ValidationSnapshotPanel, VerticalScorecardPanel } from "./wizardReviewSections";
import WizardDiagnosticsPanel from "./wizardDiagnosticsPanel";
import { getCreateAutosaveStepKeys, resolveWizardInitialStep, type WizardUiActiveStep as ActiveStep } from "./wizardStepFlow";
import { deriveWizardConsistencyRecovery, fingerprintWizardValue, readWizardAutosaveMetrics, readWizardTimelineEvents, recordWizardAutosaveMetric, recordWizardTimelineEvent, WIZARD_ENTERPRISE_FLAGS } from "./wizardEnterpriseGuards";
import type {
  WizardApplyResult,
  WizardBlueprint,
  WizardInstance,
  WizardMode,
  WizardDryRunResult,
  WizardHandoffPreview,
  WizardRecommendedCta,
  WizardRecommendedIntegration,
  WizardRecommendedPlaybook,
  WizardSubverticalProfile,
  WizardSubverticalTemplate,
  WizardValidationSnapshot,
} from "./wizard-types";

type Props = {
  organizations: SessionOrganization[];
  verticals: VerticalProfileContract[];
  strongestVerticals: VerticalProfileContract[];
  bots: BotContract[];
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

type ObjectiveValue = "agendar" | "vender" | "calificar" | "responder" | "reactivar";
type NextBestActionKey = "connect_channel" | "run_simulation" | "publish_release" | "open_inbox";

type NextBestAction = {
  key: NextBestActionKey;
  title: string;
  description: string;
  ctaLabel: string;
  href?: string;
};

type CompletionPath = "wizard" | "module";

const OBJECTIVES: ObjectiveValue[] = ["agendar", "vender", "calificar", "responder", "reactivar"];

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function normalizeName(value: string) {
  return value.trim().toLowerCase();
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? { ...(value as Record<string, unknown>) } : {};
}

function normalizeObjective(value: unknown): ObjectiveValue {
  const normalized = String(value || "").trim().toLowerCase();
  return OBJECTIVES.includes(normalized as ObjectiveValue) ? (normalized as ObjectiveValue) : "agendar";
}

function objectiveLabel(value: string) {
  switch (normalizeObjective(value)) {
    case "agendar": return "Agendar";
    case "vender": return "Vender";
    case "calificar": return "Calificar";
    case "responder": return "Responder";
    case "reactivar": return "Reactivar";
    default: return "Agendar";
  }
}

function readNestedString(value: unknown, path: string[], fallback = "") {
  let current: unknown = value;
  for (const key of path) current = asRecord(current)[key];
  const result = String(current || "").trim();
  return result || fallback;
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

function parseTextBlock(value: string) {
  return unique(value.split(/\r?\n/).map((item) => item.trim()));
}

function textBlockFromFaqs(items: Array<{ q?: string; a?: string }>) {
  return items
    .map((item) => {
      const q = String(item.q || "").trim();
      const a = String(item.a || "").trim();
      return q && a ? `${q} | ${a}` : "";
    })
    .filter(Boolean)
    .join("\n");
}

function parseFaqBlock(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [question, ...rest] = line.split("|");
      return {
        q: String(question || "").trim(),
        a: rest.join("|").trim(),
      };
    })
    .filter((item) => item.q && item.a);
}

function parseJsonObject(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return {};
  try {
    const parsed = JSON.parse(trimmed);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}


function stringifyJsonBlock(value: unknown) {
  const record = asRecord(value);
  return Object.keys(record).length ? JSON.stringify(record, null, 2) : "{}";
}

function summarizeRuleOverrides(value: unknown) {
  const record = asRecord(value);
  if (!Object.keys(record).length) return "Sin overrides visibles";
  const canSay = Array.isArray(record.can_say) ? (record.can_say as unknown[]).filter((item) => String(item || "").trim()).length : 0;
  const cannotSay = Array.isArray(record.cannot_say) ? (record.cannot_say as unknown[]).filter((item) => String(item || "").trim()).length : 0;
  const extraKeys = Object.keys(record).filter((key) => !["can_say", "cannot_say"].includes(key));
  return unique([
    `${Object.keys(record).length} reglas override`,
    canSay ? `puede decir ${canSay}` : "",
    cannotSay ? `no puede decir ${cannotSay}` : "",
    extraKeys.length ? `extras: ${extraKeys.slice(0, 3).join(", ")}` : "",
  ]).join(" · ");
}

function integrationIdentity(item: Partial<WizardRecommendedIntegration> | string) {
  if (typeof item === "string") return item;
  return String(item.provider || item.integration_key || item.name || "").trim();
}

function pickCatalogSubvertical(profile?: { selected_subvertical?: { name?: string }; recommended_subverticals?: string[]; subvertical_profiles?: Array<{ name?: string }>; subverticals?: string[] } | null) {
  return profile?.selected_subvertical?.name
    || profile?.recommended_subverticals?.[0]
    || profile?.subvertical_profiles?.[0]?.name
    || profile?.subverticals?.[0]
    || "";
}

function pickBotSubvertical(bot?: BotContract | null, organization?: SessionOrganization | null) {
  const draft = asRecord(bot?.config_draft);
  return String(draft.selected_subvertical || draft.subvertical || organization?.subvertical || "").trim();
}

function pickBotTone(bot?: BotContract | null) {
  return readNestedString(bot?.config_draft, ["personality", "tone"], safeText(bot?.tone, "Sin tono visible"));
}

function pickBotServices(bot?: BotContract | null) {
  return readNestedStrings(bot?.config_draft, ["business_knowledge", "services"]);
}

function pickBotPolicies(bot?: BotContract | null) {
  return readNestedStrings(bot?.config_draft, ["business_knowledge", "policies"]);
}

function pickBotFaqLabels(bot?: BotContract | null) {
  return unique(readFaqItems(asRecord(asRecord(bot?.config_draft).business_knowledge).faqs).map((item) => item.q));
}

function pickBotKnowledgeSourceLabels(bot?: BotContract | null) {
  const sources = asRecord(bot?.config_draft).knowledge_sources;
  return unique(Array.isArray(sources) ? sources.map((item) => {
    const record = asRecord(item);
    return String(record.label || record.connector_key || record.provider || item || "").trim();
  }) : []);
}

function pickBotIntegrationKeys(bot?: BotContract | null) {
  return unique(Object.keys(asRecord(asRecord(bot?.config_draft).integrations)));
}

function pickBotTemplateLabels(bot?: BotContract | null) {
  const draft = asRecord(bot?.config_draft);
  const templateArrays = [
    ...(Array.isArray(draft.response_templates) ? draft.response_templates : []),
    ...(Array.isArray(draft.templates) ? draft.templates : []),
    ...(Array.isArray(asRecord(draft.pipeline).templates) ? asRecord(draft.pipeline).templates as unknown[] : []),
  ];
  return unique(templateArrays.map((item) => {
    const record = asRecord(item);
    return String(record.title || record.template_key || record.key || record.name || "").trim();
  }));
}

function summarize(values: Array<string | null | undefined>, fallback: string, limit = 4) {
  const cleaned = unique(values).slice(0, limit);
  return cleaned.length ? cleaned.join(" · ") : fallback;
}

function overlapValues(nextValues: Array<string | null | undefined>, currentValues: Array<string | null | undefined>) {
  const currentSet = new Set(unique(currentValues).map(normalizeName));
  return unique(nextValues).filter((item) => currentSet.has(normalizeName(item)));
}

function freshValues(nextValues: Array<string | null | undefined>, currentValues: Array<string | null | undefined>) {
  const currentSet = new Set(unique(currentValues).map(normalizeName));
  return unique(nextValues).filter((item) => !currentSet.has(normalizeName(item)));
}

function integrationLabel(value: string) {
  return value
    .replace(/[_-]+/g, " ")
    .split(" ")
    .map((chunk) => chunk ? `${chunk[0].toUpperCase()}${chunk.slice(1)}` : "")
    .join(" ");
}

function buildSubverticalProfiles(verticalProfile: VerticalProfileContract | null, blueprint: WizardBlueprint | null, catalogVertical: VerticalProfileContract | null): WizardSubverticalProfile[] {
  if (verticalProfile?.subvertical_profiles?.length) return verticalProfile.subvertical_profiles as WizardSubverticalProfile[];
  if (catalogVertical?.subvertical_profiles?.length) return catalogVertical.subvertical_profiles as WizardSubverticalProfile[];
  return unique([
    blueprint?.selected_subvertical?.name,
    blueprint?.setup?.wizard?.selected_subvertical,
    ...(blueprint?.profile?.recommended_subverticals || []),
    ...(blueprint?.profile?.subverticals || []),
    pickCatalogSubvertical(catalogVertical),
    ...(catalogVertical?.recommended_subverticals || []),
    ...(catalogVertical?.subvertical_profiles || []).map((item) => item.name),
    ...(catalogVertical?.subverticals || []),
  ]).map((name) => ({ id: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"), name } as WizardSubverticalProfile));
}

async function requestApiJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", credentials: "same-origin", ...init });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof payload?.detail === "string" ? payload.detail : `La solicitud falló (${response.status}).`);
  }
  return payload as T;
}


function parseTimestamp(value: unknown) {
  const rendered = String(value || "").trim();
  if (!rendered) return null;
  const parsed = Date.parse(rendered);
  return Number.isFinite(parsed) ? parsed : null;
}

function happenedAfter(value: unknown, reference: unknown) {
  const valueTs = parseTimestamp(value);
  if (valueTs === null) return false;
  const referenceTs = parseTimestamp(reference);
  return referenceTs === null ? true : valueTs >= referenceTs;
}

function hasConnectedOperationalChannel(bot: BotContract | null | undefined) {
  if (!bot) return false;
  const connectionStatus = String(bot.connection_status || "").trim().toLowerCase();
  if (["connected", "active", "ready", "live", "verified", "ok"].includes(connectionStatus)) return true;
  if (String(bot.phone_number || "").trim() || String(bot.phone_number_id || "").trim()) return true;
  if (String(bot.primary_channel || "").trim()) return true;

  const configDraft = asRecord(bot.config_draft);
  const integrations = asRecord(configDraft.integrations);
  const channels = Array.isArray(configDraft.channels) ? configDraft.channels : [];
  if (channels.length) return true;

  return Object.entries(integrations).some(([key, value]) => {
    const record = asRecord(value);
    const rendered = `${key} ${String(record.provider || "")} ${String(record.status || "")} ${String(record.channel || "")}`.toLowerCase();
    const channelLike = /(whatsapp|instagram|telegram|webchat|email|voice|sms|messenger|twilio)/.test(rendered);
    if (!channelLike) return false;
    const status = String(record.status || "").toLowerCase();
    return ["connected", "active", "ready", "live", "verified", "ok"].includes(status);
  });
}

function botIsReadyToOperate(bot: BotContract | null | undefined) {
  if (!bot) return false;
  const statusSignals = [bot.status, bot.current_state, bot.connection_status, bot.published_version_id]
    .map((item) => String(item || "").trim().toLowerCase())
    .filter(Boolean);
  return statusSignals.some((value) => ["published", "live", "active", "ready", "operating", "released", "connected"].includes(value));
}

function recountValidationItems(items: Array<{ status?: string }>) {
  return items.reduce((acc, item) => {
    const status = String(item.status || "").trim().toLowerCase();
    if (status === "green" || status === "yellow" || status === "red") acc[status] += 1;
    return acc;
  }, { green: 0, yellow: 0, red: 0 });
}

function buildClientValidationSnapshot(
  base: WizardValidationSnapshot | null | undefined,
  context: {
    hasConnectedChannel: boolean;
    hasSimulationAfterApply: boolean;
    hasApprovedSimulationAfterApply: boolean;
    latestSimulationAfterApply: Record<string, unknown> | null;
    hasReleaseRequestAfterApply: boolean;
    hasPublishedReleaseAfterApply: boolean;
    nextBestAction: NextBestAction | null;
    applyReady: boolean;
  },
): WizardValidationSnapshot | null {
  if (!base) return null;
  const checklist = (base.checklist || []).map((item) => ({ ...item }));
  const updateItem = (key: string, next: { status: "green" | "yellow" | "red"; detail: string }) => {
    const index = checklist.findIndex((item) => item.key === key);
    if (index >= 0) checklist[index] = { ...checklist[index], ...next };
  };
  updateItem("primary_channel_defined", {
    status: context.hasConnectedChannel ? "green" : "yellow",
    detail: context.hasConnectedChannel
      ? "Ya se detecta un canal operativo conectado."
      : "El canal principal sigue pendiente de conexión operativa.",
  });
  updateItem("basic_simulation", {
    status: context.hasApprovedSimulationAfterApply ? "green" : context.hasSimulationAfterApply ? "yellow" : "red",
    detail: context.hasApprovedSimulationAfterApply
      ? "La simulación básica ya quedó aprobada después del apply actual."
      : context.hasSimulationAfterApply
        ? "Ya hay simulación posterior al apply, pero todavía no alcanza una aprobación clara."
        : "Todavía no existe una simulación básica aprobada después del apply actual.",
  });
  updateItem("release_ready", {
    status: context.hasPublishedReleaseAfterApply ? "green" : context.hasApprovedSimulationAfterApply && context.hasConnectedChannel ? "yellow" : context.hasReleaseRequestAfterApply ? "yellow" : "red",
    detail: context.hasPublishedReleaseAfterApply
      ? "Este cambio ya quedó publicado y puede operar en vivo."
      : context.hasApprovedSimulationAfterApply && context.hasConnectedChannel
        ? "El cambio ya está listo para publicar, pero todavía no sale a producción."
        : context.hasReleaseRequestAfterApply
          ? "Ya existe un release posterior al apply, pero todavía no llega a publicación."
          : "Todavía no está listo para publicar este cambio con seguridad.",
  });
  const blockingRed = checklist.some((item) => item.blocking !== false && item.status === "red");
  const gateStatus: "green" | "yellow" | "red" = context.hasPublishedReleaseAfterApply && context.hasConnectedChannel && context.hasApprovedSimulationAfterApply && !blockingRed
    ? "green"
    : blockingRed || !context.applyReady
      ? "red"
      : "yellow";
  const latestSummary = asRecord(context.latestSimulationAfterApply?.summary);
  return {
    ...base,
    checklist,
    counts: recountValidationItems(checklist),
    gate: {
      status: gateStatus,
      label: gateStatus === "green" ? "Listo para operar" : gateStatus === "yellow" ? "Salida parcial o pendiente" : "Bloqueado para salida",
      detail: gateStatus === "green"
        ? "El cambio ya tiene canal, simulación aprobada y release suficiente para operar."
        : gateStatus === "yellow"
          ? "La salida está avanzada, pero todavía falta completar la siguiente acción operativa."
          : "La checklist todavía tiene bloqueos importantes antes de operar.",
    },
    simulation_result: context.latestSimulationAfterApply
      ? {
          status: context.hasApprovedSimulationAfterApply ? "approved" : context.hasSimulationAfterApply ? "needs_review" : "pending",
          approved: context.hasApprovedSimulationAfterApply,
          pass_rate: Number(latestSummary.pass_rate || 0),
          cases_total: Number(latestSummary.cases_total || 0),
          created_at: String(context.latestSimulationAfterApply.created_at || "") || undefined,
          compare_target: String(latestSummary.compare_target || "") || undefined,
          run_id: String(context.latestSimulationAfterApply.id || "") || undefined,
        }
      : base.simulation_result,
    next_cta: context.nextBestAction
      ? {
          key: context.nextBestAction.key,
          title: context.nextBestAction.title,
          description: context.nextBestAction.description,
          cta_label: context.nextBestAction.ctaLabel,
          href: context.nextBestAction.href,
        }
      : base.next_cta,
  };
}

function reviewReadyForCreate(values: {
  businessName: string;
  botName: string;
  selectedVerticalId: string;
  selectedSubvertical: string;
  servicesText: string;
  faqText: string;
  integrationKeys: string[];
}) {
  return Boolean(
    values.businessName.trim()
    && values.botName.trim()
    && values.selectedVerticalId
    && values.selectedSubvertical
    && parseTextBlock(values.servicesText).length
    && parseFaqBlock(values.faqText).length
    && values.integrationKeys.length,
  );
}

function ModeCard({
  active,
  title,
  description,
  onClick,
}: {
  active: boolean;
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-[24px] border p-5 text-left transition ${active
        ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] shadow-[var(--shadow-sm)]"
        : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] hover:border-[color:var(--accent-border)] hover:bg-[color:var(--surface-elevated)]"}`}
    >
      <div className="text-base font-semibold text-[color:var(--text-primary)]">{title}</div>
      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
    </button>
  );
}

function StepBadge({ active, done, label }: { active?: boolean; done?: boolean; label: string }) {
  return (
    <div className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${active
      ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] text-[color:var(--text-primary)]"
      : done
        ? "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success-text)]"
        : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-secondary)]"}`}
    >
      {label}
    </div>
  );
}

function progressStatusMeta(status: "done" | "active" | "pending") {
  switch (status) {
    case "done":
      return { pill: "listo", tone: "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success-text)]" };
    case "active":
      return { pill: "siguiente", tone: "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] text-[color:var(--text-primary)]" };
    default:
      return { pill: "pendiente", tone: "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-secondary)]" };
  }
}

function CheckboxPill({
  checked,
  label,
  secondary,
  onClick,
  onChange,
}: {
  checked: boolean;
  label: string;
  secondary?: string;
  onClick?: () => void;
  onChange?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick || onChange}
      className={`rounded-[20px] border p-4 text-left transition ${checked
        ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)]"
        : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] hover:border-[color:var(--accent-border)] hover:bg-[color:var(--surface-elevated)]"}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-[color:var(--text-primary)]">{label}</div>
          {secondary ? <div className="mt-1 text-xs leading-5 text-[color:var(--text-secondary)]">{secondary}</div> : null}
        </div>
        <input type="checkbox" checked={checked} readOnly />
      </div>
    </button>
  );
}

export default function BotStudioWizardClient({
  organizations,
  verticals,
  strongestVerticals,
  bots,
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
}: Props) {
  const router = useRouter();
  const organizationsById = useMemo(() => Object.fromEntries(organizations.map((item) => [item.id, item])), [organizations]);
  const botsById = useMemo(() => Object.fromEntries(bots.map((item) => [item.id, item])), [bots]);

  const {
    mode,
    setMode,
    selectedBotId,
    setSelectedBotId,
    selectedOrganizationId,
    setSelectedOrganizationId,
    selectedVerticalId,
    setSelectedVerticalId,
    selectedSubvertical,
    setSelectedSubvertical,
    candidateVerticalId,
    setCandidateVerticalId,
    candidateSubvertical,
    setCandidateSubvertical,
    selectedPrimaryObjective,
    setSelectedPrimaryObjective,
    activeStep,
    setActiveStep,
    businessName,
    setBusinessName,
    botName,
    setBotName,
    tone,
    setTone,
    language,
    setLanguage,
    timezone,
    setTimezone,
    hours,
    setHours,
    whatsappNumber,
    setWhatsappNumber,
    servicesText,
    setServicesText,
    featuredOffersText,
    setFeaturedOffersText,
    primaryCtasText,
    setPrimaryCtasText,
    pricingNotesText,
    setPricingNotesText,
    faqText,
    setFaqText,
    policiesText,
    setPoliciesText,
    knowledgeSourcesText,
    setKnowledgeSourcesText,
    selectedIntegrationKeys,
    setSelectedIntegrationKeys,
    escalateWhenText,
    setEscalateWhenText,
    handoffKeywordsText,
    setHandoffKeywordsText,
    handoffSlaText,
    setHandoffSlaText,
    humanDestinationChannelText,
    setHumanDestinationChannelText,
    canSayText,
    setCanSayText,
    cannotSayText,
    setCannotSayText,
    ruleOverridesText,
    setRuleOverridesText,
    launchNotesText,
    setLaunchNotesText,
    selectedPlaybookKeys,
    setSelectedPlaybookKeys,
    autopublishKnowledge,
    setAutopublishKnowledge,
    simulationTitle,
    setSimulationTitle,
    simulationScenario,
    setSimulationScenario,
    simulationExpectedAction,
    setSimulationExpectedAction,
    simulationResult,
    setSimulationResult,
    simulationRunning,
    setSimulationRunning,
    simulationError,
    setSimulationError,
    blueprint,
    setBlueprint,
    verticalProfile,
    setVerticalProfile,
    previewLoading,
    setPreviewLoading,
    previewError,
    setPreviewError,
    wizardId,
    setWizardId,
    wizard,
    setWizard,
    working,
    setWorking,
    wizardError,
    setWizardError,
    applyResult,
    setApplyResult,
    dryRunResult,
    setDryRunResult,
    reviewConfirmed,
    setReviewConfirmed,
    postApplyBot,
    setPostApplyBot,
    postApplyReleases,
    setPostApplyReleases,
    postApplySimulationRuns,
    setPostApplySimulationRuns,
    postApplyLoading,
    setPostApplyLoading,
    postApplyError,
    setPostApplyError,
    postApplyPath,
    setPostApplyPath,
    autosaveState,
    setAutosaveState,
    autosaveError,
    setAutosaveError,
    lastSavedAt,
    setLastSavedAt,
    patchState,
  } = useBotStudioWizardState({
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
  });
  const autosaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reactiveSelectionLoader = useMemo(() => createLatestWizardReactiveSelectionLoader(), []);
  const lastAutosavedPayloadsRef = useRef<Record<string, string>>({});
  const wizardRef = useRef<WizardInstance | null>(initialWizard || null);
  const saveQueueRef = useRef<Promise<WizardInstance | null>>(Promise.resolve(initialWizard || null));
  const autosaveRunRef = useRef(0);
  const lastRecoverySignatureRef = useRef("");
  const lastIntegrityRefreshSignatureRef = useRef("");
  const [diagnosticsVersion, setDiagnosticsVersion] = useState(0);
  const [diagnosticCopyFeedback, setDiagnosticCopyFeedback] = useState("");

  const postApplyBotId = String(applyResult?.wizard?.bot_id || (wizard?.status === "applied" ? wizard?.bot_id || "" : ""));
  const postApplyAppliedAt = String(applyResult?.wizard?.applied_at || wizard?.applied_at || "");

  const selectedOrganization = selectedOrganizationId ? organizationsById[selectedOrganizationId] || null : null;
  const selectedBot = selectedBotId ? botsById[selectedBotId] || null : null;
  const previewVerticalId = candidateVerticalId || selectedVerticalId;
  const previewSubvertical = candidateSubvertical || (previewVerticalId === selectedVerticalId ? selectedSubvertical : "");
  const previewCatalogVertical = verticals.find((item) => item.id === previewVerticalId) || null;
  const catalogVertical = verticals.find((item) => item.id === selectedVerticalId) || previewCatalogVertical || null;
  const subverticalProfiles = useMemo(() => buildSubverticalProfiles(verticalProfile, blueprint, previewCatalogVertical), [verticalProfile, blueprint, previewCatalogVertical]);
  const selectedSubverticalProfile = useMemo(() => {
    const normalized = normalizeName(previewSubvertical);
    if (!normalized) return null;
    return subverticalProfiles.find((item) => normalizeName(safeText(item.name)) === normalized) || null;
  }, [previewSubvertical, subverticalProfiles]);

  const currentBotTone = pickBotTone(selectedBot);
  const currentBotServices = pickBotServices(selectedBot);
  const currentBotPolicies = pickBotPolicies(selectedBot);
  const currentBotFaqs = pickBotFaqLabels(selectedBot);
  const currentBotKnowledgeSources = pickBotKnowledgeSourceLabels(selectedBot);
  const currentBotIntegrations = pickBotIntegrationKeys(selectedBot);
  const currentBotTemplates = pickBotTemplateLabels(selectedBot);
  const currentBotObjective = safeText(selectedBot?.objective || selectedBot?.goal, "Sin objetivo visible");
  const currentBotSubvertical = pickBotSubvertical(selectedBot, selectedOrganization);

  const recommendedIntegrations = unique((blueprint?.setup?.wizard?.recommended_integrations || []).map(integrationIdentity));
  const integrationOptions = blueprint?.setup?.wizard?.recommended_integrations || [];
  const integrationOptionLabels = new Map(integrationOptions.map((item) => [integrationIdentity(item), safeText(item.name, safeText(item.provider || item.integration_key || item.name, integrationIdentity(item)))]));
  const recommendedPlaybooks = blueprint?.setup?.wizard?.recommended_playbooks || [];
  const recommendedCtas = blueprint?.setup?.wizard?.recommended_ctas || [];
  const wizardTelemetryContext = useMemo(() => ({
    mode,
    organizationId: selectedOrganizationId,
    botId: selectedBotId,
    wizardId,
    verticalId: selectedVerticalId,
    subvertical: selectedSubvertical,
  }), [mode, selectedOrganizationId, selectedBotId, wizardId, selectedVerticalId, selectedSubvertical]);

  function getWizardTelemetryStorage() {
    return typeof window !== "undefined" ? window.sessionStorage : null;
  }

  function recordTimeline(type: string, payload: Record<string, unknown> = {}) {
    if (!WIZARD_ENTERPRISE_FLAGS.enabled || !WIZARD_ENTERPRISE_FLAGS.telemetryEnabled) return;
    recordWizardTimelineEvent(getWizardTelemetryStorage(), wizardTelemetryContext, { type, payload });
    setDiagnosticsVersion((value) => value + 1);
  }

  function recordAutosaveBatchMetric(result: "success" | "error" | "ignored" | "skipped", durationMs: number, stepCount: number) {
    if (!WIZARD_ENTERPRISE_FLAGS.enabled || !WIZARD_ENTERPRISE_FLAGS.telemetryEnabled) return;
    recordWizardAutosaveMetric(getWizardTelemetryStorage(), wizardTelemetryContext, { result, durationMs, stepCount });
    setDiagnosticsVersion((value) => value + 1);
  }

  function getStepPayloadFingerprint(payload: Record<string, unknown> | null | undefined) {
    return fingerprintWizardValue(payload || {});
  }

  function getWizardStepRunPayloadFingerprint(instance: WizardInstance | null | undefined, stepKey: string) {
    const stepRun = (instance?.step_runs || []).find((item) => item.step_key === stepKey);
    return stepRun?.payload ? getStepPayloadFingerprint(stepRun.payload) : null;
  }

  function refreshVisibleDiagnostics() {
    setDiagnosticsVersion((value) => value + 1);
  }

  const wizardPayloads = useMemo(() => buildWizardPayloads({
    mode,
    selectedOrganizationId,
    selectedBotId,
    selectedVerticalId,
    selectedSubvertical,
    selectedPrimaryObjective,
    selectedOrganization,
    businessName,
    botName,
    tone,
    language,
    timezone,
    hours,
    whatsappNumber,
    servicesText,
    featuredOffersText,
    pricingNotesText,
    primaryCtasText,
    faqText,
    policiesText,
    knowledgeSourcesText,
    selectedIntegrationKeys,
    integrationOptions,
    escalateWhenText,
    handoffKeywordsText,
    handoffSlaText,
    humanDestinationChannelText,
    canSayText,
    cannotSayText,
    ruleOverridesText,
    selectedPlaybookKeys,
    recommendedPlaybooks,
    launchNotesText,
    autopublishKnowledge,
  }), [
    mode,
    selectedOrganizationId,
    selectedBotId,
    selectedVerticalId,
    selectedSubvertical,
    selectedPrimaryObjective,
    selectedOrganization,
    businessName,
    botName,
    tone,
    language,
    timezone,
    hours,
    whatsappNumber,
    servicesText,
    featuredOffersText,
    pricingNotesText,
    primaryCtasText,
    faqText,
    policiesText,
    knowledgeSourcesText,
    selectedIntegrationKeys,
    integrationOptions,
    escalateWhenText,
    handoffKeywordsText,
    handoffSlaText,
    humanDestinationChannelText,
    canSayText,
    cannotSayText,
    ruleOverridesText,
    selectedPlaybookKeys,
    recommendedPlaybooks,
    launchNotesText,
    autopublishKnowledge,
  ]);

  const requiredWizardStepPayloads = useMemo(() => ([
    ["vertical_fit", wizardPayloads.scope],
    ["business_basics", wizardPayloads.basics],
  ] as const), [wizardPayloads.basics, wizardPayloads.scope]);

  const fullWizardStepPayloads = useMemo(() => ([
    ...requiredWizardStepPayloads,
    ["catalog_offer", wizardPayloads.catalog],
    ["knowledge_seed", wizardPayloads.knowledge],
    ["integrations_rules", wizardPayloads.integrations],
    ["launch_review", wizardPayloads.launchReview],
  ] as const), [requiredWizardStepPayloads, wizardPayloads.catalog, wizardPayloads.integrations, wizardPayloads.knowledge, wizardPayloads.launchReview]);
  const clientTimelineEvents = useMemo(
    () => readWizardTimelineEvents(getWizardTelemetryStorage(), wizardTelemetryContext),
    [diagnosticsVersion, wizardTelemetryContext],
  );
  const clientAutosaveMetrics = useMemo(
    () => readWizardAutosaveMetrics(getWizardTelemetryStorage(), wizardTelemetryContext),
    [diagnosticsVersion, wizardTelemetryContext],
  );
  const wizardPayloadFingerprints = useMemo(
    () => Object.fromEntries(fullWizardStepPayloads.map(([stepKey, payload]) => [stepKey, getStepPayloadFingerprint(payload as Record<string, unknown>)])),
    [fullWizardStepPayloads],
  );
  const dirtyWizardSteps = useMemo(
    () => fullWizardStepPayloads
      .map(([stepKey]) => {
        const clientFingerprint = wizardPayloadFingerprints[stepKey];
        const serverFingerprint = getWizardStepRunPayloadFingerprint(wizard, stepKey);
        return { stepKey, clientFingerprint, serverFingerprint };
      })
      .filter((item) => item.serverFingerprint !== null && item.serverFingerprint !== item.clientFingerprint),
    [fullWizardStepPayloads, wizard, wizardPayloadFingerprints],
  );
  const nextTemplates = useMemo(() => unique([
    ...((blueprint?.setup?.response_templates || []) as Array<Record<string, unknown>>).map((item) => String(item.title || item.template_key || item.key || item.name || "").trim()),
    ...((selectedSubverticalProfile?.templates || []).map((item: WizardSubverticalTemplate) => String(item.title || item.template_key || item.key || item.name || "").trim())),
  ]), [blueprint, selectedSubverticalProfile]);
  const nextServices = unique([
    ...((blueprint?.setup?.services || []).map((item) => String(item || "").trim())),
    ...((selectedSubverticalProfile?.service_bundle || []).map((item: string) => String(item || "").trim())),
    ...parseTextBlock(servicesText),
  ]);
  const nextPolicies = unique([
    ...(((blueprint?.setup?.business_knowledge?.policies || []) as string[]).map((item) => String(item || "").trim())),
    ...(((blueprint?.setup?.wizard?.policies || []) as string[]).map((item) => String(item || "").trim())),
    ...parseTextBlock(policiesText),
  ]);
  const nextTone = tone || readNestedString(blueprint?.setup, ["personality", "tone"], safeText(catalogVertical?.short_name, "según defaults de industria"));
  const checklist = blueprint?.checklist || wizard?.checklist || [];
  const followUpBotId = applyResult?.wizard?.bot_id || wizard?.bot_id || selectedBotId || "";
  const hasReconfigurationChanges = Boolean(selectedBot && (
    safeText(selectedBot.vertical) !== selectedVerticalId
    || normalizeName(currentBotSubvertical) !== normalizeName(selectedSubvertical)
    || normalizeName(currentBotObjective) !== normalizeName(selectedPrimaryObjective)
  ));
  const selectedOrRecommendedIntegrationKeys = unique(selectedIntegrationKeys.length ? selectedIntegrationKeys : recommendedIntegrations);
  const recommendedChannels = unique(selectedOrRecommendedIntegrationKeys.map((item) => integrationOptionLabels.get(item) || integrationLabel(item)));
  const nextFaqQuestions = unique(parseFaqBlock(faqText).map((item) => item.q));
  const nextKnowledgeSources = parseTextBlock(knowledgeSourcesText);
  const currentKnowledgeSeed = unique([
    ...currentBotFaqs.map((item) => `FAQ · ${item}`),
    ...currentBotPolicies.map((item) => `Política · ${item}`),
    ...currentBotKnowledgeSources.map((item) => `Fuente · ${item}`),
  ]);
  const nextKnowledgeSeed = unique([
    ...nextFaqQuestions.map((item) => `FAQ · ${item}`),
    ...nextPolicies.map((item) => `Política · ${item}`),
    ...nextKnowledgeSources.map((item) => `Fuente · ${item}`),
  ]);
  const summarySeededServices = unique(mode === "reconfigure" ? nextServices : [...parseTextBlock(servicesText), ...nextServices]);
  const summaryTemplates = unique(mode === "reconfigure" ? nextTemplates : [...nextTemplates, ...parseTextBlock(primaryCtasText).map((item) => `CTA · ${item}`)]);
  const packTemplateCreates = freshValues(summaryTemplates, currentBotTemplates);
  const packTemplateReuses = overlapValues(summaryTemplates, currentBotTemplates);
  const packServiceCreates = freshValues(nextServices, currentBotServices);
  const packServiceReuses = overlapValues(nextServices, currentBotServices);
  const packKnowledgeCreates = freshValues(nextKnowledgeSeed, currentKnowledgeSeed);
  const packKnowledgeReuses = overlapValues(nextKnowledgeSeed, currentKnowledgeSeed);
  const packIntegrationCreates = freshValues(selectedOrRecommendedIntegrationKeys, currentBotIntegrations).map((item) => integrationOptionLabels.get(item) || integrationLabel(item));
  const packIntegrationReuses = overlapValues(selectedOrRecommendedIntegrationKeys, currentBotIntegrations).map((item) => integrationOptionLabels.get(item) || integrationLabel(item));
  const missingSummaryItems = unique(mode === "create"
    ? [
        !selectedOrganizationId ? "Falta elegir la organización." : "",
        !selectedVerticalId ? (candidateVerticalId ? "Falta confirmar la industria." : "Falta elegir la industria.") : "",
        !selectedSubvertical ? (candidateSubvertical ? "Falta confirmar el tipo de operación." : "Falta fijar el tipo de operación.") : "",
        !selectedPrimaryObjective ? "Falta definir el objetivo operativo." : "",
        !businessName.trim() ? "Falta escribir el nombre del negocio." : "",
        !botName.trim() ? "Falta nombrar el asistente operativo." : "",
        !parseTextBlock(servicesText).length ? "Falta sembrar servicios base." : "",
        !parseFaqBlock(faqText).length ? "Falta una base mínima de FAQ." : "",
        !selectedIntegrationKeys.length ? "Falta seleccionar al menos un canal o integración prioritaria." : "",
      ]
    : [
        !selectedBotId ? "Falta elegir el asistente operativo a reconfigurar." : "",
        !selectedVerticalId ? (candidateVerticalId ? "Falta confirmar la industria de destino." : "Falta elegir la industria de destino.") : "",
        !selectedSubvertical ? (candidateSubvertical ? "Falta confirmar el tipo de operación de destino." : "Falta elegir el tipo de operación de destino.") : "",
        !hasReconfigurationChanges ? "Todavía no hay cambios detectados sobre la configuración generada." : "",
        activeStep === "confirm" && !reviewConfirmed ? "Falta confirmar que revisaste el diff destructivo." : "",
      ]);
  const dryRunDomains = dryRunResult?.diff_domains || [];

  useEffect(() => {
    if (!postApplyBotId) {
      setPostApplyBot(null);
      setPostApplyReleases([]);
      setPostApplySimulationRuns([]);
      setPostApplyError("");
      setPostApplyLoading(false);
      return;
    }

    let cancelled = false;
    async function loadPostApplyState() {
      setPostApplyLoading(true);
      setPostApplyError("");
      try {
        const [botPayload, releasePayload, simulationPayload] = await Promise.all([
          requestApiJson<unknown>(`/api/v1/bots/${encodeURIComponent(postApplyBotId)}`),
          requestApiJson<unknown[]>(`/api/v1/bots/${encodeURIComponent(postApplyBotId)}/release-requests`),
          requestApiJson<Array<Record<string, unknown>>>(`/api/v1/bots/${encodeURIComponent(postApplyBotId)}/simulation-runs`),
        ]);
        if (cancelled) return;
        setPostApplyBot(normalizeBot(botPayload));
        setPostApplyReleases(Array.isArray(releasePayload) ? releasePayload.map(normalizeReleaseRequest) : []);
        setPostApplySimulationRuns(Array.isArray(simulationPayload) ? simulationPayload.map((item) => asRecord(item)) : []);
      } catch (error) {
        if (cancelled) return;
        setPostApplyError(error instanceof Error ? error.message : "No se pudo calcular la siguiente acción operativa.");
      } finally {
        if (!cancelled) setPostApplyLoading(false);
      }
    }

    loadPostApplyState();
    return () => {
      cancelled = true;
    };
  }, [postApplyBotId]);

  const effectivePostApplyBot = postApplyBot || (postApplyBotId && selectedBot?.id === postApplyBotId ? selectedBot : null);
  const simulationRunsForDecision = useMemo(
    () => simulationResult ? [asRecord(simulationResult), ...postApplySimulationRuns] : postApplySimulationRuns,
    [postApplySimulationRuns, simulationResult],
  );
  const hasConnectedChannel = useMemo(() => hasConnectedOperationalChannel(effectivePostApplyBot), [effectivePostApplyBot]);
  const latestSimulationAfterApply = useMemo(
    () => simulationRunsForDecision.find((run) => happenedAfter(run.created_at, postApplyAppliedAt)) || null,
    [postApplyAppliedAt, simulationRunsForDecision],
  );
  const latestSimulationSummary = useMemo(() => asRecord(latestSimulationAfterApply?.summary), [latestSimulationAfterApply]);
  const latestSimulationPassRate = useMemo(() => Number(latestSimulationSummary.pass_rate || 0), [latestSimulationSummary]);
  const hasSimulationAfterApply = useMemo(() => Boolean(latestSimulationAfterApply), [latestSimulationAfterApply]);
  const hasApprovedSimulationAfterApply = useMemo(
    () => Boolean(latestSimulationAfterApply && String(latestSimulationAfterApply.status || "").toLowerCase() === "completed" && latestSimulationPassRate >= 80),
    [latestSimulationAfterApply, latestSimulationPassRate],
  );
  const hasPublishedReleaseAfterApply = useMemo(
    () => postApplyReleases.some((release) => String(release.status || "").toLowerCase() === "published" && happenedAfter(release.updated_at || release.created_at, postApplyAppliedAt)),
    [postApplyAppliedAt, postApplyReleases],
  );
  const hasReleaseRequestAfterApply = useMemo(
    () => postApplyReleases.some((release) => happenedAfter(release.updated_at || release.created_at, postApplyAppliedAt)),
    [postApplyAppliedAt, postApplyReleases],
  );
  const isLiveOrReadyToOperate = useMemo(
    () => Boolean(hasConnectedChannel && hasApprovedSimulationAfterApply && (hasPublishedReleaseAfterApply || botIsReadyToOperate(effectivePostApplyBot))),
    [effectivePostApplyBot, hasApprovedSimulationAfterApply, hasConnectedChannel, hasPublishedReleaseAfterApply],
  );
  const nextBestAction = useMemo<NextBestAction | null>(() => {
    if (!postApplyBotId) return null;
    if (!hasConnectedChannel) {
      return {
        key: "connect_channel",
        title: "Conectar canal",
        description: "Todavía no hay un canal operativo claro para este asistente. Antes de pedir pruebas o release, conéctalo para que la salida del wizard termine en operación real.",
        ctaLabel: "Conectar canal",
        href: "/integrations?section=configuracion",
      };
    }
    if (!hasApprovedSimulationAfterApply) {
      return {
        key: "run_simulation",
        title: "Correr simulación",
        description: hasSimulationAfterApply
          ? "Ya hay una simulación posterior al apply, pero todavía no quedó aprobada. Corre o repite la verificación antes de empujar release."
          : "El canal ya existe, pero todavía no hay una simulación aprobada posterior al apply actual. Corre una simulación guiada antes de empujar release.",
        ctaLabel: "Correr simulación",
      };
    }
    if (isLiveOrReadyToOperate) {
      return {
        key: "open_inbox",
        title: "Abrir inbox",
        description: hasPublishedReleaseAfterApply
          ? "El canal está conectado, la simulación básica ya quedó aprobada y este cambio ya tiene release publicado. Lo siguiente es operar y observar el tráfico real desde bandeja."
          : "El asistente ya está listo para operar con canal y simulación aprobados. Aunque todavía quieras revisar releases o integraciones, el destino natural de primer nivel ya es Inbox.",
        ctaLabel: "Abrir inbox",
        href: "/inbox",
      };
    }
    return {
      key: "publish_release",
      title: "Publicar release",
      description: hasReleaseRequestAfterApply
        ? "Ya hay evidencia de simulación aprobada y también una solicitud de release en curso. El siguiente paso operativo es llevarla a salida."
        : "La simulación básica ya quedó aprobada, pero este apply todavía no tiene release publicado. El siguiente paso operativo es abrir publish y sacarlo a producción.",
      ctaLabel: "Publicar release",
      href: `/releases?stage=draft&bot_id=${encodeURIComponent(postApplyBotId)}`,
    };
  }, [hasApprovedSimulationAfterApply, hasConnectedChannel, hasPublishedReleaseAfterApply, hasReleaseRequestAfterApply, hasSimulationAfterApply, isLiveOrReadyToOperate, postApplyBotId]);

  const persistedValidationSnapshot = dryRunResult?.validation_snapshot || applyResult?.validation_snapshot || wizard?.validation_snapshot || null;
  const liveValidationSnapshot = useMemo(
    () => buildClientValidationSnapshot(persistedValidationSnapshot, {
      hasConnectedChannel,
      hasSimulationAfterApply,
      hasApprovedSimulationAfterApply,
      latestSimulationAfterApply,
      hasReleaseRequestAfterApply,
      hasPublishedReleaseAfterApply,
      nextBestAction,
      applyReady: Boolean(dryRunResult?.summary?.apply_ready ?? persistedValidationSnapshot?.apply_ready ?? wizard?.status === "applied"),
    }),
    [dryRunResult?.summary?.apply_ready, hasApprovedSimulationAfterApply, hasConnectedChannel, hasPublishedReleaseAfterApply, hasReleaseRequestAfterApply, hasSimulationAfterApply, latestSimulationAfterApply, nextBestAction, persistedValidationSnapshot, wizard?.status],
  );

  const nextBestActionModule = useMemo(() => {
    switch (nextBestAction?.key) {
      case "connect_channel": return "Integraciones";
      case "publish_release": return "Releases";
      case "open_inbox": return "Inbox";
      default: return "Wizard";
    }
  }, [nextBestAction?.key]);

  const canExitToNextModule = nextBestActionModule !== "Wizard";

  type ProgressStepStatus = "done" | "active" | "pending";
  type ProgressStep = {
    key: string;
    label: string;
    detail: string;
    status: ProgressStepStatus;
  };

  const remainingProgressSteps = useMemo<ProgressStep[]>(() => ([
    {
      key: "connect",
      label: "Conectar",
      detail: hasConnectedChannel ? "Canal operativo detectado." : "Falta conectar el canal principal.",
      status: hasConnectedChannel ? "done" : nextBestAction?.key === "connect_channel" ? "active" : "pending",
    },
    {
      key: "test",
      label: "Probar",
      detail: hasApprovedSimulationAfterApply
        ? `Simulación aprobada (${safeText(String(latestSimulationPassRate), "0")}%).`
        : hasSimulationAfterApply
          ? "Hay simulación, pero todavía no queda aprobada."
          : "Falta correr o aprobar la simulación básica.",
      status: hasApprovedSimulationAfterApply ? "done" : nextBestAction?.key === "run_simulation" ? "active" : "pending",
    },
    {
      key: "publish",
      label: "Publicar",
      detail: hasPublishedReleaseAfterApply
        ? "El release ya quedó publicado."
        : hasReleaseRequestAfterApply
          ? "Ya existe release en curso."
          : "Falta publicar el release del cambio.",
      status: hasPublishedReleaseAfterApply ? "done" : nextBestAction?.key === "publish_release" ? "active" : "pending",
    },
    {
      key: "operate",
      label: "Operar",
      detail: hasPublishedReleaseAfterApply
        ? "Ya puedes abrir inbox y operar con tráfico real."
        : "Inbox queda como último paso después de publicar.",
      status: nextBestAction?.key === "open_inbox" ? "active" : "pending",
    },
  ]), [hasApprovedSimulationAfterApply, hasConnectedChannel, hasPublishedReleaseAfterApply, hasReleaseRequestAfterApply, hasSimulationAfterApply, latestSimulationPassRate, nextBestAction?.key]);

  const remainingProgressCount = useMemo(() => remainingProgressSteps.filter((item) => item.status !== "done").length, [remainingProgressSteps]);

  const secondaryNextActions = useMemo(() => {
    const botId = postApplyBotId ? encodeURIComponent(postApplyBotId) : "";
    const inboxReadyActions = [
      { key: "versions", label: "Revisar versiones", href: botId ? `/bots/${botId}/versions` : "/bots" },
      { key: "connect_channel", label: "Abrir integraciones", href: "/integrations?section=configuracion" },
      { key: "run_simulation", label: "Ir a simulación", action: () => goToStep("simulate") },
    ];
    const defaultActions = [
      { key: "connect_channel", label: "Conectar canal", href: "/integrations?section=configuracion" },
      { key: "run_simulation", label: "Ir a simulación", action: () => goToStep("simulate") },
      { key: "publish_release", label: "Abrir publish", href: botId ? `/releases?stage=draft&bot_id=${botId}` : "/releases?stage=draft" },
      { key: "open_inbox", label: "Abrir inbox", href: "/inbox" },
      { key: "versions", label: "Revisar versiones", href: botId ? `/bots/${botId}/versions` : "/bots" },
    ];
    const source = nextBestAction?.key === "open_inbox" ? inboxReadyActions : defaultActions;
    return source.filter((item) => item.key !== nextBestAction?.key);
  }, [nextBestAction?.key, postApplyBotId]);

const currentHandoffPreview = useMemo(() => {
  const source = (dryRunResult?.handoff_preview?.current || {}) as WizardHandoffPreview["current"];
  const currentRules = Object.keys(asRecord(source?.rule_overrides)).length ? asRecord(source?.rule_overrides) : (asRecord(asRecord(selectedBot?.config_draft).handoff).override_rules || asRecord(asRecord(selectedBot?.config_draft).rules));
  return {
    escalateWhen: summarize(source?.escalate_when || readNestedStrings(selectedBot?.config_draft, ["rules", "escalate_when"]), "Sin triggers visibles", 5),
    handoffKeywords: summarize(source?.handoff_keywords || readNestedStrings(selectedBot?.config_draft, ["handoff", "sensitive_keywords"]), "Sin palabras visibles", 5),
    expectedHandoffSla: safeText(source?.expected_handoff_sla, readNestedString(selectedBot?.config_draft, ["handoff", "expected_sla"], "Sin SLA visible")),
    humanDestinationChannel: safeText(source?.human_destination_channel, readNestedString(selectedBot?.config_draft, ["handoff", "destination_channel"], readNestedString(selectedBot?.config_draft, ["handoff", "channel"], mode === "reconfigure" ? "Sin canal humano visible" : "Se definirá al crear"))),
    ruleOverridesSummary: summarizeRuleOverrides(currentRules),
  };
}, [dryRunResult?.handoff_preview, selectedBot, mode]);

const proposedHandoffPreview = useMemo(() => {
  const source = (dryRunResult?.handoff_preview?.proposed || {}) as WizardHandoffPreview["proposed"];
  return {
    escalateWhen: summarize(parseTextBlock(escalateWhenText).length ? parseTextBlock(escalateWhenText) : (source?.escalate_when || []), "Sin triggers configurados", 5),
    handoffKeywords: summarize(parseTextBlock(handoffKeywordsText).length ? parseTextBlock(handoffKeywordsText) : (source?.handoff_keywords || []), "Sin palabras configuradas", 5),
    expectedHandoffSla: handoffSlaText.trim() || safeText(source?.expected_handoff_sla, "20 minutos"),
    humanDestinationChannel: humanDestinationChannelText.trim() || safeText(source?.human_destination_channel, "Equipo humano / operaciones"),
    ruleOverridesSummary: summarizeRuleOverrides(parseJsonObject(ruleOverridesText) || source?.rule_overrides),
  };
}, [dryRunResult?.handoff_preview, escalateWhenText, handoffKeywordsText, handoffSlaText, humanDestinationChannelText, ruleOverridesText]);
  const fallbackDryRunDiff = dryRunResult?.diff_summary || [];

  const completedChecklist = checklist.length
    ? checklist.filter((item) => Boolean(item.completed)).length
    : unique(mode === "create"
      ? [
          selectedOrganizationId ? "organization" : null,
          selectedVerticalId ? "industry" : null,
          selectedSubvertical ? "operation" : null,
          selectedPrimaryObjective ? "objective" : null,
          businessName.trim() && botName.trim() ? "identity" : null,
          parseTextBlock(servicesText).length && parseFaqBlock(faqText).length ? "knowledge" : null,
          selectedIntegrationKeys.length ? "channels" : null,
        ]
      : [
          selectedBotId ? "assistant" : null,
          selectedVerticalId ? "industry" : null,
          selectedSubvertical ? "operation" : null,
          hasReconfigurationChanges ? "diff" : null,
          reviewConfirmed ? "confirm" : null,
        ]).length;
  const totalChecklist = checklist.length || (mode === "create" ? 7 : 5);
  const draftReadinessScore = totalChecklist ? Math.round((completedChecklist / totalChecklist) * 100) : 0;
  const draftReadinessTone = draftReadinessScore >= 80 ? "success" : draftReadinessScore >= 45 ? "warning" : "danger";
  const draftReadinessLabel = draftReadinessScore >= 80 ? "Listo para aplicar" : draftReadinessScore >= 45 ? "En progreso" : "Faltan bases";
  const previewReadyForCreate = reviewReadyForCreate({
    businessName,
    botName,
    selectedVerticalId,
    selectedSubvertical,
    servicesText,
    faqText,
    integrationKeys: selectedIntegrationKeys,
  });

  const hasBusinessIdentity = Boolean(businessName.trim() && botName.trim());
  const canStartCreate = Boolean(selectedOrganizationId && selectedVerticalId && selectedSubvertical && hasBusinessIdentity);
  const canSaveBasics = Boolean(selectedOrganizationId && selectedVerticalId && selectedSubvertical && hasBusinessIdentity && tone.trim() && language.trim() && timezone.trim());
  const canSaveOffer = Boolean(parseTextBlock(servicesText).length && parseTextBlock(primaryCtasText).length);
  const canSaveKnowledge = Boolean(parseFaqBlock(faqText).length && parseTextBlock(policiesText).length && parseTextBlock(knowledgeSourcesText).length);
  const canSaveIntegrations = Boolean(selectedIntegrationKeys.length && parseTextBlock(escalateWhenText).length);

  function clampCreateStepNavigation(target: ActiveStep): { step: ActiveStep; blockedReason: string } {
    const checks: Array<{ step: ActiveStep; ready: boolean; blockedReason: string }> = [
      { step: "scope", ready: true, blockedReason: "" },
      { step: "basics", ready: canStartCreate, blockedReason: "Completa organización, industria, tipo de operación y la identidad base antes de seguir." },
      { step: "offer", ready: canSaveBasics, blockedReason: "Completa y guarda Fundamentos antes de abrir Oferta." },
      { step: "knowledge", ready: canSaveOffer, blockedReason: "Completa Oferta antes de abrir Knowledge." },
      { step: "integrations", ready: canSaveKnowledge, blockedReason: "Completa Knowledge antes de abrir Reglas e integraciones." },
      { step: "review", ready: canSaveIntegrations, blockedReason: "Completa Integraciones y reglas antes de abrir Review." },
      { step: "publish", ready: Boolean(applyResult?.wizard?.id || wizard?.status === "applied"), blockedReason: "Aplica el wizard antes de abrir Publish." },
    ];
    let lastAllowed: ActiveStep = "scope";
    for (const item of checks) {
      if (item.ready) lastAllowed = item.step;
      if (item.step === target) return item.ready ? { step: target, blockedReason: "" } : { step: lastAllowed, blockedReason: item.blockedReason };
    }
    if (target === "simulate") {
      return Boolean(applyResult?.wizard?.id || wizard?.status === "applied")
        ? { step: target, blockedReason: "" }
        : { step: lastAllowed, blockedReason: "Aplica el wizard antes de abrir Simulación." };
    }
    return { step: lastAllowed, blockedReason: "" };
  }

  function goToStep(nextStep: ActiveStep, options: { silent?: boolean } = {}) {
    if (mode === "create") {
      const navigation = clampCreateStepNavigation(nextStep);
      if (navigation.blockedReason && !options.silent) {
        setWizardError(navigation.blockedReason);
        recordTimeline("wizard.navigation_blocked", { requestedStep: nextStep, recoveredStep: navigation.step, reason: navigation.blockedReason });
      }
      setActiveStep(navigation.step);
      return;
    }
    if ((nextStep === "publish" || nextStep === "simulate") && !applyResult?.wizard?.id && wizard?.status !== "applied") {
      if (!options.silent) {
        const reason = `Aplica el wizard antes de abrir ${nextStep === "publish" ? "Publish" : "Simulación"}.`;
        setWizardError(reason);
        recordTimeline("wizard.navigation_blocked", { requestedStep: nextStep, recoveredStep: activeStep, reason });
      }
      return;
    }
    setActiveStep(nextStep);
  }

  const diagnosticAllowedStep = mode === "create" ? clampCreateStepNavigation("publish").step : activeStep;

  async function handleCopyDiagnostics() {
    const backendEvents = Array.isArray(wizard?.event_log) ? wizard.event_log.slice(-8) : [];
    const report = {
      mode,
      activeStep,
      diagnosticAllowedStep,
      autosaveState,
      autosaveError,
      wizardError,
      wizard: wizard ? {
        id: wizard.id,
        status: wizard.status,
        current_step: wizard.current_step,
        progress_percent: wizard.progress_percent,
        wizard_revision: wizard.wizard_revision,
        updated_at: wizard.updated_at,
        diagnostics: wizard.diagnostics || null,
      } : null,
      dirtyWizardSteps,
      autosaveMetrics: clientAutosaveMetrics,
      clientTimelineEvents: clientTimelineEvents.slice(-12),
      backendEvents,
    };
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(JSON.stringify(report, null, 2));
        setDiagnosticCopyFeedback("Diagnóstico copiado");
        setTimeout(() => setDiagnosticCopyFeedback(""), 1600);
        return;
      }
      setDiagnosticCopyFeedback("Copia manualmente desde pantalla");
      setTimeout(() => setDiagnosticCopyFeedback(""), 1600);
    } catch {
      setDiagnosticCopyFeedback("No se pudo copiar");
      setTimeout(() => setDiagnosticCopyFeedback(""), 1600);
    }
  }

  function seedStepDrafts(nextBlueprint: WizardBlueprint | null) {
    const answers = nextBlueprint?.answers || {};
    const catalog = asRecord(answers.catalog_offer);
    const knowledge = asRecord(answers.knowledge_seed);
    const integrations = asRecord(answers.integrations_rules);
    const launch = asRecord(answers.launch_review);
    const replaceWithDefaults = !wizardId;

    const nextServicesText = textBlockFromList(Array.isArray(catalog.services) ? catalog.services.map((item) => String(item || "")) : nextBlueprint?.setup?.services || []);
    const nextFeaturedOffersText = textBlockFromList(Array.isArray(catalog.featured_offers) ? catalog.featured_offers.map((item) => String(item || "")) : nextBlueprint?.setup?.wizard?.featured_offers || []);
    const nextPrimaryCtasText = textBlockFromList(Array.isArray(catalog.primary_ctas)
      ? catalog.primary_ctas.map((item) => safeText(asRecord(item).label, String(item || "")))
      : (nextBlueprint?.setup?.wizard?.recommended_ctas || []).map((item) => item.label || item.key || item.goal || ""));
    const nextPricingNotesText = textBlockFromList(Array.isArray(catalog.pricing_notes) ? catalog.pricing_notes.map((item) => String(item || "")) : nextBlueprint?.setup?.wizard?.pricing_notes || []);
    const nextFaqText = textBlockFromFaqs(readFaqItems(knowledge.faqs || nextBlueprint?.setup?.faqs || []));
    const nextPoliciesText = textBlockFromList(Array.isArray(knowledge.policies) ? knowledge.policies.map((item) => String(item || "")) : nextBlueprint?.setup?.wizard?.policies || []);
    const nextKnowledgeSourcesText = textBlockFromList(Array.isArray(knowledge.knowledge_sources)
      ? knowledge.knowledge_sources.map((item) => safeText(asRecord(item).label, safeText(asRecord(item).connector_key, String(item || ""))))
      : (nextBlueprint?.setup?.wizard?.knowledge_sources || []).map((item) => safeText(item.label, safeText(item.connector_key, safeText(item.provider)))));
    const nextIntegrationKeys = unique(Array.isArray(integrations.selected_integrations)
      ? integrations.selected_integrations.map((item) => integrationIdentity(item as Partial<WizardRecommendedIntegration>))
      : (nextBlueprint?.setup?.wizard?.recommended_integrations || []).map(integrationIdentity));
    const nextEscalateWhenText = textBlockFromList(Array.isArray(integrations.escalate_when) ? integrations.escalate_when.map((item) => String(item || "")) : readNestedStrings(nextBlueprint?.setup, ["rules", "escalate_when"]));
    const nextHandoffKeywordsText = textBlockFromList(Array.isArray(integrations.handoff_keywords) ? integrations.handoff_keywords.map((item) => String(item || "")) : []);
    const nextHandoffSlaText = String(integrations.expected_handoff_sla || safeText(nextBlueprint?.setup?.handoff?.expected_sla, "20 minutos"));
    const nextHumanDestinationChannelText = String(integrations.human_destination_channel || safeText(nextBlueprint?.setup?.handoff?.destination_channel, "Equipo humano / operaciones"));
    const nextCanSayText = textBlockFromList(readNestedStrings(integrations, ["rule_overrides", "can_say"]));
    const nextCannotSayText = textBlockFromList(readNestedStrings(integrations, ["rule_overrides", "cannot_say"]));
    const nextRuleOverridesText = JSON.stringify(parseJsonObject(String(integrations.rule_overrides ? JSON.stringify(integrations.rule_overrides) : "")), null, 2);
    const nextLaunchNotesText = textBlockFromList(Array.isArray(launch.launch_notes)
      ? launch.launch_notes.map((item) => String(item || ""))
      : nextBlueprint?.setup?.wizard?.launch_notes || []);
    const nextPlaybookKeys = unique(Array.isArray(launch.recommended_playbooks)
      ? launch.recommended_playbooks.map((item) => safeText(asRecord(item).key, safeText(asRecord(item).label, String(item || ""))))
      : (nextBlueprint?.setup?.wizard?.recommended_playbooks || []).map((item) => item.key || item.label || ""));
    const nextAutopublishKnowledge = Boolean(launch.autopublish_knowledge ?? nextBlueprint?.setup?.wizard?.autopublish_knowledge ?? true);

    if (Array.isArray(catalog.services) || replaceWithDefaults || !servicesText.trim()) setServicesText(nextServicesText);
    if (Array.isArray(catalog.featured_offers) || replaceWithDefaults || !featuredOffersText.trim()) setFeaturedOffersText(nextFeaturedOffersText);
    if (Array.isArray(catalog.primary_ctas) || replaceWithDefaults || !primaryCtasText.trim()) setPrimaryCtasText(nextPrimaryCtasText);
    if (Array.isArray(catalog.pricing_notes) || replaceWithDefaults || !pricingNotesText.trim()) setPricingNotesText(nextPricingNotesText);
    if (Array.isArray(knowledge.faqs) || replaceWithDefaults || !faqText.trim()) setFaqText(nextFaqText);
    if (Array.isArray(knowledge.policies) || replaceWithDefaults || !policiesText.trim()) setPoliciesText(nextPoliciesText);
    if (Array.isArray(knowledge.knowledge_sources) || replaceWithDefaults || !knowledgeSourcesText.trim()) setKnowledgeSourcesText(nextKnowledgeSourcesText);
    if (Array.isArray(integrations.selected_integrations) || replaceWithDefaults || !selectedIntegrationKeys.length) setSelectedIntegrationKeys(nextIntegrationKeys);
    if (Array.isArray(integrations.escalate_when) || replaceWithDefaults || !escalateWhenText.trim()) setEscalateWhenText(nextEscalateWhenText);
    if (Array.isArray(integrations.handoff_keywords) || replaceWithDefaults || !handoffKeywordsText.trim()) setHandoffKeywordsText(nextHandoffKeywordsText);
    if (typeof integrations.expected_handoff_sla !== "undefined" || replaceWithDefaults || !handoffSlaText.trim()) setHandoffSlaText(nextHandoffSlaText);
    if (typeof integrations.human_destination_channel !== "undefined" || replaceWithDefaults || !humanDestinationChannelText.trim()) setHumanDestinationChannelText(nextHumanDestinationChannelText);
    if (readNestedStrings(integrations, ["rule_overrides", "can_say"]).length || replaceWithDefaults || !canSayText.trim()) setCanSayText(nextCanSayText);
    if (readNestedStrings(integrations, ["rule_overrides", "cannot_say"]).length || replaceWithDefaults || !cannotSayText.trim()) setCannotSayText(nextCannotSayText);
    if (Object.keys(parseJsonObject(nextRuleOverridesText)).length || replaceWithDefaults || !ruleOverridesText.trim()) setRuleOverridesText(nextRuleOverridesText);
    if (Array.isArray(launch.launch_notes) || replaceWithDefaults || !launchNotesText.trim()) setLaunchNotesText(nextLaunchNotesText);
    if (Array.isArray(launch.recommended_playbooks) || replaceWithDefaults || !selectedPlaybookKeys.length) setSelectedPlaybookKeys(nextPlaybookKeys);
    if (typeof launch.autopublish_knowledge !== "undefined" || replaceWithDefaults) setAutopublishKnowledge(nextAutopublishKnowledge);
  }

  useEffect(() => {
    if (mode !== "reconfigure" || !selectedBot) return;
    const org = organizationsById[selectedBot.organization_id] || null;
    const wizardFit = asRecord(wizard?.answers?.vertical_fit);
    setSelectedOrganizationId(selectedBot.organization_id);
    setBusinessName(selectedBot.business_name || org?.name || "");
    setBotName(selectedBot.name || "");
    setCandidateVerticalId(String(wizardFit.vertical_id || selectedBot.vertical || org?.vertical || ""));
    setCandidateSubvertical(String(wizardFit.subvertical || pickBotSubvertical(selectedBot, org) || org?.subvertical || ""));
    setSelectedVerticalId(String(wizardFit.vertical_id || wizard?.vertical_id || ""));
    setSelectedSubvertical(String(wizardFit.subvertical || wizard?.subvertical || ""));
    setSelectedPrimaryObjective(normalizeObjective(selectedBot.objective || selectedBot.goal));
    setTone(pickBotTone(selectedBot));
    setLanguage(String(selectedBot.language || "es"));
    setTimezone(String(selectedBot.timezone || org?.timezone || "America/Mexico_City"));
  }, [mode, selectedBot, organizationsById, wizard]);

  useEffect(() => {
    if (mode !== "create") return;
    if (!businessName && selectedOrganization?.name) setBusinessName(selectedOrganization.name);
    if (!botName && selectedOrganization?.name) setBotName(`Asistente operativo ${selectedOrganization.name}`);
    if (!timezone && selectedOrganization?.timezone) setTimezone(selectedOrganization.timezone);
  }, [mode, selectedOrganization, businessName, botName, timezone]);

  useEffect(() => {
    if (!selectedOrganizationId || !previewVerticalId) {
      reactiveSelectionLoader.cancel();
      setBlueprint(null);
      setVerticalProfile(null);
      setPreviewLoading(false);
      setPreviewError("");
      return;
    }
    setPreviewLoading(true);
    setPreviewError("");

    reactiveSelectionLoader.load({
      organizationId: selectedOrganizationId,
      verticalId: previewVerticalId,
      subvertical: previewSubvertical,
      primaryObjective: selectedPrimaryObjective,
      mode,
      botId: selectedBotId,
    }).then((result) => {
      if (!result) return;
      const { blueprint: nextBlueprint, verticalProfile: nextProfile, errors } = result;
      setBlueprint(nextBlueprint);
      setVerticalProfile(nextProfile);
      setPreviewError(errors.join(" "));
      if (!nextBlueprint || !nextProfile) return;
      const validNames = buildSubverticalProfiles(nextProfile, nextBlueprint, verticals.find((item) => item.id === previewVerticalId) || null).map((item) => safeText(item.name));
      if (previewSubvertical && validNames.length && !validNames.some((item) => normalizeName(item) === normalizeName(previewSubvertical))) {
        setCandidateSubvertical("");
        if (selectedVerticalId === previewVerticalId) setSelectedSubvertical("");
        return;
      }
      if (mode === "create" && selectedVerticalId && selectedSubvertical && selectedVerticalId === previewVerticalId && normalizeName(selectedSubvertical) === normalizeName(previewSubvertical)) {
        seedStepDrafts(nextBlueprint);
      }
    }).finally(() => {
      setPreviewLoading(false);
    });
    return () => { reactiveSelectionLoader.cancel(); };
  }, [mode, reactiveSelectionLoader, selectedOrganizationId, previewVerticalId, previewSubvertical, selectedPrimaryObjective, selectedBotId, verticals, selectedVerticalId, selectedSubvertical]);


  function handlePreviewVertical(nextVerticalId: string) {
    setCandidateVerticalId(nextVerticalId);
    setCandidateSubvertical(nextVerticalId === selectedVerticalId ? selectedSubvertical : "");
  }

  function handleConfirmVertical(nextVerticalId?: string) {
    const verticalId = String(nextVerticalId || candidateVerticalId || "");
    if (!verticalId) return;
    setCandidateVerticalId(verticalId);
    setSelectedVerticalId(verticalId);
    if (verticalId === selectedVerticalId) {
      setCandidateSubvertical((current) => current || selectedSubvertical);
      return;
    }
    setCandidateSubvertical("");
    setSelectedSubvertical("");
  }

  function handlePreviewSubvertical(nextSubvertical: string) {
    setCandidateSubvertical(nextSubvertical);
  }

  function handleConfirmSubvertical(nextSubvertical?: string) {
    if (!selectedVerticalId || selectedVerticalId !== previewVerticalId) return;
    const subvertical = String(nextSubvertical || candidateSubvertical || "");
    if (!subvertical) return;
    setCandidateSubvertical(subvertical);
    setSelectedSubvertical(subvertical);
  }

  function updateUrl(next: { mode?: WizardMode; wizardId?: string; botId?: string; clearWizard?: boolean; step?: ActiveStep }) {
    const url = new URL(window.location.href);
    url.searchParams.set("mode", next.mode || mode);
    if (next.botId) url.searchParams.set("bot", next.botId);
    else if ((next.mode || mode) === "create") url.searchParams.delete("bot");
    if (next.clearWizard) url.searchParams.delete("wizard_id");
    else if (next.wizardId) url.searchParams.set("wizard_id", next.wizardId);
    const effectiveStep = next.step || activeStep;
    if (effectiveStep) url.searchParams.set("step", effectiveStep);
    router.replace(`${url.pathname}${url.search}`);
  }

  function resetTransientState(nextMode: WizardMode) {
    if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    patchState({
      scope: {
        activeStep: resolveWizardInitialStep(nextMode, null),
      },
      wizardRuntime: {
        applyResult: null,
        dryRunResult: null,
        wizardError: "",
        reviewConfirmed: false,
        wizard: null,
        wizardId: "",
      },
      autosave: {
        autosaveState: "idle",
        autosaveError: "",
        lastSavedAt: "",
      },
      simulation: {
        simulationResult: null,
        simulationError: "",
        simulationTitle: "Validación guiada del wizard",
        simulationScenario: "Hola, quiero precio y también saber si pueden agendarme esta semana.",
        simulationExpectedAction: "",
      },
    });
  }

  function handleSwitchMode(nextMode: WizardMode) {
    recordTimeline("wizard.mode_switched", { fromMode: mode, toMode: nextMode, botId: selectedBotId || null });
    setMode(nextMode);
    resetTransientState(nextMode);
    updateUrl({ mode: nextMode, botId: nextMode === "reconfigure" ? selectedBotId : "", clearWizard: true });
  }

  async function ensureWizardExists() {
    const payload = wizardPayloads.start;
    const currentWizard = wizardRef.current;
    const sameScope = currentWizard
      && currentWizard.organization_id === payload.organization_id
      && String(currentWizard.bot_id || "") === String(payload.bot_id || "")
      && String(currentWizard.vertical_id || "") === payload.vertical_id
      && normalizeName(String(currentWizard.subvertical || "")) === normalizeName(payload.subvertical || "");

    const reusedWizard = sameScope && currentWizard?.id ? currentWizard : null;
    const activeWizard = reusedWizard || await startWizardRequest(payload);

    wizardRef.current = activeWizard;
    setWizard(activeWizard);
    setWizardId(activeWizard.id);
    updateUrl({ mode, wizardId: activeWizard.id, botId: payload.bot_id || "" });
    if (!reusedWizard?.id) {
      recordTimeline("wizard.started", {
        wizardId: activeWizard.id,
        verticalId: payload.vertical_id,
        subvertical: payload.subvertical || null,
        botId: payload.bot_id || null,
      });
    }
    return activeWizard;
  }

  function isWizardRevisionConflict(error: unknown) {
    return error instanceof Error && /wizard_revision_conflict/i.test(error.message);
  }

  function isWizardStepOutOfSequence(error: unknown) {
    return error instanceof Error && /wizard_step_out_of_sequence/i.test(error.message);
  }

  async function refreshWizardState(wizardIdToLoad: string) {
    const latest = await getWizardRequest(wizardIdToLoad);
    wizardRef.current = latest;
    setWizard(latest);
    setWizardId(latest.id);
    setLastSavedAt(String(latest.updated_at || ""));
    recordTimeline("wizard.refreshed", { wizardId: latest.id, revision: latest.wizard_revision ?? null, currentStep: latest.current_step || null });
    return latest;
  }

  async function persistWizardStepRaw(
    stepKey: string,
    payload: Record<string, unknown>,
    options: { existingWizard?: WizardInstance | null; source?: "manual" | "autosave" } = {},
  ) {
    const { existingWizard, source = "manual" } = options;
    const startedAt = Date.now();
    const payloadFingerprint = getStepPayloadFingerprint(payload);
    const queuedWizard = wizardRef.current?.id ? wizardRef.current : existingWizard;
    let activeWizard = queuedWizard?.id ? queuedWizard : await ensureWizardExists();
    const serverFingerprint = getWizardStepRunPayloadFingerprint(activeWizard, stepKey);
    if (serverFingerprint && serverFingerprint === payloadFingerprint) {
      lastAutosavedPayloadsRef.current[stepKey] = payloadFingerprint;
      recordTimeline(source === "autosave" ? "wizard.autosave_step_skipped_duplicate" : "wizard.step_save_skipped_duplicate", {
        stepKey,
        wizardId: activeWizard.id,
        revision: activeWizard.wizard_revision ?? null,
      });
      return activeWizard;
    }
    recordTimeline(source === "autosave" ? "wizard.autosave_step_started" : "wizard.step_save_started", {
      stepKey,
      wizardId: activeWizard.id,
      revision: activeWizard.wizard_revision ?? null,
      payloadFingerprint,
    });
    try {
      const updated = await saveWizardStepRequest(activeWizard.id, stepKey, payload, { expectedRevision: activeWizard.wizard_revision ?? null });
      wizardRef.current = updated;
      setWizard(updated);
      setWizardId(updated.id);
      setLastSavedAt(String(updated.updated_at || ""));
      lastAutosavedPayloadsRef.current[stepKey] = payloadFingerprint;
      refreshVisibleDiagnostics();
      recordTimeline(source === "autosave" ? "wizard.autosave_step_succeeded" : "wizard.step_save_succeeded", {
        stepKey,
        wizardId: updated.id,
        revision: updated.wizard_revision ?? null,
        currentStep: updated.current_step || null,
        durationMs: Date.now() - startedAt,
        payloadFingerprint,
      });
      return updated;
    } catch (error) {
      if (isWizardStepOutOfSequence(error) && activeWizard?.id) {
        const refreshed = await refreshWizardState(activeWizard.id);
        const recoveredStep = resolveWizardInitialStep(mode, refreshed, activeStep);
        setActiveStep(recoveredStep);
        setWizardError("Se bloqueó un guardado fuera de secuencia y el wizard volvió al último paso seguro.");
        recordTimeline("wizard.out_of_sequence_recovered", {
          source,
          stepKey,
          wizardId: refreshed.id,
          revision: refreshed.wizard_revision ?? null,
          recoveredStep,
        });
        return refreshed;
      }
      if (!isWizardRevisionConflict(error) || !activeWizard?.id) {
        recordTimeline(source === "autosave" ? "wizard.autosave_step_failed" : "wizard.step_save_failed", {
          stepKey,
          wizardId: activeWizard?.id || null,
          durationMs: Date.now() - startedAt,
          error: error instanceof Error ? error.message : "save_failed",
        });
        throw error;
      }
      activeWizard = await refreshWizardState(activeWizard.id);
      recordTimeline("wizard.revision_conflict_recovered", {
        source,
        stepKey,
        wizardId: activeWizard.id,
        revision: activeWizard.wizard_revision ?? null,
      });
      const updated = await saveWizardStepRequest(activeWizard.id, stepKey, payload, { expectedRevision: activeWizard.wizard_revision ?? null });
      wizardRef.current = updated;
      setWizard(updated);
      setWizardId(updated.id);
      setLastSavedAt(String(updated.updated_at || ""));
      lastAutosavedPayloadsRef.current[stepKey] = payloadFingerprint;
      refreshVisibleDiagnostics();
      recordTimeline(source === "autosave" ? "wizard.autosave_step_succeeded" : "wizard.step_save_succeeded", {
        stepKey,
        wizardId: updated.id,
        revision: updated.wizard_revision ?? null,
        currentStep: updated.current_step || null,
        durationMs: Date.now() - startedAt,
        recoveredFromConflict: true,
        payloadFingerprint,
      });
      return updated;
    }
  }

  async function persistWizardStep(
    stepKey: string,
    payload: Record<string, unknown>,
    options: { existingWizard?: WizardInstance | null; source?: "manual" | "autosave" } = {},
  ) {
    const queued = saveQueueRef.current
      .catch(() => wizardRef.current)
      .then(() => persistWizardStepRaw(stepKey, payload, options));
    saveQueueRef.current = queued.catch(() => wizardRef.current);
    return queued;
  }

  async function syncScopeStep(source: "manual" | "autosave" = "manual", existingWizard?: WizardInstance | null) {
    return persistWizardStep("vertical_fit", wizardPayloads.scope, { existingWizard, source });
  }

  async function syncBasicsStep(source: "manual" | "autosave" = "manual", existingWizard?: WizardInstance | null) {
    return persistWizardStep("business_basics", wizardPayloads.basics, { existingWizard, source });
  }

  async function syncCatalogStep(source: "manual" | "autosave" = "manual", existingWizard?: WizardInstance | null) {
    return persistWizardStep("catalog_offer", wizardPayloads.catalog, { existingWizard, source });
  }

  async function syncKnowledgeStep(source: "manual" | "autosave" = "manual", existingWizard?: WizardInstance | null) {
    return persistWizardStep("knowledge_seed", wizardPayloads.knowledge, { existingWizard, source });
  }

  async function syncIntegrationsStep(source: "manual" | "autosave" = "manual", existingWizard?: WizardInstance | null) {
    return persistWizardStep("integrations_rules", wizardPayloads.integrations, { existingWizard, source });
  }

  async function syncLaunchReviewStep(source: "manual" | "autosave" = "manual", existingWizard?: WizardInstance | null) {
    return persistWizardStep("launch_review", wizardPayloads.launchReview, { existingWizard, source });
  }

  useEffect(() => {
    updateUrl({ mode, wizardId: wizardId || undefined, botId: mode === "reconfigure" ? selectedBotId : "", step: activeStep, clearWizard: !wizardId });
  }, [activeStep]);

  useEffect(() => {
    wizardRef.current = wizard;
  }, [wizard]);

  useEffect(() => {
    lastAutosavedPayloadsRef.current = {
      ...Object.fromEntries(fullWizardStepPayloads.map(([stepKey, payload]) => [stepKey, getStepPayloadFingerprint(payload as Record<string, unknown>)])),
    };
  }, []);

  useEffect(() => {
    if (!wizard?.id) return;
    const nextFingerprints = { ...lastAutosavedPayloadsRef.current };
    for (const [stepKey] of fullWizardStepPayloads) {
      const serverFingerprint = getWizardStepRunPayloadFingerprint(wizard, stepKey);
      if (serverFingerprint) nextFingerprints[stepKey] = serverFingerprint;
    }
    lastAutosavedPayloadsRef.current = nextFingerprints;
    refreshVisibleDiagnostics();
  }, [wizard?.id, wizard?.updated_at, fullWizardStepPayloads]);

  useEffect(() => {
    if (!wizard?.id) return;
    const diagnostics = wizard.diagnostics || null;
    if (!diagnostics?.integrity_mismatch) return;
    const signature = [wizard.id, diagnostics.integrity_signature || "no_signature", String(wizard.wizard_revision || 0)].join(":");
    if (lastIntegrityRefreshSignatureRef.current === signature) return;
    lastIntegrityRefreshSignatureRef.current = signature;
    recordTimeline("wizard.integrity_refresh_requested", {
      wizardId: wizard.id,
      revision: wizard.wizard_revision ?? null,
      mismatchFields: diagnostics.integrity_mismatch_fields || [],
    });
    void refreshWizardState(wizard.id).catch(() => undefined);
  }, [wizard?.id, wizard?.wizard_revision, wizard?.diagnostics?.integrity_signature, wizard?.diagnostics?.integrity_mismatch]);

  useEffect(() => {
    return () => {
      if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (working) return;
    if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);

    const canCreateWizard = mode === "create"
      ? Boolean(selectedOrganizationId && selectedVerticalId && selectedSubvertical && hasBusinessIdentity)
      : Boolean(selectedBotId && selectedOrganizationId && selectedVerticalId && selectedSubvertical);

    if (!canCreateWizard) {
      setAutosaveState(wizardId ? "saved" : "idle");
      return;
    }

    const allowedCreateStepKeys = new Set(getCreateAutosaveStepKeys(activeStep));
    const pendingSteps: Array<[string, Record<string, unknown>]> = (mode === "create"
      ? fullWizardStepPayloads.filter(([stepKey]) => allowedCreateStepKeys.has(stepKey))
      : requiredWizardStepPayloads)
      .map(([stepKey, payload]) => [stepKey, payload as Record<string, unknown>]);

    const changedSteps = pendingSteps.filter(([stepKey, payload]) => getStepPayloadFingerprint(payload) !== lastAutosavedPayloadsRef.current[stepKey]);
    if (!changedSteps.length) {
      setAutosaveState(wizardId ? "saved" : "idle");
      return;
    }

    const runId = ++autosaveRunRef.current;
    const startedAt = Date.now();
    recordTimeline("wizard.autosave_scheduled", { runId, changedSteps: changedSteps.map(([stepKey]) => stepKey), activeStep });
    autosaveTimerRef.current = setTimeout(async () => {
      try {
        if (runId !== autosaveRunRef.current) {
          recordTimeline("wizard.autosave_ignored", { runId, reason: "stale_before_start" });
          recordAutosaveBatchMetric("ignored", 0, changedSteps.length);
          return;
        }
        setAutosaveState("saving");
        setAutosaveError("");
        const activeWizard = await ensureWizardExists();
        let currentWizard = activeWizard;
        recordTimeline("wizard.autosave_started", { runId, wizardId: activeWizard.id, changedSteps: changedSteps.map(([stepKey]) => stepKey) });
        for (const [stepKey, payload] of changedSteps) {
          currentWizard = await persistWizardStep(stepKey, payload, { existingWizard: currentWizard, source: "autosave" });
        }
        if (runId !== autosaveRunRef.current) {
          recordTimeline("wizard.autosave_ignored", { runId, reason: "stale_after_save" });
          recordAutosaveBatchMetric("ignored", Date.now() - startedAt, changedSteps.length);
          return;
        }
        setAutosaveState("saved");
        setLastSavedAt(String(currentWizard.updated_at || ""));
        recordTimeline("wizard.autosave_succeeded", { runId, wizardId: currentWizard.id, changedSteps: changedSteps.map(([stepKey]) => stepKey), durationMs: Date.now() - startedAt });
        recordAutosaveBatchMetric("success", Date.now() - startedAt, changedSteps.length);
      } catch (error) {
        if (runId !== autosaveRunRef.current) {
          recordTimeline("wizard.autosave_ignored", { runId, reason: "stale_after_error" });
          recordAutosaveBatchMetric("ignored", Date.now() - startedAt, changedSteps.length);
          return;
        }
        setAutosaveState("error");
        const message = error instanceof Error ? error.message : "No se pudo guardar el progreso.";
        setAutosaveError(message);
        recordTimeline("wizard.autosave_failed", { runId, changedSteps: changedSteps.map(([stepKey]) => stepKey), durationMs: Date.now() - startedAt, error: message });
        recordAutosaveBatchMetric("error", Date.now() - startedAt, changedSteps.length);
      }
    }, 900);

    return () => {
      if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    };
  }, [
    mode,
    selectedBotId,
    selectedOrganizationId,
    selectedVerticalId,
    selectedSubvertical,
    selectedPrimaryObjective,
    businessName,
    botName,
    tone,
    language,
    timezone,
    hours,
    whatsappNumber,
    servicesText,
    featuredOffersText,
    primaryCtasText,
    pricingNotesText,
    faqText,
    policiesText,
    knowledgeSourcesText,
    selectedIntegrationKeys,
    escalateWhenText,
    handoffKeywordsText,
    handoffSlaText,
    humanDestinationChannelText,
    canSayText,
    cannotSayText,
    ruleOverridesText,
    launchNotesText,
    selectedPlaybookKeys,
    autopublishKnowledge,
    working,
    wizardId,
    hasBusinessIdentity,
    activeStep,
  ]);

  useEffect(() => {
    if (mode !== "reconfigure") return;
    setDryRunResult(null);
    setReviewConfirmed(false);
    if (activeStep === "dry_run" || activeStep === "confirm") goToStep("review", { silent: true });
  }, [mode, selectedBotId, selectedVerticalId, selectedSubvertical, selectedPrimaryObjective, servicesText, faqText, policiesText, selectedIntegrationKeys.join("|"), launchNotesText, selectedPlaybookKeys.join("|"), autopublishKnowledge]);

  useEffect(() => {
    if (!WIZARD_ENTERPRISE_FLAGS.enabled || !WIZARD_ENTERPRISE_FLAGS.autoRecoveryEnabled || working) return;
    const createNavigation = mode === "create" ? clampCreateStepNavigation(activeStep) : { step: activeStep, blockedReason: "" };
    const persistedStep = wizard ? resolveWizardInitialStep(mode, wizard) : null;
    const recovery = deriveWizardConsistencyRecovery({
      mode,
      activeStep,
      persistedStep,
      clientAllowedStep: mode === "create" ? createNavigation.step : null,
      wizardStatus: wizard?.status || null,
      hasDryRunResult: Boolean(dryRunResult?.validation_hash || dryRunResult?.summary?.validated_at),
      hasAppliedWizard: Boolean(applyResult?.wizard?.id || wizard?.status === "applied"),
    });
    if (!recovery || recovery.step === activeStep) return;
    const signature = [mode, wizardId || "no_wizard", String(wizard?.wizard_revision || 0), activeStep, recovery.step, recovery.reason].join(":");
    if (lastRecoverySignatureRef.current === signature) return;
    lastRecoverySignatureRef.current = signature;
    setActiveStep(recovery.step);
    recordTimeline("wizard.auto_recovery_applied", {
      fromStep: activeStep,
      toStep: recovery.step,
      reason: recovery.reason,
      persistedStep: persistedStep || null,
      clientAllowedStep: mode === "create" ? createNavigation.step : null,
    });
  }, [
    mode,
    activeStep,
    wizardId,
    wizard?.status,
    wizard?.current_step,
    wizard?.wizard_revision,
    applyResult?.wizard?.id,
    dryRunResult?.validation_hash,
    dryRunResult?.summary?.validated_at,
    canStartCreate,
    canSaveBasics,
    canSaveOffer,
    canSaveKnowledge,
    canSaveIntegrations,
    working,
  ]);

  async function handleSaveCreateScope() {
    if (!canStartCreate) {
      setWizardError("Completa organización, industria, tipo de operación y nombre del negocio antes de iniciar el wizard.");
      return;
    }
    setWorking(true);
    setWizardError("");
    try {
      const updated = await syncScopeStep();
      setActiveStep(resolveWizardInitialStep("create", updated));
    } catch (error) {
      setWizardError(error instanceof Error ? error.message : "No se pudo iniciar el wizard.");
    } finally {
      setWorking(false);
    }
  }

  async function handleSaveBasics() {
    if (!canSaveBasics) {
      setWizardError("Completa nombre del negocio, nombre del asistente, tono, idioma y zona horaria antes de seguir.");
      return;
    }
    setWorking(true);
    setWizardError("");
    try {
      const updated = await syncBasicsStep();
      setActiveStep(resolveWizardInitialStep("create", updated));
    } catch (error) {
      setWizardError(error instanceof Error ? error.message : "No se pudo guardar el paso.");
    } finally {
      setWorking(false);
    }
  }

  async function handleSaveOffer() {
    if (!canSaveOffer) {
      setWizardError("Agrega al menos un servicio y una CTA principal antes de seguir.");
      return;
    }
    setWorking(true);
    setWizardError("");
    try {
      const updated = await syncCatalogStep();
      setActiveStep(resolveWizardInitialStep("create", updated));
    } catch (error) {
      setWizardError(error instanceof Error ? error.message : "No se pudo guardar la oferta.");
    } finally {
      setWorking(false);
    }
  }

  async function handleSaveKnowledge() {
    if (!canSaveKnowledge) {
      setWizardError("Necesitas al menos un FAQ, una política y una fuente de conocimiento antes de seguir.");
      return;
    }
    setWorking(true);
    setWizardError("");
    try {
      const updated = await syncKnowledgeStep();
      setActiveStep(resolveWizardInitialStep("create", updated));
    } catch (error) {
      setWizardError(error instanceof Error ? error.message : "No se pudo guardar la knowledge base.");
    } finally {
      setWorking(false);
    }
  }

  async function handleSaveIntegrations() {
    if (!canSaveIntegrations) {
      setWizardError("Selecciona al menos una integración y define cuándo escalar antes de abrir review.");
      return;
    }
    setWorking(true);
    setWizardError("");
    try {
      const updated = await syncIntegrationsStep();
      setActiveStep(resolveWizardInitialStep("create", updated));
    } catch (error) {
      setWizardError(error instanceof Error ? error.message : "No se pudo guardar integraciones y reglas.");
    } finally {
      setWorking(false);
    }
  }

  async function handlePrepareReconfigure() {
    if (!selectedBotId || !hasReconfigurationChanges) return;
    setWorking(true);
    setWizardError("");
    try {
      await syncScopeStep();
      const updated = await syncBasicsStep();
      setActiveStep(resolveWizardInitialStep("reconfigure", updated));
    } catch (error) {
      setWizardError(error instanceof Error ? error.message : "No se pudo preparar la reconfiguracion.");
    } finally {
      setWorking(false);
    }
  }

  async function handleRunDryRun() {
    if (mode !== "reconfigure" || !selectedBotId || !hasReconfigurationChanges) return;
    setWorking(true);
    setWizardError("");
    try {
      const scoped = await syncScopeStep();
      let synced = await syncBasicsStep();
      if (scoped.id && scoped.id !== synced.id) synced = scoped;
      if (!synced?.id) throw new Error("No se pudo preparar el wizard para la prevalidación.");
      await syncIntegrationsStep();
      const result = await dryRunWizardRequest(synced.id);
      setDryRunResult(result);
      setWizard(result.wizard);
      setWizardId(result.wizard.id);
      setReviewConfirmed(false);
      goToStep("dry_run");
    } catch (error) {
      setWizardError(error instanceof Error ? error.message : "No se pudo correr la prevalidacion.");
    } finally {
      setWorking(false);
    }
  }

  async function handleApplyWizard() {
    if (mode === "reconfigure") {
      if (!dryRunResult?.summary?.apply_ready) {
        setWizardError("Antes de aplicar debes correr un dry run vigente y dejarlo sin conflictos bloqueantes.");
        return;
      }
      if (!reviewConfirmed) {
        setWizardError("Antes de aplicar debes confirmar que revisaste el dry run y entiendes la mutacion fuerte.");
        return;
      }
    }
    if (mode === "create" && !previewReadyForCreate) {
      setWizardError("Todavia faltan datos del setup. Completa oferta, knowledge e integraciones antes de aplicar.");
      return;
    }
    setWorking(true);
    setWizardError("");
    try {
      await syncScopeStep();
      await syncBasicsStep();
      if (mode === "create") {
        await syncCatalogStep();
        await syncKnowledgeStep();
      }
      await syncIntegrationsStep();
      const synced = await syncLaunchReviewStep();
      const result = await applyWizardRequest(synced.id);
      setApplyResult(result);
      setWizard(result.wizard);
      setWizardId(result.wizard.id);
      const nextBotId = String(result.wizard.bot_id || "");
      const nextStep = "publish";
      if (nextBotId) {
        setSelectedBotId(nextBotId);
        updateUrl({ mode, wizardId: result.wizard.id, botId: nextBotId, step: nextStep });
      }
      if (!simulationTitle.trim()) setSimulationTitle(mode === "create" ? `Validación de ${botName || businessName || "nuevo asistente operativo"}` : `Verificación final de ${selectedBot?.name || "asistente operativo"}`);
      setSimulationError("");
      setSimulationResult(null);
      setPostApplyPath("wizard");
      goToStep(nextStep);
    } catch (error) {
      setWizardError(error instanceof Error ? error.message : "No se pudo aplicar el wizard.");
    } finally {
      setWorking(false);
    }
  }


  async function handleRunSimulation() {
    const botId = String(applyResult?.wizard?.bot_id || selectedBotId || "");
    const organizationId = String(applyResult?.wizard?.organization_id || selectedOrganizationId || "");
    if (!botId || !organizationId) {
      setSimulationError("Primero aplica el wizard para tener un asistente operativo explícito que validar.");
      return;
    }
    setSimulationRunning(true);
    setSimulationError("");
    try {
      const createdCase = await requestApiJson<Record<string, unknown>>(`/api/v1/bots/${encodeURIComponent(botId)}/simulation-cases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          organization_id: organizationId,
          title: simulationTitle.trim() || `Validación de ${botId}`,
          scenario_text: simulationScenario.trim() || "Hola, quiero precio y también saber si pueden agendarme esta semana.",
          expected_action: simulationExpectedAction || undefined,
          tags: [mode, "wizard", "validation"],
        }),
      });
      const createdCaseId = String(createdCase.id || "");
      const runResult = await requestApiJson<Record<string, unknown>>(`/api/v1/bots/${encodeURIComponent(botId)}/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          compare_target: mode === "reconfigure" ? "published" : "draft",
          case_ids: createdCaseId ? [createdCaseId] : [],
        }),
      });
      setSimulationResult(runResult);
    } catch (error) {
      setSimulationError(error instanceof Error ? error.message : "No se pudo correr la simulación.");
    } finally {
      setSimulationRunning(false);
    }
  }

  const createFlowSteps: Array<{ key: ActiveStep; label: string }> = [
    { key: "scope", label: "1. Fundamentos" },
    { key: "basics", label: "2. Ajustes avanzados" },
    { key: "offer", label: "3. Oferta" },
    { key: "knowledge", label: "4. Knowledge y reglas" },
    { key: "review", label: "5. Revisar impacto" },
    { key: "simulate", label: "6. Simular" },
    { key: "publish", label: "7. Publicar" },
  ];
  const createProgressStep = activeStep === "integrations" ? "knowledge" : activeStep;
  const createStepIndex = createFlowSteps.findIndex((item) => item.key === createProgressStep);
  const reconfigureFlowSteps: Array<{ key: ActiveStep; label: string }> = [
    { key: "scope", label: "1. Cambio" },
    { key: "review", label: "2. Revisar impacto" },
    { key: "dry_run", label: "3. Dry run" },
    { key: "confirm", label: "4. Confirmar aplicación" },
    { key: "publish", label: "5. Aplicar y publicar" },
  ];
  const reconfigureStepIndex = reconfigureFlowSteps.findIndex((item) => item.key === activeStep);

  return (
    <div className="grid gap-6 xl:grid-cols-[1.12fr_0.88fr]">
      <div className="grid gap-6">
        <div className="grid gap-4 md:grid-cols-2">
          <ModeCard active={mode === "create"} title="Modo A · Nuevo asistente operativo" description="El setup ya corre de punta a punta sobre el wizard real: fundamentos, ajustes, oferta, knowledge, integraciones, review y apply viven sobre step updates del backend." onClick={() => handleSwitchMode("create")} />
          <ModeCard active={mode === "reconfigure"} title="Modo B · Reconfigurar asistente operativo" description="Primero eliges un asistente operativo explícito. Luego el wizard prepara diff, snapshot preventivo y aplicación de la nueva configuración generada sin depender de cookies ni selección silenciosa." onClick={() => handleSwitchMode("reconfigure")} />
        </div>

        <div className="flex flex-wrap gap-2">
          {(mode === "create" ? createFlowSteps : reconfigureFlowSteps).map((item, index) => (
            <StepBadge
              key={item.key}
              label={item.label}
              active={activeStep === item.key}
              done={mode === "create" ? createStepIndex > index || Boolean(applyResult) : reconfigureStepIndex > index || Boolean(applyResult)}
            />
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3 rounded-[22px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm text-[color:var(--text-secondary)]">
          <span className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Autosave</span>
          <strong className="text-[color:var(--text-primary)]">{autosaveState === "saving" ? "Guardando progreso..." : autosaveState === "saved" ? "Todo guardado" : autosaveState === "error" ? "Guardado pendiente" : "Aún sin wizard"}</strong>
          {wizardId ? <span className="mono-pill">wizard_id: {wizardId}</span> : null}
          {lastSavedAt ? <span>Ultimo guardado: {new Date(lastSavedAt).toLocaleString("es-MX", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" })}</span> : null}
        </div>

        {autosaveError ? <UiMessage title="Autosave pendiente" tone="warning">{autosaveError}</UiMessage> : null}
        {wizardError ? <UiMessage title="Wizard con error" tone="error">{wizardError}</UiMessage> : null}
        {previewError ? <UiMessage title="Preview incompleto" tone="warning">{previewError}</UiMessage> : null}
        {applyResult?.summary ? <UiMessage title={mode === "create" ? "Wizard aplicado y asistente operativo creado" : "Wizard aplicado sobre el asistente operativo existente"} tone="success">{mode === "create" ? "El frontend ya persistio todos los pasos clave del wizard antes de aplicar. No se quedó solo en vertical_fit y business_basics." : "El backend aplicó la configuración generada sobre el asistente operativo explícito y creó un snapshot preventivo antes de mutar el draft."}</UiMessage> : null}

        <WizardDiagnosticsPanel
          mode={mode}
          activeStep={activeStep}
          allowedStep={diagnosticAllowedStep}
          wizard={wizard}
          autosaveState={autosaveState}
          wizardError={wizardError}
          dirtySteps={dirtyWizardSteps}
          timelineEvents={clientTimelineEvents}
          autosaveMetrics={clientAutosaveMetrics}
          onRefresh={wizardId ? () => { void refreshWizardState(wizardId); } : undefined}
          onCopy={() => { void handleCopyDiagnostics(); }}
          copyFeedback={diagnosticCopyFeedback}
        />

        {mode === "reconfigure" ? (
          <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Selector inline del asistente operativo</div>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">Elige el asistente operativo exacto antes de cualquier reconfiguración</h3>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">La decisión crítica ya no depende de cookies. El asistente operativo manda porque el usuario lo ve, lo elige y confirma el impacto del cambio.</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {bots.length ? bots.map((bot) => {
                const botOrg = organizationsById[bot.organization_id] || null;
                const active = bot.id === selectedBotId;
                return (
                  <button
                    data-testid={`bot-card-${bot.id}`}
                    type="button"
                    key={bot.id}
                    onClick={() => {
                      setSelectedBotId(bot.id);
                      setMode("reconfigure");
                      setApplyResult(null);
                      setDryRunResult(null);
                      setWizardError("");
                      setReviewConfirmed(false);
                      setWizard(null);
                      setWizardId("");
                      setAutosaveState("idle");
                      setAutosaveError("");
                      setLastSavedAt("");
                      if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
                      updateUrl({ mode: "reconfigure", botId: bot.id, clearWizard: true, step: "scope" });
                    }}
                    className={`rounded-[24px] border p-4 text-left transition ${active ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)]" : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] hover:border-[color:var(--accent-border)] hover:bg-[color:var(--surface-elevated)]"}`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-base font-semibold text-[color:var(--text-primary)]">{safeText(bot.name, "Asistente operativo")}</div>
                      {active ? <span className="mono-pill">Activo</span> : null}
                    </div>
                    <div className="mt-3 grid gap-2 text-sm text-[color:var(--text-secondary)]">
                      <div><strong className="text-[color:var(--text-primary)]">Organización:</strong> {safeText(botOrg?.name, bot.organization_id)}</div>
                      <div><strong className="text-[color:var(--text-primary)]">Industria:</strong> {safeText(bot.vertical, "sin industria")}</div>
                      <div><strong className="text-[color:var(--text-primary)]">Estado:</strong> {safeText(bot.status, "draft")}</div>
                      <div><strong className="text-[color:var(--text-primary)]">Tipo de operación:</strong> {safeText(pickBotSubvertical(bot, botOrg), "sin tipo de operación")}</div>
                    </div>
                  </button>
                );
              }) : <div className="rounded-[24px] border border-dashed border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5 text-sm text-[color:var(--text-secondary)]">Todavía no hay asistentes operativos para reconfigurar.</div>}
            </div>
          </div>
        ) : null}

        <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{mode === "create" ? "Paso 1 · fundamentos" : "Seleccion del cambio"}</div>
          <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">{mode === "create" ? "Empieza con 5 decisiones, no con todo el panel de administracion" : "Define el cambio antes de revisar el impacto"}</h3>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{mode === "create" ? "El primer paso solo pide organización, industria, tipo de operación, objetivo y el nombre del negocio/asistente operativo. Todo el resto vive en pasos posteriores, ya conectados a los step updates del backend." : "Para reconfigurar, el cambio sigue siendo explícito: organización, industria, tipo de operación y objetivo se revisan antes de abrir el diff destructivo."}</p>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="field-label">
              Organización
              <select data-testid="organization-select" className="field-input" value={selectedOrganizationId} onChange={(event) => setSelectedOrganizationId(event.target.value)} disabled={mode === "reconfigure" && Boolean(selectedBot)}>
                <option value="">Selecciona una organización</option>
                {organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}
              </select>
            </label>
            <label className="field-label">
              Objetivo principal
              <select data-testid="objective-select" className="field-input" value={selectedPrimaryObjective} onChange={(event) => setSelectedPrimaryObjective(normalizeObjective(event.target.value))}>
                {OBJECTIVES.map((objective) => <option key={objective} value={objective}>{objectiveLabel(objective)}</option>)}
              </select>
            </label>
          </div>

          <div className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Industria preview</div>
                <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(previewCatalogVertical?.name, "Pendiente")}</div>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Industria confirmada</div>
                <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(catalogVertical?.name, selectedVerticalId || "Pendiente")}</div>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Tipo de operación preview</div>
                <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(previewSubvertical || selectedSubverticalProfile?.name, "Pendiente")}</div>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Tipo de operación confirmada</div>
                <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(selectedSubvertical, "Pendiente")}</div>
              </div>
            </div>
            <p className="mt-4 text-sm leading-6 text-[color:var(--text-secondary)]">El preview puede moverse libremente, pero “Continuar” solo se habilita cuando la industria y el tipo de operación quedaron confirmados con sus CTA explícitas.</p>
          </div>

          <div className="mt-5 grid gap-5">
            <VerticalPicker
              verticals={verticals}
              strongestVerticals={strongestVerticals}
              candidateVerticalId={previewVerticalId}
              confirmedVerticalId={selectedVerticalId}
              onPreview={handlePreviewVertical}
              onConfirm={handleConfirmVertical}
            />
            <SubverticalPicker
              verticalName={safeText(previewCatalogVertical?.name, "Industria")}
              candidateSubvertical={previewSubvertical}
              confirmedSubvertical={selectedSubvertical}
              subverticalProfiles={subverticalProfiles}
              onPreview={handlePreviewSubvertical}
              onConfirm={handleConfirmSubvertical}
              loading={previewLoading}
              verticalConfirmed={Boolean(selectedVerticalId && selectedVerticalId === previewVerticalId)}
            />
          </div>

          {mode === "create" ? (
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="field-label">Nombre del negocio<input data-testid="business-name-input" className="field-input" value={businessName} onChange={(event) => setBusinessName(event.target.value)} placeholder="Clinica Roma" /></label>
              <label className="field-label">Nombre del asistente operativo<input data-testid="bot-name-input" className="field-input" value={botName} onChange={(event) => setBotName(event.target.value)} placeholder="Asistente operativo Clínica Roma" /></label>
            </div>
          ) : null}

          <div className="mt-5 flex flex-wrap gap-3">
            {mode === "create" ? (
              <button data-testid="save-scope" className="primary-btn" type="button" onClick={handleSaveCreateScope} disabled={!canStartCreate || working}>Guardar fundamentos y abrir ajustes avanzados</button>
            ) : (
              <button data-testid="prepare-reconfigure" className="primary-btn" type="button" onClick={handlePrepareReconfigure} disabled={!selectedBotId || !hasReconfigurationChanges || working}>Revisar cambios</button>
            )}
            {wizardId ? <span className="mono-pill">wizard_id: {wizardId}</span> : null}
          </div>
          {!selectedVerticalId || !selectedSubvertical ? (
            <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">
              {candidateVerticalId && !selectedVerticalId
                ? "Ya hay preview de industria, pero falta pulsar “Usar esta industria”. "
                : ""}
              {candidateSubvertical && !selectedSubvertical
                ? "Ya hay preview de tipo de operación, pero falta pulsar “Usar este tipo de operación”."
                : ""}
            </p>
          ) : null}
        </div>

        {mode === "create" && activeStep !== "scope" ? (
          <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Paso 2 · ajustes avanzados</div>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">Completa los ajustes avanzados cuando ya existe claridad del setup</h3>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Este paso concentra tono, idioma, timezone, horario y WhatsApp. Los datos se persisten en `business_basics` del wizard, no en un estado suelto del cliente.</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="field-label">Tono<input className="field-input" value={tone} onChange={(event) => setTone(event.target.value)} placeholder="amable" /></label>
              <label className="field-label">Idioma<select className="field-input" value={language} onChange={(event) => setLanguage(event.target.value)}><option value="es">Espanol</option><option value="en">English</option></select></label>
              <label className="field-label">Timezone<input className="field-input" value={timezone} onChange={(event) => setTimezone(event.target.value)} placeholder="America/Mexico_City" /></label>
              <label className="field-label">WhatsApp<input className="field-input" value={whatsappNumber} onChange={(event) => setWhatsappNumber(event.target.value)} placeholder="+52155..." /></label>
              <label className="field-label md:col-span-2">Horario<input className="field-input" value={hours} onChange={(event) => setHours(event.target.value)} placeholder="Lun-Vie 10:00-19:00" /></label>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <button data-testid="save-basics" className="primary-btn" type="button" onClick={handleSaveBasics} disabled={!canSaveBasics || working}>Guardar ajustes avanzados</button>
              <button className="secondary-btn" type="button" onClick={() => goToStep("offer")}>Seguir con oferta</button>
            </div>
          </div>
        ) : null}

        {mode === "create" && ["offer", "knowledge", "integrations", "review"].includes(activeStep) ? (
          <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Paso 3 · oferta, catalogo y CTA</div>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">Conecta la promesa comercial con el wizard</h3>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Este bloque escribe `catalog_offer` en backend: servicios, ofertas destacadas, CTA principales y notas de precio.</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="field-label">Servicios base<textarea className="field-input min-h-[148px]" value={servicesText} onChange={(event) => setServicesText(event.target.value)} placeholder="Implantes\nLimpieza\nValoracion" /></label>
              <label className="field-label">Ofertas destacadas<textarea className="field-input min-h-[148px]" value={featuredOffersText} onChange={(event) => setFeaturedOffersText(event.target.value)} placeholder="Valoracion sin costo\nPaquete de bienvenida" /></label>
              <label className="field-label">CTA primarios<textarea className="field-input min-h-[120px]" value={primaryCtasText} onChange={(event) => setPrimaryCtasText(event.target.value)} placeholder="Agendar ahora\nHablar con asesor" /></label>
              <label className="field-label">Notas de precio<textarea className="field-input min-h-[120px]" value={pricingNotesText} onChange={(event) => setPricingNotesText(event.target.value)} placeholder="Financiamiento disponible\nPromocion por pronto pago" /></label>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <button data-testid="save-offer" className="primary-btn" type="button" onClick={handleSaveOffer} disabled={!canSaveOffer || working}>Guardar oferta y seguir</button>
              <button className="secondary-btn" type="button" onClick={() => goToStep("knowledge")}>Seguir con knowledge</button>
            </div>
          </div>
        ) : null}

        {mode === "create" && ["knowledge", "integrations", "review"].includes(activeStep) ? (
          <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Paso 4 · knowledge base viva</div>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">Persiste FAQ, politicas y fuentes vivas</h3>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">El formato recomendado para FAQ es `pregunta | respuesta`, una por linea. Todo esto termina en `knowledge_seed` del backend.</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="field-label">FAQ base<textarea className="field-input min-h-[180px]" value={faqText} onChange={(event) => setFaqText(event.target.value)} placeholder="Atienden sabados? | Si, de 10 a 14h\nAceptan tarjeta? | Si" /></label>
              <label className="field-label">Politicas<textarea className="field-input min-h-[180px]" value={policiesText} onChange={(event) => setPoliciesText(event.target.value)} placeholder="No prometer resultados medicos\nNo confirmar precios sin validacion" /></label>
              <label className="field-label md:col-span-2">Fuentes de conocimiento<textarea className="field-input min-h-[140px]" value={knowledgeSourcesText} onChange={(event) => setKnowledgeSourcesText(event.target.value)} placeholder="Drive / docs operativos\nSitio y landing pages\nPDF comercial" /></label>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <button data-testid="save-knowledge" className="primary-btn" type="button" onClick={handleSaveKnowledge} disabled={!canSaveKnowledge || working}>Guardar knowledge y seguir</button>
              <button className="secondary-btn" type="button" onClick={() => goToStep("integrations")}>Seguir con reglas</button>
            </div>
          </div>
        ) : null}

        {mode === "create" && ["integrations", "review"].includes(activeStep) ? (
          <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Paso 4 · knowledge y reglas (2/2)</div>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">No te quedes en defaults silenciosos</h3>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Este bloque guarda `integrations_rules`: integraciones seleccionadas, criterios de escalamiento, handoff keywords y overrides de reglas.</p>
            <div className="mt-4 grid gap-4">
              <div>
                <div className="mb-3 text-sm font-semibold text-[color:var(--text-primary)]">Integraciones planeadas</div>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {(integrationOptions.length ? integrationOptions : recommendedIntegrations.map((item) => ({ provider: item, name: item, integration_key: item } as WizardRecommendedIntegration))).map((item) => {
                    const id = integrationIdentity(item);
                    return (
                      <CheckboxPill
                        key={id}
                        checked={selectedIntegrationKeys.includes(id)}
                        label={safeText(item.name, id)}
                        secondary={safeText(item.integration_type, safeText(item.provider, "planned"))}
                        onChange={() => setSelectedIntegrationKeys((current) => current.includes(id) ? current.filter((entry) => entry !== id) : [...current, id])}
                      />
                    );
                  })}
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="field-label">Escalar cuando<textarea className="field-input min-h-[132px]" value={escalateWhenText} onChange={(event) => setEscalateWhenText(event.target.value)} placeholder="cliente pide humano\ncaso urgente\nrequiere excepcion" /></label>
                <label className="field-label">Handoff keywords<textarea className="field-input min-h-[132px]" value={handoffKeywordsText} onChange={(event) => setHandoffKeywordsText(event.target.value)} placeholder="doctor\nasesor\nurgente" /></label>
                <label className="field-label">Puede decir<textarea className="field-input min-h-[132px]" value={canSayText} onChange={(event) => setCanSayText(event.target.value)} placeholder="confirmar horario\nexplicar proceso" /></label>
                <label className="field-label">No puede decir<textarea className="field-input min-h-[132px]" value={cannotSayText} onChange={(event) => setCannotSayText(event.target.value)} placeholder="prometer resultado\ndiagnosticar" /></label>
                <label className="field-label md:col-span-2">Overrides JSON opcionales<textarea className="field-input min-h-[156px] font-mono" value={ruleOverridesText} onChange={(event) => setRuleOverridesText(event.target.value)} placeholder='{"after_hours": "escalar"}' /></label>
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <button data-testid="save-integrations" className="primary-btn" type="button" onClick={handleSaveIntegrations} disabled={!canSaveIntegrations || working}>Guardar reglas y abrir review</button>
              <button className="secondary-btn" type="button" onClick={() => goToStep("review")}>Abrir review</button>
            </div>
          </div>
        ) : null}

        {((mode === "create" && activeStep === "review") || (mode === "reconfigure" && ["review", "confirm"].includes(activeStep))) ? (
          <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{mode === "create" ? "Paso 5 · revisar impacto" : activeStep === "confirm" ? "Paso 4 · confirmar aplicación" : "Paso 2 · revisar impacto"}</div>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">{mode === "create" ? "Último checkpoint antes de aplicar el wizard" : activeStep === "confirm" ? "Confirma la mutación fuerte antes de aplicar" : "Antes del dry run, deja clarísimo el impacto"}</h3>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{mode === "create" ? "Aquí ya no solo ves preview. También guardas launch notes, playbooks, política de autopublish y un pack preview fijo con todo lo que realmente se va a sembrar antes del apply final." : "Reaplicar una industria puede resembrar reglas, agenda, followups, tono, objetivo, servicios, FAQs, integraciones y templates. Por eso ahora hay review, pack preview fijo, dry run y confirmación explícita antes del apply."}</p>

            {mode === "create" ? (
              <div className="mt-5 grid gap-4">
                <div>
                  <div className="mb-3 text-sm font-semibold text-[color:var(--text-primary)]">Playbooks sugeridos</div>
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {(recommendedPlaybooks.length ? recommendedPlaybooks : [{ key: "launch_check", label: "Revision de lanzamiento", goal: "launch" } as WizardRecommendedPlaybook]).map((item) => {
                      const id = item.key || item.label || "playbook";
                      return (
                        <CheckboxPill
                          key={id}
                          checked={selectedPlaybookKeys.includes(id)}
                          label={safeText(item.label, id)}
                          secondary={safeText(item.goal, "launch")}
                          onChange={() => setSelectedPlaybookKeys((current) => current.includes(id) ? current.filter((entry) => entry !== id) : [...current, id])}
                        />
                      );
                    })}
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="field-label md:col-span-2">Launch notes<textarea className="field-input min-h-[156px]" value={launchNotesText} onChange={(event) => setLaunchNotesText(event.target.value)} placeholder="Checklist de salida\nRiesgos conocidos\nQue validar con operaciones" /></label>
                  <label className="flex items-center gap-3 rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm text-[color:var(--text-primary)]">
                    <input type="checkbox" checked={autopublishKnowledge} onChange={(event) => setAutopublishKnowledge(event.target.checked)} />
                    Autopublicar knowledge sources sugeridas despues del apply
                  </label>
                </div>
              </div>
            ) : null}

            {mode === "reconfigure" ? (
              <>
                <div className="mt-5 rounded-[24px] border border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] p-4 text-sm leading-6 text-[color:var(--warning-text)]">
                  <strong className="text-[color:var(--text-primary)]">Esto no es un ajuste menor.</strong> Reaplicar una industria con `apply_vertical_defaults` puede reemplazar templates y recalcular configuraciones operativas del asistente operativo. Por eso el submit ya no es simple: primero hay review, luego dry run y después confirmación explícita.
                </div>
                <div className="mt-5 grid gap-4 xl:grid-cols-2">
                  <DiffCard title="Industria y tipo de operación" before={`${safeText(selectedBot?.vertical, "sin industria")} · ${safeText(currentBotSubvertical, "sin tipo de operación")}`} after={`${safeText(selectedVerticalId, "sin industria")} · ${safeText(selectedSubvertical, "sin tipo de operación")}`} status={hasReconfigurationChanges ? "replace" : "keep"} detail="La industria nueva redefine la configuración generada base y el comportamiento esperado del asistente operativo." />
                  <DiffCard title="Templates" before={summarize(currentBotTemplates, "Sin templates visibles", 5)} after={summarize(nextTemplates, "Sin templates sugeridos", 5)} status={nextTemplates.length ? "replace" : "keep"} detail="Los templates recomendados por la nueva industria pueden reemplazar la librería actual del asistente operativo." />
                  <DiffCard title="Servicios y FAQ" before={summarize(currentBotServices, "Sin servicios visibles", 5)} after={summarize(nextServices, "Sin servicios sugeridos", 5)} status={nextServices.length ? "replace" : "keep"} detail="La nueva configuración generada puede resembrar servicios base, FAQ y conocimiento operativo." />
                  <DiffCard title="Tono y objetivo" before={`${currentBotTone} · ${currentBotObjective}`} after={`${nextTone} · ${objectiveLabel(selectedPrimaryObjective)}`} status={currentBotTone !== nextTone || normalizeName(currentBotObjective) !== normalizeName(selectedPrimaryObjective) ? "replace" : "keep"} detail="Tono y objetivo pueden cambiar juntos durante la reconfiguración." />
                  <DiffCard title="Integraciones sugeridas" before={summarize(currentBotIntegrations, "Sin integraciones visibles", 5)} after={summarize(recommendedIntegrations, "Sin nuevas integraciones sugeridas", 5)} status={recommendedIntegrations.length ? "suggest" : "keep"} detail="No se conectan solas, pero el wizard deja visible lo que recomienda la nueva configuración generada." />
                  <DiffCard title="Agenda / handoff / followups" before={summarize(currentBotPolicies, "Se conserva el estado actual hasta confirmar", 5)} after={summarize(nextPolicies, "Se recalculan defaults de operacion al aplicar", 5)} status="replace" detail="Antes de mutar, el backend genera snapshot preventivo del draft del asistente operativo." />
                </div>
              </>
            ) : (
              <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Promesa</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(selectedSubverticalProfile?.promise, "Selecciona un tipo de operación para ver la promesa de la configuración generada.")}</p></div>
                <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Servicios base</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{summarize(nextServices, "Sin servicios sugeridos", 5)}</p></div>
                <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Templates sugeridos</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{summarize(nextTemplates, "Sin templates sugeridos", 5)}</p></div>
                <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">FAQ y politicas</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{summarize(parseFaqBlock(faqText).map((item) => item.q), "Sin FAQ visibles", 4)} · {summarize(parseTextBlock(policiesText), "Sin politicas visibles", 3)}</p></div>
                <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Integraciones y reglas</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{summarize(selectedIntegrationKeys, "Sin integraciones visibles", 5)} · {summarize(parseTextBlock(escalateWhenText), "Sin triggers de escalamiento", 3)}</p></div>
                <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Launch review</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{summarize(selectedPlaybookKeys, "Sin playbooks seleccionados", 4)} · {autopublishKnowledge ? "Autopublish knowledge activo" : "Autopublish manual"}</p></div>
              </div>

)}

            <div className="mt-5">
              <div className="mb-3 text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Pack preview fijo</div>
              <div className="grid gap-4 xl:grid-cols-2">
                <PackPreviewBlock
                  eyebrow="Templates que se crean"
                  title="Templates del pack"
                  description="Visibilidad explícita de los mensajes, respuestas y CTA que el apply sembrará o mantendrá."
                  createItems={packTemplateCreates}
                  reuseItems={packTemplateReuses}
                  pendingItems={mode === "create" ? packTemplateCreates : []}
                  pendingLabel={mode === "create" ? "Qué queda pendiente de aplicar" : "Qué queda pendiente"}
                  pendingFallback={mode === "create" ? "Los templates visibles se materializan al aplicar el wizard." : "No hay pendientes adicionales en templates."}
                />
                <PackPreviewBlock
                  eyebrow="Servicios que se siembran"
                  title="Servicios y catálogo"
                  description="Este bloque deja claro qué servicios se crean o se conservan dentro del setup operativo."
                  createItems={packServiceCreates}
                  reuseItems={packServiceReuses}
                  pendingItems={mode === "create" ? packServiceCreates : []}
                  pendingLabel={mode === "create" ? "Qué queda pendiente de aplicar" : "Qué queda pendiente"}
                  pendingFallback={mode === "create" ? "Los servicios visibles se siembran al aplicar el wizard." : "No hay servicios pendientes adicionales en este bloque."}
                />
                <PackPreviewBlock
                  eyebrow="Knowledge seed / FAQs / políticas"
                  title="Knowledge seed"
                  description="FAQ, políticas y fuentes ya no quedan implícitas: aquí ves qué se crea y qué se reusa del estado actual."
                  createItems={packKnowledgeCreates}
                  reuseItems={packKnowledgeReuses}
                  pendingItems={[]}
                  pendingFallback="No hay piezas adicionales pendientes dentro del seed visible."
                />
                <PackPreviewBlock
                  eyebrow="Integraciones recomendadas"
                  title="Integraciones y canales"
                  description="Separa lo ya reutilizable de lo que todavía queda pendiente de conectar en el módulo de Integraciones."
                  createItems={recommendedChannels}
                  reuseItems={packIntegrationReuses}
                  pendingItems={packIntegrationCreates}
                  createLabel="Qué recomienda el pack"
                  pendingLabel="Qué queda pendiente de conectar"
                  pendingFallback="Todo lo priorizado ya existe o queda reutilizable desde el contexto actual."
                />
              </div>
            </div>

<HandoffPreviewCard
  mode={mode}
  compare={mode === "reconfigure"}
  current={currentHandoffPreview}
  proposed={proposedHandoffPreview}
  escalateWhenText={escalateWhenText}
  onEscalateWhenChange={setEscalateWhenText}
  handoffKeywordsText={handoffKeywordsText}
  onHandoffKeywordsChange={setHandoffKeywordsText}
  handoffSlaText={handoffSlaText}
  onHandoffSlaChange={setHandoffSlaText}
  humanDestinationChannelText={humanDestinationChannelText}
  onHumanDestinationChannelChange={setHumanDestinationChannelText}
  ruleOverridesText={ruleOverridesText}
  onRuleOverridesChange={setRuleOverridesText}
  onGoToDryRun={mode === "reconfigure" && activeStep === "confirm" ? () => goToStep("dry_run") : undefined}
/>

<div className="mt-5 grid gap-3">
              {(checklist.length ? checklist : [
                { key: "vertical_pack", label: "Industria y tipo de operación definidos", completed: Boolean(selectedVerticalId && selectedSubvertical) },
                { key: "business_basics", label: "Datos base listos", completed: Boolean(businessName && botName) },
                { key: "catalog_offer", label: "Oferta conectada", completed: Boolean(parseTextBlock(servicesText).length) },
                { key: "knowledge_seed", label: "Knowledge base lista", completed: Boolean(parseFaqBlock(faqText).length) },
                { key: "integrations_rules", label: "Integraciones y reglas listas", completed: Boolean(selectedIntegrationKeys.length) },
              ]).map((item, index) => (
                <div key={safeText(item.key || item.label, `check-${index}`)} className="flex items-center justify-between gap-3 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3">
                  <span className="text-sm text-[color:var(--text-primary)]">{safeText(item.label, "Paso")}</span>
                  <span className={`mono-pill ${item.completed ? "text-[color:var(--success-text)]" : "text-[color:var(--warning-text)]"}`}>{item.completed ? "Listo" : "Pendiente"}</span>
                </div>
              ))}
            </div>

            {mode === "reconfigure" && activeStep === "confirm" ? (
              <div className="mt-5 rounded-[24px] border border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] p-4">
                <div className="text-base font-semibold text-[color:var(--text-primary)]">Confirmacion explicita</div>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Esta acción puede resembrar reglas, agenda, followups, tono, objetivo, servicios, FAQs, integraciones sugeridas y templates. El apply queda desbloqueado solo si el dry run previo no reporta conflictos bloqueantes.</p>
                <label className="mt-4 flex items-center gap-3 text-sm text-[color:var(--text-primary)]">
                  <input type="checkbox" checked={reviewConfirmed} onChange={(event) => setReviewConfirmed(event.target.checked)} />
                  Confirmo que revisé el diff, el dry run y quiero aplicar esta reconfiguración dura.
                </label>
              </div>
            ) : null}

            <div className="mt-5 flex flex-wrap gap-3">
              {mode === "reconfigure" && activeStep === "review" ? (
                <button data-testid="run-dry-run" className="primary-btn" type="button" onClick={handleRunDryRun} disabled={working || !selectedBotId || !hasReconfigurationChanges}>Correr dry run</button>
              ) : (
                <button data-testid="apply-wizard" className="primary-btn" type="button" onClick={handleApplyWizard} disabled={working || (mode === "create" ? !previewReadyForCreate : !selectedBotId || !hasReconfigurationChanges || !reviewConfirmed || !dryRunResult?.summary?.apply_ready)}>{mode === "create" ? "Aplicar wizard completo" : "Aplicar reconfiguración"}</button>
              )}
              {mode === "reconfigure" && activeStep === "confirm" ? <button className="secondary-btn" type="button" onClick={() => goToStep("dry_run")}>Volver al dry run</button> : null}
              {followUpBotId ? <Link href={`/bots/${followUpBotId}`} className="secondary-btn">Ver detalle del asistente operativo</Link> : null}
            </div>
          </div>
        ) : null}

        {mode === "reconfigure" && activeStep === "dry_run" ? (
          <div data-testid="dry-run-step" className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Paso 3 · dry run</div>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">Prevalidación antes del apply real</h3>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Aquí el backend valida la reconfiguración contra el wizard persistido antes de mutar el draft: divide el diff por dominios operativos, muestra estados, contadores, riesgos, conflictos, checklist y score de salida.</p>

            {!dryRunResult ? (
              <UiMessage title="Dry run pendiente" tone="warning">Todavía no corriste la prevalidación. Vuelve al review y ejecútala antes de confirmar.</UiMessage>
            ) : (
              <>
                <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Exit score</div><div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(dryRunResult.exit_score?.value), "0")}%</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(dryRunResult.exit_score?.label, "Sin score")}</p></div>
                  <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Apply readiness</div><div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{dryRunResult.summary?.apply_ready ? "Apto para confirmar" : "Bloqueado"}</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{dryRunResult.summary?.snapshot_required ? "Con snapshot preventivo obligatorio." : "Sin snapshot previo obligatorio."}</p></div>
                  <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Conflictos</div><div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{dryRunResult.conflicts?.length || 0}</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Bloquean el apply hasta resolverlos o volver a validar.</p></div>
                  <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Riesgos</div><div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{dryRunResult.risks?.length || 0}</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Se muestran antes del apply, no después.</p></div>
                </div>

                <ValidationSnapshotPanel
                  title="Semáforo formal antes del apply"
                  description="Esta puerta ya no es narrativa: combina contexto confirmado, handoff, canal, integración crítica, simulación y release para dejar claro si realmente puedes salir del wizard sin sorpresas."
                  snapshot={dryRunResult.validation_snapshot || null}
                />

                <VerticalScorecardPanel
                  title="Scorecard mínima por vertical"
                  description="Antes de publicar, esta scorecard revisa señales de negocio mínimas para la industria actual: intents, objeciones, handoff seguro y CTA visible."
                  snapshot={dryRunResult.validation_snapshot || null}
                />

<HandoffPreviewCard
  mode={mode}
  compare
  current={currentHandoffPreview}
  proposed={proposedHandoffPreview}
  escalateWhenText={escalateWhenText}
  onEscalateWhenChange={setEscalateWhenText}
  handoffKeywordsText={handoffKeywordsText}
  onHandoffKeywordsChange={setHandoffKeywordsText}
  handoffSlaText={handoffSlaText}
  onHandoffSlaChange={setHandoffSlaText}
  humanDestinationChannelText={humanDestinationChannelText}
  onHumanDestinationChannelChange={setHumanDestinationChannelText}
  ruleOverridesText={ruleOverridesText}
  onRuleOverridesChange={setRuleOverridesText}
/>

<div className="mt-5">
                  <div className="mb-3 text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Diff operable por dominios</div>
                  {dryRunDomains.length ? (
                    <div className="grid gap-4 xl:grid-cols-2">
                      {dryRunDomains.map((block, index) => (
                        <OperationalDiffDomainCard key={safeText(block.key || block.label, `dry-domain-${index}`)} block={block} />
                      ))}
                    </div>
                  ) : (
                    <div className="grid gap-4 xl:grid-cols-2">
                      {fallbackDryRunDiff.map((item, index) => (
                        <DiffCard
                          key={safeText(item.key || item.label, `dry-diff-${index}`)}
                          title={safeText(item.label, "Cambio")}
                          before={safeText(item.before, "Sin valor previo")}
                          after={safeText(item.after, "Sin valor siguiente")}
                          status={(item.status as "replace" | "keep" | "suggest" | "add" | "remove") || "suggest"}
                          detail={safeText(item.detail, "") || "Sin detalle adicional."}
                        />
                      ))}
                    </div>
                  )}
                </div>

                {(dryRunResult.conflicts?.length || dryRunResult.risks?.length) ? (
                  <div className="mt-5 grid gap-4 xl:grid-cols-2">
                    <div className="rounded-[24px] border border-[color:var(--danger-border)] bg-[color:var(--danger-soft)] p-4">
                      <div className="text-base font-semibold text-[color:var(--text-primary)]">Conflictos detectados</div>
                      <div className="mt-3 grid gap-3">
                        {(dryRunResult.conflicts?.length ? dryRunResult.conflicts : [{ key: "none", label: "Sin conflictos bloqueantes", detail: "El backend dejó pasar la reconfiguración hacia confirmación." }]).map((item, index) => (
                          <div key={safeText(item.key, `conflict-${index}`)} className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
                            <div className="text-sm font-semibold text-[color:var(--text-primary)]">{safeText(item.label, "Sin conflictos bloqueantes")}</div>
                            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(item.detail, "") || "Sin detalle adicional."}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-[24px] border border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] p-4">
                      <div className="text-base font-semibold text-[color:var(--text-primary)]">Riesgos del apply</div>
                      <div className="mt-3 grid gap-3">
                        {(dryRunResult.risks?.length ? dryRunResult.risks : [{ key: "none", label: "Sin riesgos relevantes", detail: "La prevalidación no detectó alertas adicionales." }]).map((item, index) => (
                          <div key={safeText(item.key, `risk-${index}`)} className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
                            <div className="text-sm font-semibold text-[color:var(--text-primary)]">{safeText(item.label, "Sin riesgos relevantes")}</div>
                            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(item.detail, "") || "Sin detalle adicional."}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : null}

                <div className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Checklist técnica del dry run</div>
                  <div className="mt-3 grid gap-3">
                    {(dryRunResult.checklist || []).map((item, index) => (
                      <div key={safeText(item.key || item.label, `dry-check-${index}`)} className="flex items-center justify-between gap-3 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-4 py-3">
                        <span className="text-sm text-[color:var(--text-primary)]">{safeText(item.label, "Checkpoint")}</span>
                        <span className={`mono-pill ${item.completed ? "text-[color:var(--success-text)]" : item.required ? "text-[color:var(--danger-text)]" : "text-[color:var(--warning-text)]"}`}>{item.completed ? "Listo" : item.required ? "Bloquea" : "Pendiente"}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            <div className="mt-5 flex flex-wrap gap-3">
              <button data-testid="rerun-dry-run" className="primary-btn" type="button" onClick={handleRunDryRun} disabled={working || !selectedBotId || !hasReconfigurationChanges}>{working ? "Corriendo dry run..." : "Volver a correr dry run"}</button>
              <button data-testid="continue-confirmation" className="secondary-btn" type="button" onClick={() => goToStep("confirm")} disabled={!dryRunResult?.summary?.apply_ready}>Ir a confirmación final</button>
              <button className="secondary-btn" type="button" onClick={() => goToStep("review")}>Volver al review</button>
            </div>
          </div>
        ) : null}

        {postApplyBotId && activeStep === "simulate" ? (
          <div data-testid="simulate-step" className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Paso {mode === "create" ? "6" : "4"} · simular</div>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">Valida el draft después del impacto, no antes</h3>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">La prueba ya no compite visualmente con la decisión de industria. Primero cierras el setup y el review; luego corres una validación guiada con el asistente operativo explícito.</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="field-label">Título del caso
                <input data-testid="simulation-title-input" className="field-input" value={simulationTitle} onChange={(event) => setSimulationTitle(event.target.value)} placeholder="Validación de agendado" />
              </label>
              <label className="field-label">Acción esperada
                <select data-testid="simulation-expected-action" className="field-input" value={simulationExpectedAction} onChange={(event) => setSimulationExpectedAction(event.target.value)}><option value="">Sin validar acción fija</option><option value="reply">Responder</option><option value="schedule">Agendar</option><option value="sell">Vender</option><option value="payment">Cobro</option><option value="handoff">Handoff</option></select>
              </label>
              <label className="field-label md:col-span-2">Escenario
                <textarea data-testid="simulation-scenario-input" className="field-input min-h-[156px]" value={simulationScenario} onChange={(event) => setSimulationScenario(event.target.value)} placeholder="Hola, quiero precio y saber si me pueden agendar esta semana." />
              </label>
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Compare target</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{mode === "reconfigure" ? "Published: la simulación compara contra la versión publicada para detectar cambio real." : "Draft: la simulación valida el nuevo asistente operativo recién creado."}</p></div>
              <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Rollback</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{mode === "reconfigure" ? "El snapshot preventivo ya quedó encapsulado antes del apply. Úsalo desde versiones si detectas regresión." : "En un asistente operativo nuevo no hay rollback de draft previo, pero sí trazabilidad del wizard y versiones posteriores."}</p></div>
              <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Trazabilidad</div><p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Versiones, simulación y publish siguen viviendo desde el asistente operativo explícito, ya sin competir con la selección de industria.</p></div>
            </div>

            {simulationError ? <UiMessage title="Simulación pendiente" tone="warning">{simulationError}</UiMessage> : null}
            {simulationResult ? (
              <div data-testid="simulation-result" className="mt-4 rounded-[24px] border border-[color:var(--success-border)] bg-[color:var(--success-soft)] p-4">
                <div className="text-base font-semibold text-[color:var(--text-primary)]">Simulación completada</div>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Pass rate: {safeText(String(asRecord(simulationResult.summary).pass_rate), "0")}% · casos: {safeText(String(asRecord(simulationResult.summary).cases_total), "1")} · cambios vs baseline: {safeText(String(asRecord(simulationResult.summary).changed_vs_baseline), "0")}</p>
              </div>
            ) : null}

            <div className="mt-5 flex flex-wrap gap-3">
              <button data-testid="run-simulation" className="primary-btn" type="button" onClick={handleRunSimulation} disabled={simulationRunning}>{simulationRunning ? "Corriendo simulación..." : "Crear caso y correr simulación"}</button>
              <button data-testid="go-publish" className="secondary-btn" type="button" onClick={() => goToStep("publish")}>Seguir a publicar</button>
              <Link href={`/bots/${postApplyBotId}/versions`} className="secondary-btn">Revisar versiones</Link>
            </div>
          </div>
        ) : null}

        {postApplyBotId && activeStep === "publish" ? (
          <div data-testid="publish-step" className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Paso {mode === "create" ? "7" : "5"} · siguiente acción</div>
            <SuccessState
              title={mode === "create" ? "Asistente operativo aplicado y guiado a la operación" : "Reconfiguración aplicada con salida operativa clara"}
              description={mode === "create"
                ? "El wizard ya no se siente terminado en falso. Después del apply se queda como torre de control, muestra progreso restante y deja elegir entre seguir dentro del wizard o salir al siguiente módulo."
                : "El cambio ya pasó por review, dry run, confirmación y apply. Ahora el cierre del wizard deja dos caminos explícitos: seguir aquí con acompañamiento o salir al módulo dueño del siguiente paso operativo."}
              actions={<div className="flex flex-wrap gap-3"><button className={postApplyPath === "wizard" ? "primary-btn" : "secondary-btn"} type="button" onClick={() => setPostApplyPath("wizard")}>Seguir en el wizard</button><button className={postApplyPath === "module" ? "primary-btn" : "secondary-btn"} type="button" onClick={() => setPostApplyPath("module")}>Salir al siguiente módulo</button></div>}
            />

            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              <div className={`rounded-[24px] border p-4 ${postApplyPath === "wizard" ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)]" : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)]"}`}>
                <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Camino 1</div>
                <h4 className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">Seguir en el wizard</h4>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Mantén aquí la checklist formal, la scorecard de negocio y el progreso restante. Este modo evita la sensación de cierre prematuro mientras todavía faltan conectar, probar, publicar u operar.</p>
                <div className="mt-4 flex flex-wrap gap-3">
                  {nextBestAction?.key === "run_simulation" ? (
                    <button className="primary-btn" type="button" onClick={() => { setPostApplyPath("wizard"); goToStep("simulate"); }}>Ir a simulación dentro del wizard</button>
                  ) : (
                    <button className={postApplyPath === "wizard" ? "primary-btn" : "secondary-btn"} type="button" onClick={() => setPostApplyPath("wizard")}>Quedarme aquí</button>
                  )}
                  <button className="secondary-btn" type="button" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>Volver al resumen</button>
                </div>
              </div>
              <div className={`rounded-[24px] border p-4 ${postApplyPath === "module" ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)]" : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)]"}`}>
                <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Camino 2</div>
                <h4 className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">Salir al siguiente módulo</h4>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Lleva el contexto al módulo dueño del siguiente paso operativo. Hoy el owner es <strong className="text-[color:var(--text-primary)]">{nextBestActionModule}</strong>.</p>
                <div className="mt-4 flex flex-wrap gap-3">
                  {canExitToNextModule && nextBestAction?.href ? (
                    <Link href={nextBestAction.href} className="primary-btn" onClick={() => setPostApplyPath("module")}>Salir a {nextBestActionModule}</Link>
                  ) : canExitToNextModule ? (
                    <button className="primary-btn" type="button" onClick={() => setPostApplyPath("module")}>Preparar salida</button>
                  ) : (
                    <button className="secondary-btn" type="button" onClick={() => setPostApplyPath("module")} disabled>La siguiente acción sigue aquí</button>
                  )}
                  <p className="text-sm leading-6 text-[color:var(--text-secondary)]">{canExitToNextModule ? "Úsalo cuando quieras abandonar el wizard y ejecutar el siguiente paso en el módulo correcto." : "Todavía no conviene salir: la siguiente acción vive dentro del wizard porque falta probar el cambio."}</p>
                </div>
              </div>
            </div>

            <div className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Progreso restante</div>
                  <h4 className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">Conectar → probar → publicar → operar</h4>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Quedan {remainingProgressCount} hitos sin cerrar. El wizard sigue visible para que nunca pierdas el contexto del camino completo.</p>
                </div>
                <span className="rounded-full border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--text-primary)]">{postApplyPath === "wizard" ? "Modo wizard" : "Salida a módulo"}</span>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {remainingProgressSteps.map((item) => {
                  const meta = progressStatusMeta(item.status);
                  return (
                    <div key={item.key} className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="text-sm font-semibold text-[color:var(--text-primary)]">{item.label}</div>
                        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${meta.tone}`}>{meta.pill}</span>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{item.detail}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            <ValidationSnapshotPanel
              title="Puerta formal de salida"
              description="Esta checklist deja claro si el cambio realmente ya puede salir a operar: contexto, pack, handoff, canal, integración crítica, simulación básica y release en una sola vista con semáforo."
              snapshot={liveValidationSnapshot}
            />

            <VerticalScorecardPanel
              title="Scorecard mínima por vertical"
              description="Antes de publicar, esta scorecard valida cobertura de intents, objeciones, handoff seguro y CTA visible para la industria actual."
              snapshot={liveValidationSnapshot}
            />

            <div className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Next best action</div>
              <h4 className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">{safeText(nextBestAction?.title, "Revisar versiones")}</h4>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{postApplyPath === "wizard" ? "Sigues dentro del wizard, así que este CTA funciona como guía del próximo paso y no como cierre definitivo." : "Elegiste salir al siguiente módulo. Este CTA ya apunta al owner correcto del siguiente paso operativo."} {safeText(nextBestAction?.description, "El wizard ya aplicó el cambio. Revisa las versiones para continuar.")}</p>

              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Canal</div>
                  <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{hasConnectedChannel ? "Conectado" : "Pendiente"}</div>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{hasConnectedChannel ? "Ya hay un canal operativo visible para este asistente operativo." : "Todavía no se ve un canal operativo listo para salida."}</p>
                </div>
                <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Prueba</div>
                  <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{hasApprovedSimulationAfterApply ? "Aprobada" : hasSimulationAfterApply ? "Revisar" : "Pendiente"}</div>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{hasApprovedSimulationAfterApply ? `Pass rate ${safeText(String(latestSimulationPassRate), "0")}% después del apply actual.` : hasSimulationAfterApply ? `Ya existe simulación posterior al apply, pero todavía no quedó aprobada (${safeText(String(latestSimulationPassRate), "0")}%).` : "Todavía falta una simulación posterior al apply actual."}</p>
                </div>
                <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Release</div>
                  <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{hasPublishedReleaseAfterApply ? "Publicado" : hasApprovedSimulationAfterApply && hasConnectedChannel ? "Listo para publicar" : hasReleaseRequestAfterApply ? "En proceso" : "Pendiente"}</div>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{hasPublishedReleaseAfterApply ? "Este apply ya llegó a publish." : hasApprovedSimulationAfterApply && hasConnectedChannel ? "La salida ya cumplió los gates operativos y solo falta publicar release." : hasReleaseRequestAfterApply ? "Ya existe un release posterior al apply, pero todavía no queda publicado." : "Todavía no existe release posterior al apply actual."}</p>
                </div>
              </div>

              {postApplyError ? <UiMessage title="Estado operativo parcial" tone="warning">{postApplyError}</UiMessage> : null}
              {postApplyLoading ? <p className="mt-4 text-sm leading-6 text-[color:var(--text-secondary)]">Calculando siguiente mejor acción...</p> : null}

              <div className="mt-5 flex flex-wrap gap-3">
                {nextBestAction?.key === "run_simulation" ? (
                  <button className="primary-btn" type="button" onClick={() => { setPostApplyPath("wizard"); goToStep("simulate"); }}>{nextBestAction.ctaLabel}</button>
                ) : nextBestAction?.href ? (
                  <Link href={nextBestAction.href} className="primary-btn" onClick={() => setPostApplyPath(canExitToNextModule ? "module" : "wizard")}>{nextBestAction.ctaLabel}</Link>
                ) : (
                  <Link href={`/bots/${postApplyBotId}/versions`} className="primary-btn">Revisar versiones</Link>
                )}
                {secondaryNextActions.map((item) => item.href ? (
                  <Link key={item.key} href={item.href} className="secondary-btn">{item.label}</Link>
                ) : (
                  <button key={item.key} className="secondary-btn" type="button" onClick={item.action}>{item.label}</button>
                ))}
              </div>
            </div>

            {mode === "reconfigure" ? (
              <div data-testid="simulate-step" className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Verificación final opcional</div>
                <h4 className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">Simulación post-apply</h4>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Esta simulación ya no decide si se puede aplicar. Solo sirve como verificación final después del dry run y del apply real.</p>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="field-label">Título del caso
                    <input data-testid="simulation-title-input" className="field-input" value={simulationTitle} onChange={(event) => setSimulationTitle(event.target.value)} placeholder="Verificación final de reconfiguración" />
                  </label>
                  <label className="field-label">Acción esperada
                    <select data-testid="simulation-expected-action" className="field-input" value={simulationExpectedAction} onChange={(event) => setSimulationExpectedAction(event.target.value)}><option value="">Sin validar acción fija</option><option value="reply">Responder</option><option value="schedule">Agendar</option><option value="sell">Vender</option><option value="payment">Cobro</option><option value="handoff">Handoff</option></select>
                  </label>
                  <label className="field-label md:col-span-2">Escenario
                    <textarea data-testid="simulation-scenario-input" className="field-input min-h-[156px]" value={simulationScenario} onChange={(event) => setSimulationScenario(event.target.value)} placeholder="Hola, quiero precio y saber si me pueden agendar esta semana." />
                  </label>
                </div>
                {simulationError ? <UiMessage title="Simulación pendiente" tone="warning">{simulationError}</UiMessage> : null}
                {simulationResult ? (
                  <div data-testid="simulation-result" className="mt-4 rounded-[24px] border border-[color:var(--success-border)] bg-[color:var(--success-soft)] p-4">
                    <div className="text-base font-semibold text-[color:var(--text-primary)]">Simulación completada</div>
                    <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Pass rate: {safeText(String(asRecord(simulationResult.summary).pass_rate), "0")}% · casos: {safeText(String(asRecord(simulationResult.summary).cases_total), "1")} · cambios vs baseline: {safeText(String(asRecord(simulationResult.summary).changed_vs_baseline), "0")}</p>
                  </div>
                ) : null}
                <div className="mt-4 flex flex-wrap gap-3">
                  <button data-testid="run-simulation" className="secondary-btn" type="button" onClick={handleRunSimulation} disabled={simulationRunning}>{simulationRunning ? "Corriendo simulación..." : "Correr verificación final"}</button>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="grid gap-6">
        <StickySummaryRail
          mode={mode}
          organizationName={safeText(selectedOrganization?.name, "")}
          industry={safeText(catalogVertical?.name, safeText(selectedVerticalId, ""))}
          operationType={safeText(selectedSubverticalProfile?.name, safeText(selectedSubvertical, ""))}
          objective={objectiveLabel(selectedPrimaryObjective)}
          businessName={businessName.trim()}
          assistantName={safeText(selectedBot?.name, botName.trim())}
          recommendedChannels={recommendedChannels}
          seededServices={summarySeededServices}
          createdTemplates={summaryTemplates}
          readinessScore={draftReadinessScore}
          readinessLabel={draftReadinessLabel}
          readinessTone={draftReadinessTone}
          risks={missingSummaryItems}
        />

        <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Estado persistido</div>
          <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">Ahora el frontend sí vive montado sobre el motor de wizard</h3>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Industria y tipo de operación usan blueprint reactivo. Los avances reales se guardan con wizard_id, el paso actual también vive en la URL y el autosave ya recupera el formulario exacto al recargar, no solo el estado principal.</p>
          <div className="mt-4 grid gap-3">
            <div className="surface-row"><span>Wizard id</span><strong>{safeText(wizardId, "todavía no iniciado")}</strong></div>
            <div className="surface-row"><span>Status</span><strong>{safeText(wizard?.status, "draft local")}</strong></div>
            <div className="surface-row"><span>Paso actual</span><strong>{safeText(wizard?.current_step || blueprint?.current_step, "vertical_fit")}</strong></div>
            <div className="surface-row"><span>Asistente operativo explícito</span><strong>{safeText(selectedBot?.name, mode === "create" ? "se creará al aplicar" : "pendiente")}</strong></div>
            <div className="surface-row"><span>Progress</span><strong>{safeText(String(wizard?.progress_percent ?? blueprint?.progress_percent ?? 0), "0")}%</strong></div>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <button className="secondary-btn" type="button" onClick={() => { resetTransientState(mode); updateUrl({ mode, botId: mode === "reconfigure" ? selectedBotId : "", clearWizard: true }); }}>Empezar wizard nuevo</button>
            <Link href="/onboarding" className="secondary-btn">Ver readiness</Link>
          </div>
        </div>

        <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Qué guarda el backend</div>
          <div className="mt-4 grid gap-4 text-sm leading-6 text-[color:var(--text-secondary)]">
            <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><strong className="text-[color:var(--text-primary)]">vertical_fit</strong><br />vertical_id (industria), subvertical (tipo de operación) y primary_objective.</div>
            <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><strong className="text-[color:var(--text-primary)]">business_basics</strong><br />business_name, bot_name, tone, language, timezone, hours y WhatsApp del asistente operativo.</div>
            <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><strong className="text-[color:var(--text-primary)]">catalog_offer</strong><br />services, featured_offers, primary_ctas y pricing_notes.</div>
            <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><strong className="text-[color:var(--text-primary)]">knowledge_seed</strong><br />FAQ, políticas y knowledge_sources iniciales.</div>
            <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><strong className="text-[color:var(--text-primary)]">integrations_rules</strong><br />selected_integrations, escalate_when, handoff_keywords y overrides.</div>
            <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4"><strong className="text-[color:var(--text-primary)]">launch_review + apply</strong><br />playbooks, launch_notes, autopublish_knowledge y aplicación final. Si es un asistente operativo nuevo, el backend lo crea; si es existente, genera snapshot y luego aplica la configuración generada.</div>
          </div>
        </div>
      </div>
    </div>
  );
}
