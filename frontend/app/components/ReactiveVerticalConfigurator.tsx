"use client";

import { useEffect, useMemo, useState } from "react";
import type { VerticalProfileContract } from "../lib/contracts";
import { safeText } from "../lib/ui";
import { UiMessage } from "./UiMessage";
import VerticalPicker from "../bot-studio/VerticalPicker";
import SubverticalPicker from "../bot-studio/SubverticalPicker";
import type { WizardBlueprint, WizardSubverticalProfile } from "../bot-studio/wizard-types";

type ReactiveVerticalConfiguratorProps = {
  organizationId: string;
  organizationName: string;
  initialVerticalId: string;
  initialSubvertical: string;
  initialVerticalProfile: VerticalProfileContract | null;
  verticals: VerticalProfileContract[];
  strongestVerticals?: VerticalProfileContract[];
  submitLabel: string;
  redirectTo: string;
  action: (formData: FormData) => void | Promise<void>;
  introTitle: string;
  introDescription: string;
  previewTitle: string;
};

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function normalizeName(value: string) {
  return value.trim().toLowerCase();
}

function summarize(values: Array<string | null | undefined>, fallback: string, limit = 4) {
  const cleaned = unique(values).slice(0, limit);
  return cleaned.length ? cleaned.join(" · ") : fallback;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? { ...(value as Record<string, unknown>) } : {};
}

function readNestedString(value: unknown, path: string[], fallback = "") {
  let current: unknown = value;
  for (const key of path) current = asRecord(current)[key];
  const result = String(current || "").trim();
  return result || fallback;
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

function buildSubverticalProfiles(verticalProfile: VerticalProfileContract | null, blueprint: WizardBlueprint | null): WizardSubverticalProfile[] {
  if (verticalProfile?.subvertical_profiles?.length) return verticalProfile.subvertical_profiles as WizardSubverticalProfile[];
  return pickSubverticalOptions(blueprint, verticalProfile).map((name) => ({
    id: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
    name,
  } as WizardSubverticalProfile));
}

function resolveActiveSubverticalProfile(args: {
  selectedSubvertical: string;
  verticalProfile: VerticalProfileContract | null;
  blueprint: WizardBlueprint | null;
  subverticalProfiles: WizardSubverticalProfile[];
}) {
  const selected = normalizeName(args.selectedSubvertical);
  const match = (value?: string | null) => normalizeName(String(value || "")) === selected;

  if (!selected) return null;

  return args.verticalProfile?.selected_subvertical && match(args.verticalProfile.selected_subvertical.name)
    ? args.verticalProfile.selected_subvertical as WizardSubverticalProfile
    : args.subverticalProfiles.find((item) => match(item.name)) || null;
}

function pickRecommendedIntegrations(blueprint: WizardBlueprint | null, catalogVertical?: VerticalProfileContract | null) {
  const fromBlueprint = unique((blueprint?.setup?.wizard?.recommended_integrations || []).map((item) => item.name || item.provider || item.integration_key));
  return fromBlueprint.length ? fromBlueprint : unique(catalogVertical?.recommended_integrations || []);
}

function pickPlaybooks(blueprint: WizardBlueprint | null, catalogVertical?: VerticalProfileContract | null) {
  const fromBlueprint = unique((blueprint?.setup?.wizard?.recommended_playbooks || []).map((item) => item.label));
  return fromBlueprint.length ? fromBlueprint : unique(catalogVertical?.flows || []);
}

function pickTemplateLabels(blueprint: WizardBlueprint | null, activeSubverticalProfile: WizardSubverticalProfile | null, activeVerticalProfile: VerticalProfileContract | null) {
  const setupTemplates = Array.isArray(asRecord(blueprint?.setup).response_templates)
    ? asRecord(blueprint?.setup).response_templates as Array<Record<string, unknown>>
    : [];

  return unique([
    ...setupTemplates.map((item) => String(item.title || item.template_key || item.key || "").trim()),
    ...(activeSubverticalProfile?.templates || []).map((item) => String(item.title || item.template_key || item.key || item.name || "").trim()),
    ...((asRecord(activeVerticalProfile?.pipeline).templates || []) as Array<Record<string, unknown>>).map((item) => String(item.title || item.template_key || item.key || item.name || "").trim()),
  ]);
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

function PreviewTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{label}</div>
      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{value}</p>
    </div>
  );
}

