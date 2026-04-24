import type { ReactNode } from "react";

export default function SuccessState({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) {
  return (
    <div className="rounded-3xl border border-[color:var(--success-border)] bg-[color:var(--success-soft)] p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-[color:var(--success-border)] bg-[color:var(--surface-strong)] text-[color:var(--success-text)]">
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <circle cx="12" cy="12" r="9" />
            <path d="m8.5 12.5 2.2 2.2 4.8-5" />
          </svg>
        </span>
        <div className="min-w-0">
          <div className="text-lg font-semibold text-[color:var(--text-primary)]">{title}</div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--success-text)]">{description}</p>
          {actions ? <div className="mt-4 flex flex-wrap gap-2">{actions}</div> : null}
        </div>
      </div>
    </div>
  );
}
