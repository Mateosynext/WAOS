import { safeText } from "@/shared/lib/ui";
import type { WizardValidationSnapshot } from "@/features/bot-studio/domain/wizardTypes";
import { SummaryList, validationStatusMeta } from "./reviewUtils";

export function ValidationSnapshotPanel({
  title,
  description,
  snapshot,
}: {
  title: string;
  description: string;
  snapshot: WizardValidationSnapshot | null;
}) {
  if (!snapshot) return null;
  const gate = snapshot.gate || {};
  const gateMeta = validationStatusMeta(gate.status);
  const counts = snapshot.counts || {};
  const simulation = snapshot.simulation_result || {};
  const checklist = Array.isArray(snapshot.checklist) ? snapshot.checklist : [];
  const coveredItems = checklist
    .filter((item) => item.status === "green")
    .map((item) => safeText(item.label, safeText(item.key, "")))
    .filter(Boolean);
  const missingItems = checklist
    .filter((item) => item.status === "yellow" || item.status === "red")
    .map((item) => safeText(item.label, safeText(item.key, "")))
    .filter(Boolean);
  return (
    <div className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Checklist formal de salida</div>
          <h4 className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">{title}</h4>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${gateMeta.tone}`}>{gateMeta.pill}</span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Puerta de salida</div>
          <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{safeText(gate.label, "Sin estado")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(gate.detail, "Sin detalle adicional.")}</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Verde</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.green || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Checks listos para operar.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Amarillo</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.yellow || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Todavía requieren atención.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Rojo</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.red || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Bloqueos visibles antes de publish.</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Señales cubiertas</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(coveredItems.length), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Lo que ya quedó resuelto por el draft actual.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Faltantes</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(missingItems.length), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Todavía no aparecen en el draft operativo.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Simulación</div>
          <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{simulation.approved ? "Aprobada" : safeText(String(simulation.status || "pendiente"), "pendiente")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Pass rate: {safeText(String(simulation.pass_rate ?? 0), "0")}% · casos: {safeText(String(simulation.cases_total ?? 0), "0")}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Señales cubiertas</div>
          <SummaryList items={coveredItems} fallback="Sin cobertura visible todavía." />
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Faltantes</div>
          <SummaryList items={missingItems} fallback="Sin faltantes visibles." />
        </div>
      </div>
    </div>
  );
}
