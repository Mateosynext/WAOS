"use client";

import { safeText } from "@/shared/lib/ui";
import type { WizardSubverticalProfile, WizardSubverticalTemplate } from "../domain/wizardTypes";

type SubverticalPickerProps = {
  verticalName: string;
  candidateSubvertical?: string;
  confirmedSubvertical?: string;
  selectedSubvertical?: string;
  subverticalProfiles: WizardSubverticalProfile[];
  onPreview?: (subverticalName: string) => void;
  onConfirm?: (subverticalName: string) => void;
  onSelect?: (subverticalName: string) => void;
  loading?: boolean;
  verticalConfirmed?: boolean;
};

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function summarizeList(values: Array<string | null | undefined>, fallback: string, limit = 4) {
  const cleaned = unique(values).slice(0, limit);
  return cleaned.length ? cleaned.join(" · ") : fallback;
}

function normalizeName(value: string) {
  return value.trim().toLowerCase();
}

function templateLabel(template: WizardSubverticalTemplate) {
  return safeText(template.title, safeText(template.name, safeText(template.template_key, safeText(template.key, "Template"))));
}

function cardClasses(isPreview: boolean, isConfirmed: boolean) {
  if (isConfirmed) return "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] shadow-[var(--shadow-sm)]";
  if (isPreview) return "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] shadow-[var(--shadow-sm)]";
  return "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] hover:border-[color:var(--accent-border)] hover:bg-[color:var(--surface-elevated)]";
}

