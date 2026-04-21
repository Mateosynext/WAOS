import type { ReactNode } from "react";
import { toneClass } from "./shared";

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-3xl border border-dashed border-[color:var(--border-strong)] bg-[color:var(--surface-subtle)] px-5 py-8 text-sm text-[color:var(--text-secondary)]">
      <div className="text-xl font-semibold text-[color:var(--text-primary)]">{title}</div>
      <div className="mt-2 max-w-2xl leading-6 text-[color:var(--text-secondary)]">{description}</div>
    </div>
  );
}

export function DataTable({ columns, rows }: { columns: string[]; rows: Array<Array<ReactNode>> }) {
  if (!rows.length) return <EmptyState title="Todavía no hay datos" description="Cuando haya información disponible, aparecerá aquí de forma clara y ordenada." />;
  return (
    <div className="overflow-hidden rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)]">
      <div className="overflow-x-auto">
        <table className="waos-data-table min-w-full divide-y divide-[color:var(--border-soft)] text-left text-sm">
          <thead className="bg-[color:var(--surface-subtle)] text-[color:var(--text-secondary)]">
            <tr>{columns.map((column) => <th key={column} className="px-4 py-3 text-[11px] font-medium uppercase tracking-[0.18em]">{column}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] text-[color:var(--text-primary)]">
            {rows.map((row, index) => (
              <tr key={index} className="transition hover:bg-[color:var(--surface-subtle)]">{row.map((cell, cellIndex) => <td key={cellIndex} data-label={columns[cellIndex] || ""} className="px-4 py-3 align-top text-sm text-[color:var(--text-primary)]">{cell}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function KeyValueList({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.label} className="surface-row flex items-center justify-between gap-4">
          <span className="text-sm text-[color:var(--text-secondary)]">{item.label}</span>
          <span className="text-right text-sm font-medium text-[color:var(--text-primary)]">{item.value}</span>
        </div>
      ))}
    </div>
  );
}

export function TimelineList({ items }: { items: Array<{ title: string; detail: string; tone?: "slate" | "green" | "gold" | "red" | "blue" }> }) {
  if (!items.length) return <EmptyState title="Nada por ahora" description="Cuando haya actividad reciente o pasos definidos, aparecerán aquí." />;
  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={`${item.title}-${index}`} className={`rounded-2xl border p-4 ${toneClass(item.tone || "slate")}`}>
          <div className="flex items-start gap-3">
            <div className="grid h-8 w-8 place-items-center rounded-full border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-sm font-semibold text-[color:var(--text-primary)]">{index + 1}</div>
            <div>
              <div className="font-medium text-[color:var(--text-primary)]">{item.title}</div>
              <div className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{item.detail}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function StoryBeat({ step, title, description, outcome, tone = "slate" }: { step: string; title: string; description: string; outcome?: string; tone?: "slate" | "green" | "gold" | "red" | "blue" }) {
  return (
    <div className={`rounded-3xl border p-5 ${toneClass(tone)}`}>
      <div className="eyebrow">{step}</div>
      <div className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">{title}</div>
      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
      {outcome ? <div className="mt-4 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm text-[color:var(--text-secondary)]">{outcome}</div> : null}
    </div>
  );
}

export function StageRail({ steps, activeStep }: { steps: Array<{ id: string; label?: string; title?: string; detail?: string }>; activeStep?: string }) {
  return (
    <div className="space-y-3">
      {steps.map((step, index) => {
        const active = activeStep ? step.id === activeStep : index === 0;
        return (
          <div key={step.id} className={`rounded-2xl border px-4 py-3 ${active ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)]" : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)]"}`}>
            <div className="flex items-center gap-3">
              <span className={`grid h-8 w-8 place-items-center rounded-full text-sm font-semibold ${active ? "bg-[color:var(--accent)] text-[color:var(--accent-foreground)]" : "border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-primary)]"}`}>{index + 1}</span>
              <div>
                <div className="font-medium text-[color:var(--text-primary)]">{step.label || step.title || `Paso ${index + 1}`}</div>
                {step.detail ? <div className="text-sm text-[color:var(--text-secondary)]">{step.detail}</div> : null}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
