"use client";

import { useMemo, useState } from "react";
import type { VerticalProfileContract } from "../lib/contracts";
import { safeText } from "../lib/ui";

type VerticalPickerProps = {
  verticals: VerticalProfileContract[];
  strongestVerticals: VerticalProfileContract[];
  candidateVerticalId?: string;
  confirmedVerticalId?: string;
  selectedVerticalId?: string;
  onPreview?: (verticalId: string) => void;
  onConfirm?: (verticalId: string) => void;
  onSelect?: (verticalId: string) => void;
};

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function uniqueById(items: VerticalProfileContract[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (!item?.id || seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}

function sortByStrength(items: VerticalProfileContract[]) {
  return [...items].sort((left, right) => {
    const leftRank = typeof left.strongest_rank === "number" ? left.strongest_rank : Number.MAX_SAFE_INTEGER;
    const rightRank = typeof right.strongest_rank === "number" ? right.strongest_rank : Number.MAX_SAFE_INTEGER;
    if (leftRank !== rightRank) return leftRank - rightRank;
    const leftScore = typeof left.ten_x_score === "number" ? left.ten_x_score : -1;
    const rightScore = typeof right.ten_x_score === "number" ? right.ten_x_score : -1;
    if (leftScore !== rightScore) return rightScore - leftScore;
    return safeText(left.name).localeCompare(safeText(right.name));
  });
}

function summarizeList(values: string[], fallback: string, limit = 3) {
  const cleaned = unique(values).slice(0, limit);
  return cleaned.length ? cleaned.join(" · ") : fallback;
}

function audienceLabel(vertical: VerticalProfileContract) {
  return safeText(vertical.buyer.primary, summarizeList(vertical.buyer.secondary, safeText(vertical.description, "Sin buyer visible"), 2));
}

function searchIndex(vertical: VerticalProfileContract) {
  return [
    vertical.name,
    vertical.short_name,
    vertical.description,
    vertical.problem,
    vertical.buyer.primary,
    ...vertical.buyer.secondary,
    ...vertical.flows,
    ...vertical.recommended_integrations,
    ...vertical.recommended_subverticals,
    ...vertical.subverticals,
  ].map((item) => String(item || "").toLowerCase()).join(" ");
}

function hasTenXSignal(vertical: VerticalProfileContract) {
  return Boolean(vertical.ten_x_score || vertical.ten_x_narrative || vertical.ten_x_growth_loops.length);
}

function hasStrongestSignal(vertical: VerticalProfileContract) {
  return Boolean(vertical.is_strongest_vertical || typeof vertical.strongest_rank === "number");
}

function badgeClasses(kind: "confirmed" | "preview" | "tenx" | "strong") {
  if (kind === "confirmed") return "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] text-[color:var(--text-primary)]";
  if (kind === "preview") return "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] text-[color:var(--warning-text)]";
  if (kind === "tenx") return "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success-text)]";
  return "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] text-[color:var(--warning-text)]";
}

function VerticalCard({
  vertical,
  isPreview,
  isConfirmed,
  onPreview,
  onConfirm,
}: {
  vertical: VerticalProfileContract;
  isPreview: boolean;
  isConfirmed: boolean;
  onPreview: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onMouseEnter={onPreview}
      onFocus={onPreview}
      onClick={onPreview}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onPreview();
        }
      }}
      className={`w-full rounded-[24px] border p-4 text-left transition ${isConfirmed
        ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] shadow-[var(--shadow-sm)]"
        : isPreview
          ? "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] shadow-[var(--shadow-sm)]"
          : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] hover:border-[color:var(--accent-border)] hover:bg-[color:var(--surface-elevated)]"}`}
    >
      <div data-testid={`vertical-card-${vertical.id}`} className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-base font-semibold text-[color:var(--text-primary)]">{safeText(vertical.name, "Industria")}</div>
          <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(vertical.problem, safeText(vertical.description, "Sin tesis visible"))}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {isConfirmed ? <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${badgeClasses("confirmed")}`}>Confirmada</span> : null}
          {!isConfirmed && isPreview ? <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${badgeClasses("preview")}`}>Preview</span> : null}
          {hasTenXSignal(vertical) ? <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${badgeClasses("tenx")}`}>10x</span> : null}
          {hasStrongestSignal(vertical) ? <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${badgeClasses("strong")}`}>Más fuerte</span> : null}
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Para quién aplica</div>
          <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{audienceLabel(vertical)}</p>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Flujos clave</div>
          <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{summarizeList(vertical.flows, "Sin flujos sugeridos")}</p>
        </div>
        <div className="sm:col-span-2">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Integraciones recomendadas</div>
          <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{summarizeList(vertical.recommended_integrations, "Sin integraciones sugeridas")}</p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <button data-testid={`preview-vertical-${vertical.id}`} type="button" className="secondary-btn" onClick={(event) => {
          event.stopPropagation();
          onPreview();
        }}>
          Ver preview
        </button>
        <button
          data-testid={`confirm-vertical-${vertical.id}`}
          type="button"
          className="primary-btn"
          disabled={isConfirmed}
          onClick={(event) => {
            event.stopPropagation();
            onConfirm();
          }}
        >
          {isConfirmed ? "Industria confirmada" : "Usar esta industria"}
        </button>
      </div>
    </div>
  );
}

