import { safeText } from "@/shared/lib/ui";
import type { WizardValidationSnapshot } from "@/features/bot-studio/domain/wizardTypes";
import { validationStatusMeta } from "./reviewUtils";

export function VerticalScorecardPanel({
  title,
  description,
  snapshot,
}: {
  title: string;
  description: string;
  snapshot: WizardValidationSnapshot | null;
}) {
  const scorecard = snapshot?.scorecard;
  if (!scorecard) return null;
  const meta = validationStatusMeta(scorecard.status);
  const counts = scorecard.counts || {};
  return (
    <div className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{title}</div>
          <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{safeText(scorecard.label, "Vertical")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${meta.tone}`}>{meta.pill}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(scorecard.summary, "Sin scorecard visible.")}</p>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Verde</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.green || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Señales de negocio cubiertas.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Amarillo</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.yellow || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Requieren refuerzo antes de publish.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Rojo</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.red || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Bloquean o debilitan el go-live.</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {(scorecard.items || []).map((item, index) => {
          const itemMeta = validationStatusMeta(item.status);
          const covered = Array.isArray(item.covered_signals) ? item.covered_signals.filter(Boolean) : [];
          const missing = Array.isArray(item.missing_signals) ? item.missing_signals.filter(Boolean) : [];
          return (
            <div key={safeText(item.key || item.label, `scorecard-${index}`)} className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="text-sm font-semibold text-[color:var(--text-primary)]">{safeText(item.label, "Señal")}</div>
                <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${itemMeta.tone}`}>{itemMeta.pill}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(item.detail, "Sin detalle adicional.")}</p>
              {covered.length ? <p className="mt-3 text-xs leading-5 text-[color:var(--success-text)]">Cubre: {covered.join(" · ")}</p> : null}
              {missing.length ? <p className="mt-2 text-xs leading-5 text-[color:var(--warning-text)]">Falta: {missing.join(" · ")}</p> : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