export default function ReactiveVerticalConfigurator({
  organizationId,
  organizationName,
  initialVerticalId,
  initialSubvertical,
  initialVerticalProfile,
  verticals,
  strongestVerticals = [],
  submitLabel,
  redirectTo,
  action,
  introTitle,
  introDescription,
  previewTitle,
}: ReactiveVerticalConfiguratorProps) {
  const [selectedVerticalId, setSelectedVerticalId] = useState(initialVerticalId || "");
  const [selectedSubvertical, setSelectedSubvertical] = useState(initialSubvertical || initialVerticalProfile?.selected_subvertical?.name || "");
  const [verticalProfile, setVerticalProfile] = useState<VerticalProfileContract | null>(initialVerticalProfile);
  const [blueprint, setBlueprint] = useState<WizardBlueprint | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeCatalogVertical = useMemo(
    () => verticals.find((item) => item.id === selectedVerticalId) || null,
    [selectedVerticalId, verticals],
  );

  const subverticalProfiles = useMemo(
    () => buildSubverticalProfiles(verticalProfile, blueprint),
    [verticalProfile, blueprint],
  );

  const subverticalOptions = useMemo(
    () => unique([
      ...subverticalProfiles.map((item) => item.name),
      ...pickSubverticalOptions(blueprint, verticalProfile),
    ]),
    [blueprint, subverticalProfiles, verticalProfile],
  );

  const activeSubverticalProfile = useMemo(() => resolveActiveSubverticalProfile({
    selectedSubvertical,
    verticalProfile,
    blueprint,
    subverticalProfiles,
  }), [blueprint, selectedSubvertical, subverticalProfiles, verticalProfile]);

  const previewVerticalName = safeText(blueprint?.profile?.name, safeText(verticalProfile?.name, safeText(activeCatalogVertical?.name, "Vertical")));
  const previewVerticalProblem = safeText(blueprint?.profile?.problem, safeText(verticalProfile?.problem, safeText(activeCatalogVertical?.description, "Selecciona industria y tipo de operación para ver el preview operativo.")));
  const previewSubverticalName = safeText(activeSubverticalProfile?.name, safeText(blueprint?.setup?.wizard?.selected_subvertical || selectedSubvertical, "Sin subvertical fija"));
  const previewPromise = safeText(activeSubverticalProfile?.promise, previewVerticalProblem);
  const previewIntegrations = summarize(pickRecommendedIntegrations(blueprint, verticalProfile), "Sin integraciones sugeridas visibles");
  const previewPlaybooks = summarize(pickPlaybooks(blueprint, verticalProfile), "Sin playbooks visibles");
  const previewTemplates = summarize(pickTemplateLabels(blueprint, activeSubverticalProfile, verticalProfile), "Sin templates visibles");
  const previewQuestions = summarize(activeSubverticalProfile?.qualification_questions || [], "Sin preguntas sugeridas visibles");
  const previewServiceBundle = summarize(activeSubverticalProfile?.service_bundle || [], "Sin bundle de servicios visible");
  const previewTone = readNestedString(blueprint?.setup, ["personality", "tone"], safeText(verticalProfile?.short_name, "según defaults de industria"));

  useEffect(() => {
    let cancelled = false;
    if (!selectedVerticalId) {
      setVerticalProfile(null);
      setBlueprint(null);
      setError(null);
      return;
    }

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const blueprintParams = new URLSearchParams();
        blueprintParams.set("organization_id", organizationId);
        blueprintParams.set("vertical_id", selectedVerticalId);
        if (selectedSubvertical) blueprintParams.set("subvertical", selectedSubvertical);

        const verticalParams = new URLSearchParams();
        verticalParams.set("organization_id", organizationId);
        verticalParams.set("vertical", selectedVerticalId);
        if (selectedSubvertical) verticalParams.set("subvertical", selectedSubvertical);

        const [nextBlueprint, nextVerticalProfile] = await Promise.all([
          fetchWizardBlueprint(blueprintParams),
          fetchWizardVerticalProfile(verticalParams),
        ]);

        if (cancelled) return;
        setBlueprint(nextBlueprint);
        setVerticalProfile(nextVerticalProfile);
      } catch (loadError) {
        if (cancelled) return;
        setError(loadError instanceof Error ? loadError.message : "No se pudo refrescar la selección de industria.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [organizationId, selectedSubvertical, selectedVerticalId]);

  useEffect(() => {
    if (!subverticalOptions.length) {
      if (selectedSubvertical) setSelectedSubvertical("");
      return;
    }
    if (selectedSubvertical && subverticalOptions.some((item) => normalizeName(item) === normalizeName(selectedSubvertical))) return;
    setSelectedSubvertical("");
  }, [selectedSubvertical, subverticalOptions]);

  return (
    <div className="grid gap-5">
      <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
        <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Mismo patrón reactivo del wizard</div>
        <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">{introTitle}</h3>
        <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{introDescription}</p>
      </div>

      <VerticalPicker
        verticals={verticals}
        strongestVerticals={strongestVerticals}
        selectedVerticalId={selectedVerticalId}
        onSelect={(nextVertical) => {
          setSelectedVerticalId(nextVertical);
          setSelectedSubvertical("");
          setError(null);
        }}
      />

      <SubverticalPicker
        verticalName={previewVerticalName}
        selectedSubvertical={selectedSubvertical}
        subverticalProfiles={subverticalProfiles}
        onSelect={(nextSubvertical) => {
          setSelectedSubvertical(nextSubvertical);
          setError(null);
        }}
        loading={loading}
      />

      <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Preview antes de guardar</div>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">{previewTitle}</h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">{previewVerticalProblem}</p>
          </div>
          <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-right">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Selección activa</div>
            <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{previewVerticalName}</div>
            <div className="mt-1 text-sm text-[color:var(--text-secondary)]">{previewSubverticalName}</div>
          </div>
        </div>

        {loading ? <p className="mt-4 text-sm leading-6 text-[color:var(--text-secondary)]">Actualizando subverticales y blueprint con tu selección…</p> : null}
        {error ? <div className="mt-4"><UiMessage title="No se pudo refrescar el preview" tone="warning">{error}</UiMessage></div> : null}

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <PreviewTile label="Promesa del tipo de operación" value={previewPromise} />
          <PreviewTile label="Servicios base" value={previewServiceBundle} />
          <PreviewTile label="Preguntas de calificación" value={previewQuestions} />
          <PreviewTile label="Templates sugeridos" value={previewTemplates} />
          <PreviewTile label="Integraciones sugeridas" value={previewIntegrations} />
          <PreviewTile label="Playbooks / flujos" value={previewPlaybooks} />
        </div>

        <div className="mt-4 rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Configuración generada resumida</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(previewVerticalName, "Industria")} · {safeText(previewSubverticalName, "Sin tipo de operación fijo")} · tono sugerido {previewTone}.</p>
        </div>
      </div>

      <form action={action} className="grid gap-4 rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
        <input type="hidden" name="organization_id" value={organizationId} />
        <input type="hidden" name="redirect_to" value={redirectTo} />
        <input type="hidden" name="vertical" value={selectedVerticalId} />
        <input type="hidden" name="subvertical" value={selectedSubvertical} />

        <div className="grid gap-4 md:grid-cols-2">
          <label className="field-label">Organización
            <input className="field-input" value={organizationName} readOnly />
          </label>
          <label className="field-label">Configuración generada que se va a guardar
            <input className="field-input" value={`${safeText(previewVerticalName, "Sin industria")} · ${safeText(previewSubverticalName, "Sin tipo de operación fijo")}`} readOnly />
          </label>
        </div>

        <div className="flex flex-wrap gap-2">
          <button className="primary-btn" type="submit" disabled={!selectedVerticalId || !selectedSubvertical || loading}>{submitLabel}</button>
          <span className="rounded-full border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-2 text-xs text-[color:var(--text-secondary)]">
            El tipo de operación se reinicia solo si ya no aplica a la nueva industria.
          </span>
        </div>
      </form>
    </div>
  );
}