export default function SubverticalPicker({
  verticalName,
  candidateSubvertical,
  confirmedSubvertical,
  selectedSubvertical,
  subverticalProfiles,
  onPreview,
  onConfirm,
  onSelect,
  loading = false,
  verticalConfirmed = false,
}: SubverticalPickerProps) {
  const effectiveCandidateSubvertical = candidateSubvertical ?? selectedSubvertical ?? "";
  const effectiveConfirmedSubvertical = confirmedSubvertical ?? selectedSubvertical ?? "";
  const handlePreview = onPreview || onSelect || (() => undefined);
  const handleConfirm = onConfirm || onSelect || (() => undefined);
  const effectiveVerticalConfirmed = verticalConfirmed || Boolean(selectedSubvertical && !confirmedSubvertical && !candidateSubvertical);
  const previewProfile = subverticalProfiles.find((item) => normalizeName(safeText(item.name)) === normalizeName(effectiveCandidateSubvertical)) || null;
  const confirmedProfile = subverticalProfiles.find((item) => normalizeName(safeText(item.name)) === normalizeName(effectiveConfirmedSubvertical)) || null;

  return (
    <div data-testid="subvertical-picker" className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Paso 2 · tipo de operación obligatorio</div>
          <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">Haz preview del tipo de operación y confírmalo aparte</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">El preview sigue siendo inmediato, pero la configuración 10x no queda tomada como decisión hasta que pulses “Usar este tipo de operación”. Así evitas que el wizard parezca ya armado sin confirmación real.</p>
        </div>
        <div className="grid gap-3 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-right">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Preview</div>
            <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(previewProfile?.name, effectiveCandidateSubvertical || "Pendiente")}</div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Confirmada</div>
            <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(confirmedProfile?.name, effectiveConfirmedSubvertical || "Pendiente")}</div>
          </div>
        </div>
      </div>

      {!effectiveVerticalConfirmed ? (
        <div className="mt-4 rounded-2xl border border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] px-4 py-3 text-sm leading-6 text-[color:var(--warning-text)]">
          Primero confirma la industria para que el tipo de operación quede asociado al contexto correcto.
        </div>
      ) : null}

      {loading && !subverticalProfiles.length ? <p className="mt-4 text-sm leading-6 text-[color:var(--text-secondary)]">Cargando tipos de operación y configuración generada 10x…</p> : null}

      {subverticalProfiles.length ? (
        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          {subverticalProfiles.map((profile) => {
            const isPreview = normalizeName(safeText(profile.name)) === normalizeName(previewProfile?.name || effectiveCandidateSubvertical);
            const isConfirmed = normalizeName(safeText(profile.name)) === normalizeName(confirmedProfile?.name || effectiveConfirmedSubvertical);
            return (
              <div
                data-testid={`subvertical-card-${safeText(profile.id, safeText(profile.name, "subvertical"))}`}
                key={safeText(profile.id, safeText(profile.name, "subvertical"))}
                role="button"
                tabIndex={0}
                onMouseEnter={() => handlePreview(safeText(profile.name))}
                onFocus={() => handlePreview(safeText(profile.name))}
                onClick={() => handlePreview(safeText(profile.name))}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    handlePreview(safeText(profile.name));
                  }
                }}
                className={`w-full rounded-[24px] border p-4 text-left transition ${cardClasses(isPreview, isConfirmed)}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="text-base font-semibold text-[color:var(--text-primary)]">{safeText(profile.name, "Tipo de operación")}</div>
                    <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(profile.promise, "Sin promesa visible")}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {isConfirmed ? <span className="rounded-full border border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--text-primary)]">Confirmada</span> : null}
                    {!isConfirmed && isPreview ? <span className="rounded-full border border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--warning-text)]">Preview</span> : null}
                    {typeof profile.strength_score === "number" ? <span className="rounded-full border border-[color:var(--success-border)] bg-[color:var(--success-soft)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--success-text)]">10x {profile.strength_score}</span> : null}
                  </div>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Buyer / motion</div>
                    <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{summarizeList([profile.buyer, profile.growth_motion], "Sin buyer ni motion visibles", 2)}</p>
                  </div>
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Bundle base</div>
                    <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{summarizeList(profile.service_bundle || [], "Sin bundle visible")}</p>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-3">
                  <button data-testid={`preview-subvertical-${safeText(profile.id, safeText(profile.name, "subvertical"))}`} type="button" className="secondary-btn" onClick={(event) => {
                    event.stopPropagation();
                    handlePreview(safeText(profile.name));
                  }}>
                    Ver preview
                  </button>
                  <button
                    data-testid={`confirm-subvertical-${safeText(profile.id, safeText(profile.name, "subvertical"))}`}
                    type="button"
                    className="primary-btn"
                    disabled={!effectiveVerticalConfirmed || isConfirmed}
                    onClick={(event) => {
                      event.stopPropagation();
                      handleConfirm(safeText(profile.name));
                    }}
                  >
                    {isConfirmed ? "Tipo de operación confirmado" : "Usar este tipo de operación"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="mt-5 rounded-2xl border border-dashed border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] px-4 py-5 text-sm leading-6 text-[color:var(--warning-text)]">
          Esta industria no devolvió tipos de operación visibles. Sin ese dato no conviene avanzar porque el producto quedaría a mitad de promesa.
        </div>
      )}

      <div data-testid="subvertical-preview" className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Preview de la configuración generada 10x</div>
            <h4 className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">{safeText(previewProfile?.name, "Selecciona un tipo de operación")}</h4>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(previewProfile?.promise, "Elige un tipo de operación para ver la configuración generada que se va a sembrar en el asistente operativo y en la operación.")}</p>
          </div>
          {previewProfile?.monetizes?.length ? (
            <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-4 py-3 text-sm text-[color:var(--text-secondary)]">
              Monetiza con {summarizeList(previewProfile?.monetizes || [], "sin foco", 3)}
            </div>
          ) : null}
        </div>

        <div className="mt-4 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-4 py-3 text-sm leading-6 text-[color:var(--text-secondary)]">
          <strong className="text-[color:var(--text-primary)]">Contexto activo:</strong> industria {safeText(verticalName, "Pendiente")} · preview {safeText(previewProfile?.name, effectiveCandidateSubvertical || "Pendiente")} · confirmada {safeText(confirmedProfile?.name, effectiveConfirmedSubvertical || "Pendiente")}
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Preguntas de calificación</div>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{summarizeList(previewProfile?.qualification_questions || [], "Sin preguntas sugeridas")}</p>
          </div>
          <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Bundles de servicios</div>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{summarizeList(previewProfile?.service_bundle || [], "Sin bundle visible")}</p>
          </div>
          <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Automatizaciones recomendadas</div>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{summarizeList(previewProfile?.automation_priorities || [], "Sin automatizaciones visibles")}</p>
          </div>
          <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Templates sugeridos</div>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{summarizeList((previewProfile?.templates || []).map(templateLabel), "Sin templates sugeridos")}</p>
          </div>
          <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">KPI de la configuración</div>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{summarizeList(previewProfile?.kpi_pack || [], "Sin KPI de la configuración visible")}</p>
          </div>
          <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Assets de lanzamiento</div>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{summarizeList(previewProfile?.launch_assets || [], "Sin launch assets visibles")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
