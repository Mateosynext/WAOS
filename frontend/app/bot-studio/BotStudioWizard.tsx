"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useActionState, useEffect, useMemo, useState, type ReactNode } from "react";
import { applyBotVerticalAction, createBotAction } from "../actions";
import type { BotStudioActionState } from "../actions/bots";
import { SuccessState } from "../components";
import { UiMessage } from "../components/UiMessage";
import type { BotContract, SessionOrganization, VerticalProfileContract } from "../lib/contracts";
import { safeText } from "../lib/ui";
import SubverticalPicker from "./SubverticalPicker";
import VerticalPicker from "./VerticalPicker";
import type { WizardBlueprint, WizardMode, WizardSubverticalProfile } from "./wizard-types";

type BotStudioWizardProps = {
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
};

type ObjectiveValue = "agendar" | "vender" | "calificar" | "responder" | "reactivar";

const OBJECTIVES: ObjectiveValue[] = ["agendar", "vender", "calificar", "responder", "reactivar"];
const initialActionState: BotStudioActionState = { ok: false };

function normalizeObjective(value: unknown): ObjectiveValue {
  const normalized = String(value || "").trim().toLowerCase();
  return OBJECTIVES.includes(normalized as ObjectiveValue) ? (normalized as ObjectiveValue) : "agendar";
}

function objectiveLabel(value: string) {
  switch (normalizeObjective(value)) {
    case "agendar":
      return "Agendar";
    case "vender":
      return "Vender";
    case "calificar":
      return "Calificar";
    case "responder":
      return "Responder";
    case "reactivar":
      return "Reactivar";
    default:
      return "Agendar";
  }
}

