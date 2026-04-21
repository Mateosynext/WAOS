import type { ReactNode } from "react";
import { Icon, type IconName, toneClass } from "./shared";

export function Section({ title, subtitle, children, icon = "spark", aside }: { title: string; subtitle?: string; children: ReactNode; icon?: IconName; aside?: ReactNode }) {
  return (
    <section className="panel p-5 lg:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="eyebrow">Sección</div>
          <div className="mt-2 flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-primary)]">
              <Icon name={icon} className="h-5 w-5" />
            </span>
            <h2 className="text-2xl font-semibold tracking-[-0.04em] text-[color:var(--text-primary)]">{title}</h2>
          </div>
          {subtitle ? <p className="mt-3 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">{subtitle}</p> : null}
        </div>
        {aside ? <div>{aside}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function StatCard({ label, value, hint, icon = "spark", tone = "slate" }: { label: string; value: string | number | null | undefined; hint?: string; icon?: IconName; tone?: "slate" | "green" | "gold" | "red" | "blue" }) {
  return (
    <div className={`panel p-5 ${toneClass(tone)}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="eyebrow">{label}</div>
          <div className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-[color:var(--text-primary)]">{value ?? "-"}</div>
        </div>
        <div className="grid h-11 w-11 place-items-center rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-primary)]">
          <Icon name={icon} className="h-5 w-5" />
        </div>
      </div>
      {hint ? <div className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{hint}</div> : null}
    </div>
  );
}

export function ModuleCard({ title, description, tone = "slate", icon = "spark", footer }: { title: string; description: string; tone?: "slate" | "green" | "gold" | "red" | "blue"; icon?: IconName; footer?: ReactNode }) {
  return (
    <div className={`rounded-3xl border p-4 transition duration-200 hover:-translate-y-0.5 ${toneClass(tone)}`}>
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-primary)]">
          <Icon name={icon} className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <div className="text-base font-semibold text-[color:var(--text-primary)]">{title}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
        </div>
      </div>
      {footer ? <div className="mt-4 flex flex-wrap gap-2">{footer}</div> : null}
    </div>
  );
}
