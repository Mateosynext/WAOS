import { diffStatusMeta, type DiffStatus } from "./reviewUtils";

export function DiffCard({ title, before, after, status, detail }: { title: string; before: string; after: string; status: DiffStatus; detail: string }) {
  const meta = diffStatusMeta(status);
  return (
    <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="text-base font-semibold text-[color:var(--text-primary)]">{title}</div>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${meta.tone}`}>{meta.pill}</span>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Antes</div>
          <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{before}</p>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Después</div>
          <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{after}</p>
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{detail}</p>
    </div>
  );
}