function titleCase(value: string) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : value;
}

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function normalizeName(value: string) {
  return value.trim().toLowerCase();
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? { ...(value as Record<string, unknown>) } : {};
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

function pickBotTone(bot?: BotContract | null) {
  return readNestedString(bot?.config_draft, ["personality", "tone"], safeText(bot?.tone, "Sin tono visible"));
}

function pickBotServices(bot?: BotContract | null) {
  return readNestedStrings(bot?.config_draft, ["business_knowledge", "services"]);
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

function pickTemplateLabels(blueprint: WizardBlueprint | null, activeSubverticalProfile: WizardSubverticalProfile | null, activeVerticalProfile: VerticalProfileContract | null) {
  const setupTemplates = Array.isArray(asRecord(blueprint?.setup).response_templates) ? asRecord(blueprint?.setup).response_templates as Array<Record<string, unknown>> : [];
  return unique([
    ...setupTemplates.map((item) => String(item.title || item.template_key || item.key || "").trim()),
    ...(activeSubverticalProfile?.templates || []).map((item) => String(item.title || item.template_key || item.key || item.name || "").trim()),
    ...((asRecord(activeVerticalProfile?.pipeline).templates || []) as Array<Record<string, unknown>>).map((item) => String(item.title || item.template_key || item.key || item.name || "").trim()),
  ]);
}

function pickNextTone(blueprint: WizardBlueprint | null, activeVerticalProfile: VerticalProfileContract | null) {
  return readNestedString(blueprint?.setup, ["personality", "tone"], readNestedString(blueprint?.setup, ["behavior_settings", "tone"], safeText(activeVerticalProfile?.short_name, "según defaults de vertical")));
}

function pickSubverticalOptions(blueprint: WizardBlueprint | null, catalogVertical?: VerticalProfileContract | null) {
  return unique([
    blueprint?.selected_subvertical?.name,
    blueprint?.setup?.wizard?.selected_subvertical,
    ...(blueprint?.profile?.recommended_subverticals || []),
    ...(blueprint?.profile?.subverticals || []),
    catalogVertical?.selected_subvertical?.name,
    ...(catalogVertical?.recommended_subverticals || []),
    ...(catalogVertical?.subvertical_profiles || []).map((item) => item.name),
    ...(catalogVertical?.subverticals || []),
  ]);
}

function pickRecommendedCtas(blueprint: WizardBlueprint | null, objective: ObjectiveValue) {
  const labels = unique((blueprint?.setup?.wizard?.recommended_ctas || []).map((item) => item.label));
  if (labels.length) return labels;
  if (objective === "vender") return ["Ver plan o precio", "Hablar con asesor", "Cerrar compra"];
  if (objective === "calificar") return ["Responder preguntas clave", "Hablar con asesor", "Continuar evaluación"];
  if (objective === "reactivar") return ["Retomar conversación", "Ver oferta vigente", "Hablar con asesor"];
  if (objective === "responder") return ["Resolver duda", "Ver servicios", "Hablar con asesor"];
  return ["Agendar ahora", "Ver plan o precio", "Hablar con asesor"];
}

function pickRecommendedIntegrations(blueprint: WizardBlueprint | null, catalogVertical?: VerticalProfileContract | null) {
  const fromBlueprint = unique((blueprint?.setup?.wizard?.recommended_integrations || []).map((item) => item.name || item.provider || item.integration_key));
  return fromBlueprint.length ? fromBlueprint : unique(catalogVertical?.recommended_integrations || []);
}

function pickPlaybooks(blueprint: WizardBlueprint | null, catalogVertical?: VerticalProfileContract | null) {
  const fromBlueprint = unique((blueprint?.setup?.wizard?.recommended_playbooks || []).map((item) => item.label));
  return fromBlueprint.length ? fromBlueprint : unique(catalogVertical?.flows || []);
}

function summarize(values: Array<string | null | undefined>, fallback: string, limit = 4) {
  const cleaned = unique(values).slice(0, limit);
  return cleaned.length ? cleaned.join(" · ") : fallback;
}

function buildSubverticalProfiles(verticalProfile: VerticalProfileContract | null, blueprint: WizardBlueprint | null, catalogVertical: VerticalProfileContract | null) {
  if (verticalProfile?.subvertical_profiles?.length) return verticalProfile.subvertical_profiles as WizardSubverticalProfile[];
  if (catalogVertical?.subvertical_profiles?.length) return catalogVertical.subvertical_profiles as WizardSubverticalProfile[];
  return pickSubverticalOptions(blueprint, catalogVertical).map((name) => ({
    id: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
    name,
  }));
}

function resolveActiveSubverticalProfile(args: {
  selectedSubvertical: string;
  verticalProfile: VerticalProfileContract | null;
  blueprint: WizardBlueprint | null;
  subverticalProfiles: WizardSubverticalProfile[];
}) {
  const selected = normalizeName(args.selectedSubvertical);
  const match = (value?: string | null) => normalizeName(String(value || "")) === selected;

  return args.verticalProfile?.selected_subvertical && (!selected || match(args.verticalProfile.selected_subvertical.name))
    ? args.verticalProfile.selected_subvertical as WizardSubverticalProfile
    : args.subverticalProfiles.find((item) => !selected || match(item.name))
    || args.blueprint?.selected_subvertical
    || args.subverticalProfiles[0]
    || null;
}

async function fetchWizardBlueprint(params: URLSearchParams): Promise<WizardBlueprint> {
  const response = await fetch(`/api/onboarding/wizard/blueprint?${params.toString()}`, {
    method: "GET",
    cache: "no-store",
    credentials: "same-origin",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = typeof payload?.detail === "string" ? payload.detail : `La UI no pudo actualizar el blueprint (${response.status}).`;
    throw new Error(detail);
  }
  return response.json();
}

async function fetchWizardVerticalProfile(params: URLSearchParams): Promise<VerticalProfileContract> {
  const response = await fetch(`/api/onboarding/wizard/vertical-profile?${params.toString()}`, {
    method: "GET",
    cache: "no-store",
    credentials: "same-origin",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = typeof payload?.detail === "string" ? payload.detail : `La UI no pudo cargar el perfil vertical (${response.status}).`;
    throw new Error(detail);
  }
  return response.json();
}

function cardClasses(active: boolean) {
  return active
    ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] text-[color:var(--text-primary)]"
    : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-secondary)]";
}

function StepRail({ title, steps }: { title: string; steps: string[] }) {
  return (
    <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{title}</div>
      <div className="mt-4 grid gap-3">
        {steps.map((step, index) => (
          <div key={`${title}-${step}`} className="flex items-start gap-3 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-4 py-3">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-xs font-semibold text-[color:var(--text-primary)]">{index + 1}</span>
            <span className="text-sm leading-6 text-[color:var(--text-secondary)]">{step}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function NextStepCard({ title, description, action }: { title: string; description: string; action: ReactNode }) {
  return (
    <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
      <div className="text-base font-semibold text-[color:var(--text-primary)]">{title}</div>
      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
      <div className="mt-4 flex flex-wrap gap-2">{action}</div>
    </div>
  );
}

type DiffStatus = "replace" | "keep" | "suggest";

function ImpactBadge({ status }: { status: DiffStatus }) {
  const label = status === "replace" ? "se reemplaza" : status === "keep" ? "se conserva" : "se sugiere";
  const classes = status === "replace"
    ? "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] text-[color:var(--text-primary)]"
    : status === "keep"
      ? "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--text-primary)]"
      : "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] text-[color:var(--text-primary)]";

  return <span className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${classes}`}>{label}</span>;
}

function DiffField({
  label,
  status,
  before,
  after,
  detail,
}: {
  label: string;
  status: DiffStatus;
  before: string;
  after: string;
  detail?: string;
}) {
  return (
    <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-semibold text-[color:var(--text-primary)]">{label}</div>
        <ImpactBadge status={status} />
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Antes</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{before}</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Después</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{after}</p>
        </div>
      </div>
      {detail ? <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{detail}</p> : null}
    </div>
  );
}

export default function BotStudioWizard({
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
}: BotStudioWizardProps) {
  const router = useRouter();
  const organizationsById = useMemo(() => Object.fromEntries(organizations.map((item) => [item.id, item])), [organizations]);
  const verticalsById = useMemo(() => Object.fromEntries(verticals.map((item) => [item.id, item])), [verticals]);
  const botsById = useMemo(() => Object.fromEntries(bots.map((item) => [item.id, item])), [bots]);

  const [mode, setMode] = useState<WizardMode>(initialMode);
  const [selectedBotId, setSelectedBotId] = useState(initialSelectedBotId || "");
  const [selectedOrganizationId, setSelectedOrganizationId] = useState(initialOrganizationId || "");
  const [selectedVerticalId, setSelectedVerticalId] = useState(initialVerticalId || "");
  const [selectedSubvertical, setSelectedSubvertical] = useState(initialSubvertical || "");
  const [selectedPrimaryObjective, setSelectedPrimaryObjective] = useState<ObjectiveValue>(normalizeObjective(initialPrimaryObjective));
  const [businessName, setBusinessName] = useState(organizationsById[initialOrganizationId]?.name || "");
  const [botName, setBotName] = useState("");
  const [tone, setTone] = useState("amable");
  const [language, setLanguage] = useState("es");
  const [timezone, setTimezone] = useState(organizationsById[initialOrganizationId]?.timezone || "America/Mexico_City");
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [hours, setHours] = useState("");
  const [publishNow, setPublishNow] = useState(true);
  const [blueprint, setBlueprint] = useState<WizardBlueprint | null>(initialBlueprint);
  const [verticalProfile, setVerticalProfile] = useState<VerticalProfileContract | null>(initialVerticalProfile);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [createState, createFormAction, createPending] = useActionState(createBotAction, initialActionState);
  const [reconfigureState, reconfigureFormAction, reconfigurePending] = useActionState(applyBotVerticalAction, initialActionState);
  const [reviewStageOpen, setReviewStageOpen] = useState(false);
  const [reviewConfirmed, setReviewConfirmed] = useState(false);

  const selectedOrganization = selectedOrganizationId ? organizationsById[selectedOrganizationId] || null : null;
  const selectedBot = selectedBotId ? botsById[selectedBotId] || null : null;
  const catalogVertical = selectedVerticalId ? verticalsById[selectedVerticalId] || null : null;
  const activeVerticalProfile = verticalProfile || catalogVertical || null;
  const subverticalProfiles = useMemo(() => buildSubverticalProfiles(verticalProfile, blueprint, catalogVertical), [verticalProfile, blueprint, catalogVertical]);
  const subverticalOptions = useMemo(() => unique(subverticalProfiles.map((item) => item.name)), [subverticalProfiles]);
  const activeSubverticalProfile = useMemo(() => resolveActiveSubverticalProfile({
    selectedSubvertical,
    verticalProfile,
    blueprint,
    subverticalProfiles,
  }), [selectedSubvertical, verticalProfile, blueprint, subverticalProfiles]);

  const previewVerticalName = safeText(blueprint?.profile?.name, safeText(activeVerticalProfile?.name, "Vertical"));
  const previewVerticalProblem = safeText(blueprint?.profile?.problem, safeText(activeVerticalProfile?.problem, "Selecciona vertical, subvertical y objetivo para ver el encuadre operativo."));
  const previewSubverticalName = safeText(activeSubverticalProfile?.name, safeText(blueprint?.setup?.wizard?.selected_subvertical || selectedSubvertical, safeText(pickCatalogSubvertical(activeVerticalProfile), "Sin subvertical")));
  const previewPromise = safeText(activeSubverticalProfile?.promise, safeText(blueprint?.selected_subvertical?.promise, previewVerticalProblem));
  const recommendedCtas = pickRecommendedCtas(blueprint, selectedPrimaryObjective);
  const recommendedIntegrations = pickRecommendedIntegrations(blueprint, activeVerticalProfile);
  const recommendedPlaybooks = pickPlaybooks(blueprint, activeVerticalProfile);
  const checklist = blueprint?.checklist || [];
  const canSubmit = Boolean(selectedOrganizationId && selectedVerticalId && selectedSubvertical);
  const createCompletedBotId = createState.ok ? String(createState.botId || "") : "";
  const followUpBotId = createCompletedBotId || selectedBotId;
  const selectedBotTenant = selectedBot ? organizationsById[selectedBot.organization_id] || null : null;
  const currentBotSubvertical = pickBotSubvertical(selectedBot, selectedBotTenant || selectedOrganization);
  const currentBotVerticalId = safeText(selectedBot?.vertical, "");
  const currentBotVertical = safeText(verticalsById[currentBotVerticalId]?.name, safeText(selectedBot?.vertical, "Sin vertical"));
  const currentBotObjectiveValue = normalizeObjective(selectedBot?.objective || selectedBot?.goal || "agendar");
  const currentBotObjective = objectiveLabel(currentBotObjectiveValue);
  const currentBotTone = pickBotTone(selectedBot);
  const currentBotServices = pickBotServices(selectedBot);
  const currentBotIntegrationKeys = pickBotIntegrationKeys(selectedBot);
  const currentBotTemplateLabels = pickBotTemplateLabels(selectedBot);
  const nextTone = pickNextTone(blueprint, activeVerticalProfile);
  const nextTemplateLabels = pickTemplateLabels(blueprint, activeSubverticalProfile, activeVerticalProfile);
  const nextServices = unique([
    ...readNestedStrings(blueprint?.setup, ["services"]),
    ...(activeSubverticalProfile?.service_bundle || []),
  ]);
  const verticalStatus: DiffStatus = normalizeName(currentBotVerticalId) === normalizeName(selectedVerticalId) ? "keep" : "replace";
  const subverticalStatus: DiffStatus = normalizeName(currentBotSubvertical) === normalizeName(selectedSubvertical) ? "keep" : "replace";
  const objectiveStatus: DiffStatus = normalizeName(currentBotObjectiveValue) === normalizeName(selectedPrimaryObjective) ? "keep" : "replace";
  const templateStatus: DiffStatus = nextTemplateLabels.length ? "replace" : "suggest";
  const servicesStatus: DiffStatus = nextServices.length ? "replace" : "suggest";
  const toneStatus: DiffStatus = normalizeName(currentBotTone) === normalizeName(nextTone) ? "keep" : "replace";
  const integrationsStatus: DiffStatus = recommendedIntegrations.length ? "suggest" : "keep";
  const operationsStatus: DiffStatus = "replace";
  const hasReconfigurationChanges = Boolean(
    selectedBot
    && (
      normalizeName(currentBotVerticalId) !== normalizeName(selectedVerticalId)
      || normalizeName(currentBotSubvertical) !== normalizeName(selectedSubvertical)
      || normalizeName(currentBotObjectiveValue) !== normalizeName(selectedPrimaryObjective)
    )
  );

  const createSteps = [
    "Elegir tenant para el nuevo bot.",
    "Elegir vertical y bajar a subvertical obligatoria.",
    "Definir básicos: objetivo, nombre, tono, idioma y horario.",
    "Revisar el pack generado antes de crear.",
    "Crear sin salir de esta vista y seguir a canal, simulación o publicación.",
  ];
  const reconfigureSteps = [
    "Elegir el bot que vas a reconfigurar.",
    "Ver la vertical actual y escoger la nueva vertical/subvertical.",
    "Revisar el diff e impacto antes de aplicar.",
    "Generar snapshot previo y confirmar la aplicación.",
    "Seguir a simulación, canal o publicación sin brincar a otra pantalla.",
  ];

  function handleOrganizationChange(nextOrganizationId: string) {
    setSelectedOrganizationId(nextOrganizationId);
    const organization = organizationsById[nextOrganizationId] || null;
    if (mode === "create") {
      const nextVerticalId = selectedVerticalId || organization?.vertical || "";
      const nextCatalogVertical = nextVerticalId ? verticalsById[nextVerticalId] || null : null;
      if (!selectedVerticalId) setSelectedVerticalId(nextVerticalId);
      if (!selectedSubvertical) setSelectedSubvertical(organization?.subvertical || pickCatalogSubvertical(nextCatalogVertical));
      setTimezone(organization?.timezone || "America/Mexico_City");
      if (organization?.name) setBusinessName((current) => current || organization.name);
    }
  }

  function handleVerticalChange(nextVerticalId: string) {
    setSelectedVerticalId(nextVerticalId);
    const nextCatalogVertical = nextVerticalId ? verticalsById[nextVerticalId] || null : null;
    setSelectedSubvertical(pickCatalogSubvertical(nextCatalogVertical));
  }

  useEffect(() => {
    if (!selectedOrganizationId) setSelectedOrganizationId("");
  }, [organizations, selectedOrganizationId]);

  useEffect(() => {
    if (mode !== "reconfigure") return;
    const activeBot = selectedBotId ? botsById[selectedBotId] || null : null;
    if (!activeBot) return;
    const organization = organizationsById[activeBot.organization_id] || null;
    const nextVerticalId = activeBot.vertical || organization?.vertical || "";
    const nextCatalogVertical = nextVerticalId ? verticalsById[nextVerticalId] || null : null;
    setSelectedOrganizationId(activeBot.organization_id || organization?.id || selectedOrganizationId);
    setSelectedVerticalId(nextVerticalId);
    setSelectedSubvertical(pickBotSubvertical(activeBot, organization) || pickCatalogSubvertical(nextCatalogVertical));
    setSelectedPrimaryObjective(normalizeObjective(activeBot.objective || activeBot.goal));
    setTimezone(safeText(activeBot.timezone, organization?.timezone || "America/Mexico_City"));
  }, [botsById, mode, organizationsById, selectedBotId, selectedOrganizationId, verticals, verticalsById]);

  useEffect(() => {
    if (selectedSubvertical && subverticalOptions.some((item) => normalizeName(item) === normalizeName(selectedSubvertical))) return;
    setSelectedSubvertical(subverticalOptions[0] || "");
  }, [selectedSubvertical, subverticalOptions]);

  useEffect(() => {
    if (createState.ok && createState.botId) {
      setSelectedBotId(String(createState.botId));
      if (createState.organizationId) setSelectedOrganizationId(String(createState.organizationId));
    }
  }, [createState.botId, createState.ok, createState.organizationId]);

  useEffect(() => {
    if (mode !== "reconfigure") {
      setReviewStageOpen(false);
      setReviewConfirmed(false);
      return;
    }
    setReviewStageOpen(false);
    setReviewConfirmed(false);
  }, [mode, selectedBotId, selectedPrimaryObjective, selectedSubvertical, selectedVerticalId]);

  useEffect(() => {
    if (createState.ok || reconfigureState.ok) router.refresh();
  }, [createState.ok, reconfigureState.ok, router]);

  useEffect(() => {
    if (!selectedVerticalId || !selectedOrganizationId || (mode === "reconfigure" && !selectedBotId)) {
      setBlueprint(null);
      setVerticalProfile(null);
      setPreviewError(null);
      return;
    }

    const blueprintParams = new URLSearchParams();
    blueprintParams.set("organization_id", selectedOrganizationId);
    blueprintParams.set("vertical_id", selectedVerticalId);
    blueprintParams.set("primary_objective", selectedPrimaryObjective);
    if (selectedSubvertical) blueprintParams.set("subvertical", selectedSubvertical);
    if (mode === "reconfigure" && selectedBotId) blueprintParams.set("bot_id", selectedBotId);

    const verticalParams = new URLSearchParams();
    verticalParams.set("organization_id", selectedOrganizationId);
    verticalParams.set("vertical", selectedVerticalId);
    if (selectedSubvertical) verticalParams.set("subvertical", selectedSubvertical);
    if (mode === "reconfigure" && selectedBotId) verticalParams.set("bot_id", selectedBotId);

    let ignore = false;
    setPreviewLoading(true);
    setPreviewError(null);

    void Promise.allSettled([
      fetchWizardBlueprint(blueprintParams),
      fetchWizardVerticalProfile(verticalParams),
    ]).then((results) => {
      if (ignore) return;
      const [blueprintResult, profileResult] = results;
      const errors: string[] = [];

      if (blueprintResult.status === "fulfilled") setBlueprint(blueprintResult.value);
      else errors.push(blueprintResult.reason instanceof Error ? blueprintResult.reason.message : "No se pudo actualizar el blueprint.");

      if (profileResult.status === "fulfilled") setVerticalProfile(profileResult.value);
      else errors.push(profileResult.reason instanceof Error ? profileResult.reason.message : "No se pudo cargar el perfil vertical.");

      setPreviewError(errors.length ? errors.join(" ") : null);
    }).finally(() => {
      if (!ignore) setPreviewLoading(false);
    });

    return () => {
      ignore = true;
    };
  }, [mode, selectedBotId, selectedOrganizationId, selectedPrimaryObjective, selectedSubvertical, selectedVerticalId]);

  const createCtaLabel = createPending ? "Creando…" : `Crear bot para ${objectiveLabel(selectedPrimaryObjective).toLowerCase()}`;
  const reconfigureCtaLabel = reconfigurePending ? "Aplicando…" : `Confirmar aplicación en ${safeText(selectedBot?.name, "este bot")}`;

  return (
    <div className="grid gap-6">
      <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
        <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Entrada clara al wizard</div>
        <h3 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">¿Quieres crear uno nuevo o reconfigurar uno existente?</h3>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">Primero eliges el modo. Después el wizard te lleva por un solo camino: en nuevo bot te quedas aquí al crear; en reconfiguración ves diff, impacto y snapshot automático antes de seguir.</p>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <button
            type="button"
            className={`rounded-[24px] border p-4 text-left transition ${cardClasses(mode === "create")}`}
            onClick={() => setMode("create")}
          >
            <div className="text-base font-semibold text-[color:var(--text-primary)]">Modo A — Nuevo bot</div>
            <p className="mt-2 text-sm leading-6">Tenant, vertical, subvertical, básicos, review y create sin salir de esta vista.</p>
          </button>
          <button
            type="button"
            className={`rounded-[24px] border p-4 text-left transition ${cardClasses(mode === "reconfigure")} ${bots.length ? "" : "opacity-50"}`}
            onClick={() => { if (bots.length) setMode("reconfigure"); }}
            disabled={!bots.length}
          >
            <div className="text-base font-semibold text-[color:var(--text-primary)]">Modo B — Reconfigurar bot</div>
            <p className="mt-2 text-sm leading-6">Bot explícito, vertical actual, diff, impacto, reaplicar pack y snapshot automático.</p>
          </button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.96fr)_minmax(0,1.04fr)]">
        <div className="grid gap-5">
          <StepRail title={mode === "create" ? "Ruta del modo nuevo bot" : "Ruta del modo reconfigurar"} steps={mode === "create" ? createSteps : reconfigureSteps} />

          {mode === "reconfigure" ? (
            <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
              <label className="field-label">Bot a reconfigurar
                <select className="field-input" value={selectedBotId} onChange={(event) => setSelectedBotId(event.target.value)} required>
                  <option value="">Selecciona un bot explícitamente</option>
                  {bots.map((bot) => <option key={bot.id} value={bot.id}>{bot.name} · {safeText(organizationsById[bot.organization_id]?.name, "sin tenant")}</option>)}
                </select>
              </label>
              <p className="mt-4 text-sm leading-6 text-[color:var(--text-secondary)]">La reconfiguración ya no depende de una cookie ni de un bot implícito. Aquí eliges el bot de forma explícita antes de ver o aplicar cualquier cambio fuerte.</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Bot</div>
                  <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(selectedBot?.name, "Sin bot seleccionado")}</div>
                </div>
                <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Tenant</div>
                  <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(selectedBotTenant?.name, "Sin tenant")}</div>
                </div>
                <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Vertical actual</div>
                  <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{currentBotVertical}</div>
                </div>
                <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Estado</div>
                  <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(selectedBot?.status, selectedBot ? "draft" : "Sin estado")}</div>
                </div>
              </div>
              {selectedBot ? (
                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Subvertical actual</div>
                    <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(currentBotSubvertical, "Sin subvertical")}</div>
                  </div>
                  <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Objetivo actual</div>
                    <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{currentBotObjective}</div>
                  </div>
                  <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Tono actual</div>
                    <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{currentBotTone}</div>
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="field-label">Tenant
                  <select className="field-input" value={selectedOrganizationId} onChange={(event) => handleOrganizationChange(event.target.value)} required disabled={!organizations.length}>
                    {organizations.length ? organizations.map((organization) => (
                      <option key={organization.id} value={organization.id}>{organization.name}</option>
                    )) : <option value="">Sin organizaciones disponibles</option>}
                  </select>
                </label>
                <label className="field-label">Objetivo primario
                  <select className="field-input" value={selectedPrimaryObjective} onChange={(event) => setSelectedPrimaryObjective(normalizeObjective(event.target.value))} required>
                    {OBJECTIVES.map((item) => <option key={item} value={item}>{objectiveLabel(item)}</option>)}
                  </select>
                </label>
              </div>
              <p className="mt-4 text-sm leading-6 text-[color:var(--text-secondary)]">El nuevo bot nace dentro del tenant elegido. La vertical y la subvertical que selecciones aquí gobiernan el pack generado y lo que verás en el review antes de crear.</p>
            </div>
          )}

          <VerticalPicker
            verticals={verticals}
            strongestVerticals={strongestVerticals}
            selectedVerticalId={selectedVerticalId}
            onSelect={handleVerticalChange}
          />

          <SubverticalPicker
            verticalName={previewVerticalName}
            selectedSubvertical={selectedSubvertical}
            subverticalProfiles={subverticalProfiles}
            onSelect={setSelectedSubvertical}
            loading={previewLoading}
          />

          {!canSubmit ? (
            <UiMessage title="Falta una decisión obligatoria" tone="warning">
              El wizard necesita tenant, vertical y subvertical antes de crear o reaplicar el pack.
            </UiMessage>
          ) : null}

          {mode === "create" ? (
            <form action={createFormAction} className="grid gap-4 rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)] md:grid-cols-2">
              <input type="hidden" name="redirect_to" value="/bot-studio?mode=create" />
              <input type="hidden" name="organization_id" value={selectedOrganizationId} />
              <input type="hidden" name="vertical" value={selectedVerticalId} />
              <input type="hidden" name="subvertical" value={selectedSubvertical} />

              <label className="field-label">Tenant elegido
                <input className="field-input" value={safeText(selectedOrganization?.name, "Sin tenant")} readOnly />
              </label>

              <label className="field-label">Vertical y subvertical
                <input className="field-input" value={`${safeText(activeVerticalProfile?.name, "Sin vertical")} · ${previewSubverticalName}`} readOnly />
              </label>

              <label className="field-label">Nombre del negocio
                <input className="field-input" name="business_name" value={businessName} onChange={(event) => setBusinessName(event.target.value)} placeholder={safeText(selectedOrganization?.name, "Ej. WAOS Dental Polanco")} required />
              </label>

              <label className="field-label">Nombre del bot
                <input className="field-input" name="bot_name" value={botName} onChange={(event) => setBotName(event.target.value)} placeholder="Ej. Sofia" required />
              </label>

              <label className="field-label">Tono base
                <input className="field-input" name="tone" value={tone} onChange={(event) => setTone(event.target.value)} placeholder="amable" />
              </label>

              <label className="field-label">Idioma
                <select className="field-input" name="language" value={language} onChange={(event) => setLanguage(event.target.value)}>
                  <option value="es">Español</option>
                  <option value="en">English</option>
                </select>
              </label>

              <label className="field-label">Timezone
                <input className="field-input" name="timezone" value={timezone} onChange={(event) => setTimezone(event.target.value)} />
              </label>

              <label className="field-label">WhatsApp (opcional)
                <input className="field-input" name="whatsapp_number" value={whatsappNumber} onChange={(event) => setWhatsappNumber(event.target.value)} placeholder="+525512345678" />
              </label>

              <label className="field-label md:col-span-2">Horario inicial
                <input className="field-input" name="hours" value={hours} onChange={(event) => setHours(event.target.value)} placeholder="Lun-Vie 9:00-18:00" />
              </label>

              <label className="field-label md:col-span-2 flex items-center gap-3 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3">
                <input type="checkbox" name="publish_now" checked={publishNow} onChange={(event) => setPublishNow(event.target.checked)} />
                <span>Publicar el primer draft al crear</span>
              </label>

              {createState.error ? <div className="md:col-span-2"><UiMessage title="No se pudo crear el bot" tone="error">{createState.error}</UiMessage></div> : null}
              {createState.ok && createState.success ? <div className="md:col-span-2"><UiMessage title="Bot creado sin salir del wizard" tone="success">{createState.success}</UiMessage></div> : null}

              <div className="md:col-span-2 flex flex-wrap gap-3">
                <button className="primary-btn" type="submit" disabled={!organizations.length || !canSubmit || createPending}>{createCtaLabel}</button>
                {!organizations.length ? <Link href="/organizations" className="secondary-btn">Primero crea o asigna una organización</Link> : null}
              </div>
            </form>
          ) : bots.length ? (
            selectedBot ? (
              <form action={reconfigureFormAction} className="grid gap-4 rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)] md:grid-cols-2">
                <input type="hidden" name="bot_id" value={selectedBotId} />
                <input type="hidden" name="organization_id" value={selectedOrganizationId} />
                <input type="hidden" name="redirect_to" value={`/bot-studio?mode=reconfigure${selectedBotId ? `&bot=${encodeURIComponent(selectedBotId)}` : ""}`} />
                <input type="hidden" name="vertical" value={selectedVerticalId} />
                <input type="hidden" name="subvertical" value={selectedSubvertical} />
                <input type="hidden" name="review_required" value="true" />
                <input type="hidden" name="review_confirmed" value={reviewConfirmed ? "true" : "false"} />

                <label className="field-label">Nueva vertical
                  <input className="field-input" value={safeText(activeVerticalProfile?.name, "Sin vertical")} readOnly />
                </label>

                <label className="field-label">Nueva subvertical
                  <input className="field-input" value={previewSubverticalName} readOnly />
                </label>

                <label className="field-label md:col-span-2">Objetivo primario
                  <select className="field-input" name="primary_objective" value={selectedPrimaryObjective} onChange={(event) => setSelectedPrimaryObjective(normalizeObjective(event.target.value))} required>
                    {OBJECTIVES.map((item) => <option key={item} value={item}>{objectiveLabel(item)}</option>)}
                  </select>
                </label>

                <div className="md:col-span-2 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Revisión obligatoria antes de aplicar</div>
                      <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">Comparador visual de impacto para {safeText(selectedBot.name, "el bot seleccionado")}</div>
                      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Esto no es un ajuste menor. Estás por reaplicar defaults fuertes del vertical y por eso el wizard separa el estado actual del pack propuesto antes del snapshot y la confirmación final.</p>
                    </div>
                    <span className="mono-pill">Snapshot previo obligatorio</span>
                  </div>

                  <div className="mt-4 rounded-[24px] border border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] p-4">
                    <div className="text-sm font-semibold text-[color:var(--text-primary)]">Impacto potencial de esta reconfiguración dura</div>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
                        <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Se puede reemplazar</div>
                        <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Templates, tono, objetivo, servicios y FAQs sembradas por el pack.</p>
                      </div>
                      <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
                        <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Se puede recalcular</div>
                        <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Agenda, handoff, followups e integraciones sugeridas derivadas de la nueva vertical.</p>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
                      <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Antes</div>
                      <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">Estado actual del bot</div>
                      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(selectedBot.name, "Bot actual")} · {currentBotVertical} · {safeText(currentBotSubvertical, "Sin subvertical")} · {currentBotObjective}</p>
                    </div>
                    <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
                      <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Después</div>
                      <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">Pack propuesto por el wizard</div>
                      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(selectedBot.name, "Bot actual")} · {previewVerticalName} · {previewSubverticalName} · {objectiveLabel(selectedPrimaryObjective)}</p>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3">
                    <DiffField
                      label="Vertical"
                      status={verticalStatus}
                      before={currentBotVertical}
                      after={previewVerticalName}
                      detail="La vertical define el marco principal del pack, su catálogo base y parte de las reglas de operación." 
                    />
                    <DiffField
                      label="Subvertical"
                      status={subverticalStatus}
                      before={safeText(currentBotSubvertical, "Sin subvertical")}
                      after={previewSubverticalName}
                      detail="La subvertical aterriza la promesa, el bundle y los ejemplos operativos que se sembrarán." 
                    />
                    <DiffField
                      label="Templates"
                      status={templateStatus}
                      before={summarize(currentBotTemplateLabels, "No hay templates visibles hoy", 5)}
                      after={summarize(nextTemplateLabels, "Se aplicarán templates del pack seleccionado", 5)}
                      detail="Los templates activos pueden ser reemplazados por los del nuevo pack vertical. Esta es una mutación fuerte." 
                    />
                    <DiffField
                      label="Servicios y FAQs"
                      status={servicesStatus}
                      before={summarize(currentBotServices, "Sin servicios visibles", 5)}
                      after={summarize(nextServices, "Se resembrarán servicios base y FAQs del pack", 5)}
                      detail="El catálogo operativo puede resembrarse con servicios semilla y FAQs derivadas del vertical pack." 
                    />
                    <DiffField
                      label="Tono"
                      status={toneStatus}
                      before={currentBotTone}
                      after={nextTone}
                      detail="La personalidad base del bot puede cambiar junto con el objetivo y el encuadre del nuevo pack." 
                    />
                    <DiffField
                      label="Objetivo"
                      status={objectiveStatus}
                      before={currentBotObjective}
                      after={objectiveLabel(selectedPrimaryObjective)}
                      detail="El objetivo primario afecta followups, calificación, handoff y rutas de cierre del bot." 
                    />
                    <DiffField
                      label="Integraciones sugeridas"
                      status={integrationsStatus}
                      before={summarize(currentBotIntegrationKeys, "Sin integraciones visibles", 5)}
                      after={summarize(recommendedIntegrations, "No hay nuevas integraciones sugeridas", 5)}
                      detail="Las integraciones aquí no se fuerzan automáticamente: se muestran como recomendación del nuevo pack." 
                    />
                    <DiffField
                      label="Agenda, handoff y followups"
                      status={operationsStatus}
                      before="Se conserva la configuración actual del bot hasta confirmar la aplicación."
                      after="Se recalculan reglas de agenda, handoff, followups y policy defaults del vertical al confirmar."
                      detail="Este impacto operativo es de los más delicados, por eso el snapshot previo es obligatorio antes de mutar." 
                    />
                  </div>

                  <p className="mt-4 text-sm leading-6 text-[color:var(--text-secondary)]">El submit final solo se habilita después de revisar cambios y confirmar. Si no se puede generar el snapshot previo, la reconfiguración no se aplica.</p>
                </div>

                {reconfigureState.error ? <div className="md:col-span-2"><UiMessage title="No se pudo reconfigurar el bot" tone="error">{reconfigureState.error}</UiMessage></div> : null}
                {reconfigureState.ok && reconfigureState.success ? <div className="md:col-span-2"><UiMessage title="Reconfiguración aplicada" tone="success">{reconfigureState.success}</UiMessage></div> : null}

                {!reviewStageOpen ? (
                  <div className="md:col-span-2 flex flex-wrap gap-3">
                    <button className="primary-btn" type="button" onClick={() => setReviewStageOpen(true)} disabled={!canSubmit || !selectedBotId || !hasReconfigurationChanges}>Revisar cambios</button>
                    {selectedBotId ? <Link href={`/bots/${selectedBotId}`} className="secondary-btn">Ver detalle del bot</Link> : null}
                  </div>
                ) : (
                  <div className="md:col-span-2 rounded-[24px] border border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] p-4">
                    <div className="text-base font-semibold text-[color:var(--text-primary)]">Confirmación final</div>
                    <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Estás a punto de reaplicar el pack vertical a {safeText(selectedBot.name, "este bot")}. Esto puede reemplazar templates y resembrar agenda, followups, handoff, personality, objective, servicios, FAQs e integraciones sugeridas.</p>
                    <label className="mt-4 flex items-center gap-3 text-sm text-[color:var(--text-primary)]">
                      <input type="checkbox" checked={reviewConfirmed} onChange={(event) => setReviewConfirmed(event.target.checked)} />
                      Confirmo que ya revisé el diff, entiendo la mutación fuerte y quiero aplicar la reconfiguración.
                    </label>
                    <div className="mt-4 flex flex-wrap gap-3">
                      <button className="primary-btn" type="submit" disabled={!canSubmit || !selectedBotId || !hasReconfigurationChanges || !reviewConfirmed || reconfigurePending}>{reconfigureCtaLabel}</button>
                      <button className="secondary-btn" type="button" onClick={() => { setReviewStageOpen(false); setReviewConfirmed(false); }}>Cerrar revisión</button>
                      {selectedBotId ? <Link href={`/bots/${selectedBotId}`} className="secondary-btn">Ver detalle del bot</Link> : null}
                    </div>
                  </div>
                )}
                {!hasReconfigurationChanges ? <div className="md:col-span-2 text-sm text-[color:var(--text-secondary)]">Todavía no hay cambios entre el estado actual y la nueva selección del wizard.</div> : null}
              </form>
            ) : (
              <div className="rounded-[28px] border border-dashed border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-6 text-sm leading-6 text-[color:var(--text-secondary)]">
                Primero selecciona un bot explícitamente. Hasta entonces no se habilita la reconfiguración ni se muestra una mutación destructiva detrás de un submit simple.
              </div>
            )
          ) : (
            <div className="rounded-[28px] border border-dashed border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-6 text-sm leading-6 text-[color:var(--text-secondary)]">
              Todavía no hay bots para reconfigurar. Usa el modo Nuevo bot para sembrar el primero y luego vuelve aquí.
            </div>
          )}
        </div>

        <div className="grid gap-5">
          <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Review del pack generado</div>
                <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">{safeText(previewVerticalName, "Vertical")}</h3>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{previewVerticalProblem}</p>
              </div>
              <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-right">
                <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Progreso</div>
                <div className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">{safeText(blueprint?.progress_percent, "-")}%</div>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <span className="mono-pill">{titleCase(mode)}</span>
              <span className="mono-pill">{previewSubverticalName}</span>
              <span className="mono-pill">{objectiveLabel(selectedPrimaryObjective)}</span>
              {safeText(blueprint?.current_step, "") ? <span className="mono-pill">Paso: {safeText(blueprint?.current_step)}</span> : null}
            </div>

            {previewLoading ? <p className="mt-4 text-sm text-[color:var(--text-secondary)]">Actualizando review con la selección actual del wizard…</p> : null}
            {previewError ? <div className="mt-4"><UiMessage title="No se pudo refrescar el review" tone="warning">{previewError}</UiMessage></div> : null}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Promesa</div>
              <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{previewSubverticalName}</div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{previewPromise}</p>
            </div>
            <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">CTA principal</div>
              <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{recommendedCtas[0] || "Sin CTA"}</div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">El CTA principal ya sale del wizard y no del contexto heredado del bot activo.</p>
            </div>
            <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Integraciones sugeridas</div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{recommendedIntegrations.join(" · ") || "Sin integraciones sugeridas"}</p>
            </div>
            <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Playbooks y flujos</div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{recommendedPlaybooks.join(" · ") || "Sin playbooks sugeridos"}</p>
            </div>
            <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Bundle activo</div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{summarize(activeSubverticalProfile?.service_bundle || [], "Sin bundle activo")}</p>
            </div>
            <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Preguntas 10x</div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{summarize(activeSubverticalProfile?.qualification_questions || [], "Sin preguntas visibles")}</p>
            </div>
          </div>

          <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Checklist del paso actual</div>
            <div className="mt-4 grid gap-3">
              {(checklist.length ? checklist : [
                { key: "vertical", label: "Vertical definida", completed: Boolean(selectedVerticalId) },
                { key: "subvertical", label: "Subvertical 10x elegida", completed: Boolean(selectedSubvertical) },
                { key: mode === "create" ? "basics" : "impact", label: mode === "create" ? "Básicos listos para crear" : "Diff listo para aplicar", completed: mode === "create" ? Boolean(businessName && botName) : hasReconfigurationChanges },
              ]).map((item, index) => (
                <div key={safeText(item.key || item.label, `check-${index}`)} className="flex items-center justify-between gap-3 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3">
                  <span className="text-sm text-[color:var(--text-primary)]">{safeText(item.label, "Paso")}</span>
                  <span className={`mono-pill ${item.completed ? "text-[color:var(--success-text)]" : "text-[color:var(--warning-text)]"}`}>{item.completed ? "Listo" : "Pendiente"}</span>
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4 text-sm leading-6 text-[color:var(--text-secondary)]">
              <strong className="text-[color:var(--text-primary)]">Payload activo:</strong>{" "}
              {mode === "create"
                ? `organization_id=${safeText(selectedOrganizationId, "-")}, vertical=${safeText(selectedVerticalId, "-")}, subvertical=${safeText(selectedSubvertical, "-")}, primary_objective=${selectedPrimaryObjective}`
                : `bot_id=${safeText(selectedBotId, "-")}, organization_id=${safeText(selectedOrganizationId, "-")}, vertical=${safeText(selectedVerticalId, "-")}, subvertical=${safeText(selectedSubvertical, "-")}, primary_objective=${selectedPrimaryObjective}`}
            </div>
          </div>

          {(createState.ok || reconfigureState.ok) && followUpBotId ? (
            <SuccessState
              title={createState.ok ? "Bot listo para seguir dentro del mismo flujo" : "Reconfiguración lista para el siguiente paso"}
              description={createState.ok
                ? "El wizard no te expulsó de la vista. Ahora sigue con canal, simulación o publicación desde aquí, y deja el detalle del bot como CTA secundario."
                : "El cambio quedó aplicado dentro del wizard. Ya puedes ir a canal, revisar publicación o abrir el detalle del bot sin perder el contexto."}
              actions={<>
                <Link href="/integrations?section=configuracion" className="primary-btn">Conectar canal</Link>
                <Link href={`/releases?stage=draft&bot_id=${encodeURIComponent(followUpBotId)}`} className="secondary-btn">Ir a publish</Link>
                <Link href={`/bots/${followUpBotId}`} className="secondary-btn">Ver detalle</Link>
              </>}
            />
          ) : null}

          {followUpBotId ? (
            <div className="grid gap-4 md:grid-cols-3">
              <NextStepCard
                title="Canal"
                description="Conecta WhatsApp, Calendar o pagos sin salir del flujo mental del wizard."
                action={<Link href="/integrations?section=configuracion" className="primary-btn">Configurar canal</Link>}
              />
              <NextStepCard
                title="Simulación"
                description={reconfigureState.snapshotCreated ? "El snapshot automático ya quedó generado. Usa el bot para revisar versiones, comparar y seguir con pruebas." : "Después de crear o reconfigurar, sigue a revisión y pruebas con el bot explícito ya seleccionado."}
                action={<Link href={`/bots/${followUpBotId}/versions`} className="secondary-btn">Revisar versiones</Link>}
              />
              <NextStepCard
                title="Publicación"
                description="Launch y releases quedan como siguiente paso operativo, no como redirección forzada al guardar." 
                action={<Link href={`/releases?stage=draft&bot_id=${encodeURIComponent(followUpBotId)}`} className="secondary-btn">Abrir publish</Link>}
              />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
