"use client";

import { useEffect, useMemo, useState } from "react";
import type { VerticalProfileContract } from "../lib/contracts";
import { safeText } from "../lib/ui";
import { UiMessage } from "./UiMessage";
import VerticalPicker from "../bot-studio/VerticalPicker";
import SubverticalPicker from "../bot-studio/SubverticalPicker";
import type { WizardBlueprint } from "../bot-studio/wizard-types";
import { loadWizardReactiveSelection } from "../bot-studio/wizardReactiveData";
import { buildReactiveVerticalPreviewModel, isSelectedSubverticalValid } from "./reactiveVerticalViewModel";

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

  const previewModel = useMemo(() => buildReactiveVerticalPreviewModel({
    selectedSubvertical,
    verticalProfile,
    blueprint,
    activeCatalogVertical,
  }), [activeCatalogVertical, blueprint, selectedSubvertical, verticalProfile]);

  const {
    subverticalProfiles,
    subverticalOptions,
    previewVerticalName,
    previewVerticalProblem,
    previewSubverticalName,
    previewPromise,
    previewIntegrations,
    previewPlaybooks,
    previewTemplates,
    previewQuestions,
    previewServiceBundle,
    previewTone,
  } = previewModel;

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
        const { blueprint: nextBlueprint, verticalProfile: nextVerticalProfile, errors } = await loadWizardReactiveSelection({
          organizationId,
          verticalId: selectedVerticalId,
          subvertical: selectedSubvertical,
        });

        if (cancelled) return;
        setBlueprint(nextBlueprint);
        setVerticalProfile(nextVerticalProfile);
        setError(errors.length ? errors.join(" ") : null);
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
    if (isSelectedSubverticalValid(selectedSubvertical, subverticalOptions)) return;
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
