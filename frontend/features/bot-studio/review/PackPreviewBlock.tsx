import { SummaryList } from "./reviewUtils";

export function PackPreviewBlock({
  eyebrow,
  title,
  description,
  createItems,
  reuseItems,
  pendingItems,
  createLabel = "Qué se crea",
  reuseLabel = "Qué se reusa",
  pendingLabel = "Qué queda pendiente",
  pendingFallback = "Nada pendiente por cerrar en este bloque.",
}: {
  eyebrow: string;
  title: string;
  description: string;
  createItems: string[];
  reuseItems: string[];
  pendingItems: string[];
  createLabel?: string;
  reuseLabel?: string;
  pendingLabel?: string;
  pendingFallback?: string;
}) {
  return (
    <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{eyebrow}</div>
      <h4 className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">{title}</h4>
      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>

      <div className="mt-4 grid gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{createLabel} ({createItems.length})</div>
          <SummaryList items={createItems} fallback="No hay creación nueva visible en este bloque." />
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{reuseLabel} ({reuseItems.length})</div>
          <SummaryList items={reuseItems} fallback="No se reusa nada visible del estado actual." />
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{pendingLabel} ({pendingItems.length})</div>
          <SummaryList items={pendingItems} fallback={pendingFallback} />
        </div>
      </div>
    </div>
  );
}
