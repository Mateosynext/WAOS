import type { ReactNode } from "react";

type FieldBaseProps = {
  label: string;
  hint?: string;
  testId?: string;
};

export function ProgressHeader({ eyebrow, title, description, stepLabel, progress }: { eyebrow: string; title: string; description: string; stepLabel: string; progress: number }) {
  return (
    <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-6 shadow-[var(--shadow-sm)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{eyebrow}</div>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.05em] text-[color:var(--text-primary)]">{title}</h2>
          <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
        </div>
        <div className="min-w-[220px] rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Progreso visible</div>
          <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{stepLabel}</div>
          <div className="mt-3 h-2 rounded-full bg-[color:var(--border-soft)]">
            <div className="h-full rounded-full bg-[color:var(--accent-border)]" style={{ width: `${Math.max(10, Math.min(progress, 100))}%` }} />
          </div>
          <div className="mt-2 text-xs text-[color:var(--text-secondary)]">{Math.round(progress)}% del flujo</div>
        </div>
      </div>
    </div>
  );
}

export function StepRail({ title, items, activeKey, completedKeys = [] }: { title: string; items: Array<{ key: string; label: string; description: string }>; activeKey: string; completedKeys?: string[] }) {
  const completed = new Set(completedKeys);
  return (
    <aside className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
      <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{title}</div>
      <div className="mt-4 grid gap-3">
        {items.map((item, index) => {
          const isActive = item.key === activeKey;
          const isComplete = completed.has(item.key);
          return (
            <div
              key={item.key}
              className={`rounded-[22px] border p-4 transition ${isActive ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)]" : isComplete ? "border-[color:var(--success-border)] bg-[color:var(--success-soft)]" : "border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)]"}`}
            >
              <div className="flex items-start gap-3">
                <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full border text-xs font-semibold ${isActive ? "border-[color:var(--accent-border)] bg-[color:var(--surface-strong)] text-[color:var(--text-primary)]" : isComplete ? "border-[color:var(--success-border)] bg-[color:var(--surface-strong)] text-[color:var(--success-text)]" : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-secondary)]"}`}>{index + 1}</span>
                <div>
                  <div className="text-sm font-semibold text-[color:var(--text-primary)]">{item.label}</div>
                  <p className="mt-1 text-xs leading-5 text-[color:var(--text-secondary)]">{item.description}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

export function FieldGroup({ title, description, children, testId }: { title: string; description: string; children: ReactNode; testId?: string }) {
  return (
    <section data-testid={testId} className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-6 shadow-[var(--shadow-sm)]">
      <div className="max-w-3xl">
        <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Decisión del paso</div>
        <h3 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[color:var(--text-primary)]">{title}</h3>
        <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
      </div>
      <div className="mt-6 grid gap-4">{children}</div>
    </section>
  );
}

export function InputField({ label, hint, value, onChange, placeholder, testId }: FieldBaseProps & { value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="grid gap-2 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <span className="text-sm font-semibold text-[color:var(--text-primary)]">{label}</span>
      {hint ? <span className="text-xs leading-5 text-[color:var(--text-secondary)]">{hint}</span> : null}
      <input data-testid={testId} className="field-input" value={value} onChange={(event) => onChange(event.currentTarget.value)} placeholder={placeholder} />
    </label>
  );
}

export function TextAreaField({ label, hint, value, onChange, placeholder, rows = 5, testId }: FieldBaseProps & { value: string; onChange: (value: string) => void; placeholder?: string; rows?: number }) {
  return (
    <label className="grid gap-2 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <span className="text-sm font-semibold text-[color:var(--text-primary)]">{label}</span>
      {hint ? <span className="text-xs leading-5 text-[color:var(--text-secondary)]">{hint}</span> : null}
      <textarea data-testid={testId} className="field-input min-h-[120px]" rows={rows} value={value} onChange={(event) => onChange(event.currentTarget.value)} placeholder={placeholder} />
    </label>
  );
}

export function SelectField({ label, hint, value, onChange, options, testId }: FieldBaseProps & { value: string; onChange: (value: string) => void; options: Array<{ label: string; value: string }> }) {
  return (
    <label className="grid gap-2 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <span className="text-sm font-semibold text-[color:var(--text-primary)]">{label}</span>
      {hint ? <span className="text-xs leading-5 text-[color:var(--text-secondary)]">{hint}</span> : null}
      <select data-testid={testId} className="field-input" value={value} onChange={(event) => onChange(event.currentTarget.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ChecklistChips({ label, options, selected, onToggle }: { label: string; options: string[]; selected: string[]; onToggle: (value: string) => void }) {
  const active = new Set(selected);
  return (
    <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="text-sm font-semibold text-[color:var(--text-primary)]">{label}</div>
      <div className="mt-3 flex flex-wrap gap-2">
        {options.map((option) => {
          const isActive = active.has(option);
          return (
            <button
              key={option}
              type="button"
              className={`rounded-full border px-3 py-1.5 text-sm transition ${isActive ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] text-[color:var(--text-primary)]" : "border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] text-[color:var(--text-secondary)] hover:border-[color:var(--accent-border)]"}`}
              onClick={() => onToggle(option)}
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function SummaryCard({ title, children, tone = "default", testId }: { title: string; children: ReactNode; tone?: "default" | "accent" | "success" | "warning"; testId?: string }) {
  const toneClass = tone === "accent" ? "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)]" : tone === "success" ? "border-[color:var(--success-border)] bg-[color:var(--success-soft)]" : tone === "warning" ? "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)]" : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)]";
  return (
    <div data-testid={testId} className={`rounded-[24px] border p-4 ${toneClass}`}>
      <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{title}</div>
      <div className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{children}</div>
    </div>
  );
}

export function ActionBar({ previous, next, helper }: { previous?: ReactNode; next?: ReactNode; helper?: ReactNode }) {
  return (
    <div data-testid="wizard-action-bar" className="sticky bottom-4 z-10 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)]/95 p-4 shadow-[var(--shadow-soft)] backdrop-blur">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="text-sm leading-6 text-[color:var(--text-secondary)]">{helper}</div>
        <div className="flex flex-wrap gap-2">{previous}{next}</div>
      </div>
    </div>
  );
}