export default function VerticalPicker({
  verticals,
  strongestVerticals,
  candidateVerticalId,
  confirmedVerticalId,
  selectedVerticalId,
  onPreview,
  onConfirm,
  onSelect,
}: VerticalPickerProps) {
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState(false);

  const strongest = useMemo(() => {
    const explicit = uniqueById(strongestVerticals);
    if (explicit.length) return explicit.slice(0, 5);
    return sortByStrength(verticals.filter((item) => hasStrongestSignal(item) || hasTenXSignal(item))).slice(0, 5);
  }, [strongestVerticals, verticals]);

  const strongestIds = useMemo(() => new Set(strongest.map((item) => item.id)), [strongest]);
  const filteredVerticals = useMemo(() => {
    const query = search.trim().toLowerCase();
    const catalog = sortByStrength(uniqueById(verticals));
    if (!query) return catalog;
    return catalog.filter((vertical) => searchIndex(vertical).includes(query));
  }, [search, verticals]);

  const visibleAllVerticals = useMemo(() => {
    if (search.trim()) return filteredVerticals;
    if (showAll) return filteredVerticals;
    return filteredVerticals.filter((item) => !strongestIds.has(item.id));
  }, [filteredVerticals, search, showAll, strongestIds]);

  const effectivePreviewId = candidateVerticalId ?? selectedVerticalId ?? "";
  const effectiveConfirmedId = confirmedVerticalId ?? selectedVerticalId ?? "";
  const handlePreview = onPreview || onSelect || (() => undefined);
  const handleConfirm = onConfirm || onSelect || (() => undefined);
  const previewVertical = verticals.find((item) => item.id === effectivePreviewId) || null;
  const confirmedVertical = verticals.find((item) => item.id === effectiveConfirmedId) || null;

  return (
    <div data-testid="vertical-picker" className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Catálogo de industrias siempre visible</div>
          <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">Primero previsualizas, luego confirmas la industria</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">Pasar el cursor o hacer click muestra el preview inmediato, pero el wizard no toma la industria como elegida hasta que pulses una CTA explícita.</p>
        </div>
        <div className="grid gap-3 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-right">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Preview</div>
            <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(previewVertical?.name, "Sin preview")}</div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Confirmada</div>
            <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{safeText(confirmedVertical?.name, "Pendiente")}</div>
          </div>
        </div>
      </div>

      {strongest.length ? (
        <div className="mt-5">
          <div className="mb-3 text-sm font-semibold text-[color:var(--text-primary)]">Las 5 industrias más fuertes</div>
          <div className="grid gap-4 xl:grid-cols-2">
            {strongest.map((vertical) => (
              <VerticalCard
                key={`strong-${vertical.id}`}
                vertical={vertical}
                isPreview={vertical.id === effectivePreviewId}
                isConfirmed={vertical.id === effectiveConfirmedId}
                onPreview={() => handlePreview(vertical.id)}
                onConfirm={() => handleConfirm(vertical.id)}
              />
            ))}
          </div>
        </div>
      ) : null}

      <div data-testid="vertical-catalog" className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="field-label flex-1 min-w-[240px]">
            Ver todas
            <input
              className="field-input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              data-testid="vertical-search"
              placeholder="Busca por industria, buyer, flujo, tipo de operación o integración"
            />
          </label>
          <button type="button" className="secondary-btn" onClick={() => setShowAll((current) => !current)}>
            {showAll ? "Ocultar catálogo" : "Ver todas las industrias"}
          </button>
        </div>

        {search.trim() || showAll ? (
          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            {visibleAllVerticals.length ? visibleAllVerticals.map((vertical) => (
              <VerticalCard
                key={`all-${vertical.id}`}
                vertical={vertical}
                isPreview={vertical.id === effectivePreviewId}
                isConfirmed={vertical.id === effectiveConfirmedId}
                onPreview={() => handlePreview(vertical.id)}
                onConfirm={() => handleConfirm(vertical.id)}
              />
            )) : (
              <div className="rounded-2xl border border-dashed border-[color:var(--border-soft)] px-4 py-5 text-sm leading-6 text-[color:var(--text-secondary)]">
                No encontramos verticales para “{search.trim()}”. Prueba con buyer, flujo o integración.
              </div>
            )}
          </div>
        ) : (
          <p className="mt-4 text-sm leading-6 text-[color:var(--text-secondary)]">Abre el catálogo completo o busca una vertical puntual. El picker mantiene visibles las 5 más fuertes y deja el resto a un paso, sin marcar ninguna como confirmada por accidente.</p>
        )}
      </div>
    </div>
  );
}
