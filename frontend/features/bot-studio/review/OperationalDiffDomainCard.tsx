import { safeText } from "@/shared/lib/ui";
import type { WizardDryRunDomain } from "@/features/bot-studio/domain/wizardTypes";
import { diffStatusMeta } from "./reviewUtils";

export function OperationalDiffDomainCard({ block }: { block: WizardDryRunDomain }) {
  const meta = diffStatusMeta(block.status);
  const counters = block.counters || {};
  const items = block.items || [];
  return (
    <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-base font-semibold text-[color:var(--text-primary)]">{safeText(block.label, "Dominio")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(block.detail, "Sin detalle adicional.")}</p>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${meta.tone}`}>{meta.pill}</span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {(block.badges?.length
          ? block.badges
          : [
            counters.added ? `+${counters.added} cambios` : "",
            counters.removed ? `-${counters.removed} cambios` : "",
            counters.replaced ? `reemplaza ${counters.replaced}` : "",
          ].filter(Boolean)
        ).slice(0, 6).map((badge) => (
          <span key={badge} className="mono-pill">{badge}</span>
        ))}
        {!block.badges?.length && !counters.added && !counters.removed && !counters.replaced ? <span className="mono-pill">Sin cambio material visible</span> : null}
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-4">
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-2 text-sm text-[color:var(--text-secondary)]">Se conserva <strong className="text-[color:var(--text-primary)]">{safeText(String(counters.kept || 0), "0")}</strong></div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-2 text-sm text-[color:var(--text-secondary)]">Se reemplaza <strong className="text-[color:var(--text-primary)]">{safeText(String(counters.replaced || 0), "0")}</strong></div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-2 text-sm text-[color:var(--text-secondary)]">Se agrega <strong className="text-[color:var(--text-primary)]">{safeText(String(counters.added || 0), "0")}</strong></div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-2 text-sm text-[color:var(--text-secondary)]">Se elimina <strong className="text-[color:var(--text-primary)]">{safeText(String(counters.removed || 0), "0")}</strong></div>
      </div>

      <div className="mt-4 grid gap-3">
        {items.map((item, index) => {
          const itemMeta = diffStatusMeta(item.status);
          return (
            <div key={safeText(item.key || item.label, `domain-item-${index}`)} className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="text-sm font-semibold text-[color:var(--text-primary)]">{safeText(item.label, "Cambio")}</div>
                <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${itemMeta.tone}`}>{itemMeta.pill}</span>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Antes</div>
                  <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(item.before, "Sin valor previo")}</p>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Después</div>
                  <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(item.after, "Sin valor propuesto")}</p>
                </div>
              </div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(item.detail, "Sin detalle adicional.")}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
