import Link from "next/link";
import type { ReactNode } from "react";
import { StatusPill } from "@/app/components/feedback";
import { Badge, Icon } from "@/app/components/primitives/shared";

const surfaceClass = "rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] shadow-[var(--shadow-soft)]";
const subtleSurfaceClass = "rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)]";

export function ClientPanel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`${surfaceClass} ${className}`.trim()}>{children}</div>;
}

export function ClientSectionBlock({ title, subtitle, aside, children }: { title: string; subtitle?: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className={surfaceClass}>
      <div className="flex flex-col gap-4 border-b border-[color:var(--border-soft)] px-5 py-5 sm:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="eyebrow">Portal cliente</div>
            <h2 className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)] sm:text-[1.8rem]">{title}</h2>
            {subtitle ? <p className="mt-3 max-w-3xl text-sm leading-7 text-[color:var(--text-secondary)]">{subtitle}</p> : null}
          </div>
          {aside ? <div className="w-full lg:w-auto">{aside}</div> : null}
        </div>
      </div>
      <div className="px-5 py-5 sm:px-6 sm:py-6">{children}</div>
    </section>
  );
}

export function ClientExecutiveSummary({ title, description, insights, cta }: { title: string; description: string; insights: string[]; cta?: ReactNode }) {
  return (
    <ClientPanel className="overflow-hidden">
      <div className="grid gap-6 p-5 sm:p-6 lg:grid-cols-[1.2fr_0.8fr] lg:p-7">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-[color:var(--info-border)] bg-[color:var(--info-soft)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--info-text)]">
            <Icon name="spark" className="h-4 w-4" />
            Portada ejecutiva
          </div>
          <h2 className="mt-4 text-3xl font-semibold text-[color:var(--text-primary)] sm:text-[2.4rem]">{title}</h2>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-[color:var(--text-secondary)] sm:text-[15px]">{description}</p>
          {cta ? <div className="mt-5 flex flex-wrap gap-3">{cta}</div> : null}
        </div>
        <div className={`${subtleSurfaceClass} p-4 sm:p-5`}>
          <div className="text-sm font-semibold text-[color:var(--text-primary)]">Qué revisar primero</div>
          <ul className="mt-4 space-y-3 text-sm text-[color:var(--text-secondary)]">
            {insights.map((item, index) => (
              <li key={`${item}-${index}`} className="flex items-start gap-3">
                <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[color:var(--accent-soft)] text-xs font-semibold text-[color:var(--accent)]">{index + 1}</span>
                <span className="leading-6">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </ClientPanel>
  );
}

export function ClientMetricCard({ label, value, description, icon, tone = "slate" }: { label: string; value: string; description: string; icon: "chat" | "calendar" | "folder" | "bot" | "promo" | "stats" | "layers" | "tool" | "shield" | "alert"; tone?: "slate" | "green" | "gold" | "blue" }) {
  const badgeTone = tone === "gold" ? "gold" : tone === "green" ? "green" : tone === "blue" ? "sky" : "slate";
  return (
    <ClientPanel className="h-full p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Badge tone={badgeTone}>{label}</Badge>
          <div className="mt-4 text-3xl font-semibold text-[color:var(--text-primary)]">{value}</div>
        </div>
        <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-primary)]">
          <Icon name={icon} className="h-5 w-5" />
        </span>
      </div>
      <p className="mt-4 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
    </ClientPanel>
  );
}

export function ClientNotice({ title, description, tone = "info", action, detail }: { title: string; description: string; tone?: "info" | "success" | "warning" | "danger"; action?: ReactNode; detail?: string }) {
  const palette = {
    info: "border-[color:var(--info-border)] bg-[color:var(--info-soft)] text-[color:var(--info-text)]",
    success: "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success-text)]",
    warning: "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] text-[color:var(--warning-text)]",
    danger: "border-[color:var(--danger-border)] bg-[color:var(--danger-soft)] text-[color:var(--danger-text)]",
  } as const;

  return (
    <div className={`rounded-[24px] border p-4 sm:p-5 ${palette[tone]}`}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="text-base font-semibold">{title}</div>
          <p className="mt-2 max-w-3xl text-sm leading-6 opacity-90">{description}</p>
          {detail ? <p className="mt-2 text-xs leading-5 opacity-75">{detail}</p> : null}
        </div>
        {action ? <div className="w-full lg:w-auto">{action}</div> : null}
      </div>
    </div>
  );
}

export function ClientConversationCard({
  title,
  summary,
  status,
  meta,
  preview,
}: {
  title: string;
  summary: string;
  status: string;
  meta: Array<{ label: string; value: string }>;
  preview?: string;
}) {
  return (
    <ClientPanel className="p-5 sm:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-semibold text-[color:var(--text-primary)]">{title}</h3>
            <StatusPill status={status} />
          </div>
          <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{summary}</p>
        </div>
      </div>
      <dl className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {meta.map((item) => (
          <div key={`${title}-${item.label}`} className={`${subtleSurfaceClass} px-3 py-3`}>
            <dt className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[color:var(--text-muted)]">{item.label}</dt>
            <dd className="mt-2 text-sm text-[color:var(--text-primary)]">{item.value}</dd>
          </div>
        ))}
      </dl>
      {preview ? <div className="mt-5 rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm leading-6 text-[color:var(--text-secondary)]">{preview}</div> : null}
    </ClientPanel>
  );
}

export function ClientAppointmentCard({ title, when, status, chips, detail }: { title: string; when: string; status: string; chips: string[]; detail: string }) {
  return (
    <ClientPanel className="p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-[color:var(--text-primary)]">{title}</h3>
          <p className="mt-2 text-sm text-[color:var(--text-secondary)]">{when}</p>
        </div>
        <StatusPill status={status} />
      </div>
      <p className="mt-4 text-sm leading-6 text-[color:var(--text-secondary)]">{detail}</p>
      <div className="mt-4 flex flex-wrap gap-2">{chips.map((chip) => <span key={`${title}-${chip}`} className="mono-pill">{chip}</span>)}</div>
    </ClientPanel>
  );
}

export function ClientRequestCard({ title, detail, status, kind, createdAt }: { title: string; detail: string; status?: string; kind: string; createdAt: string }) {
  return (
    <ClientPanel className="p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={kind.toLowerCase().includes("feedback") ? "sky" : "gold"}>{kind}</Badge>
            {status ? <StatusPill status={status} /> : null}
          </div>
          <h3 className="mt-3 text-lg font-semibold text-[color:var(--text-primary)]">{title}</h3>
        </div>
        <div className="text-sm text-[color:var(--text-muted)]">{createdAt}</div>
      </div>
      <p className="mt-4 text-sm leading-6 text-[color:var(--text-secondary)]">{detail}</p>
    </ClientPanel>
  );
}

export function ClientPromotionCard({ title, message, validity, status, ctaLabel }: { title: string; message: string; validity: string; status: string; ctaLabel: string }) {
  return (
    <ClientPanel className="h-full overflow-hidden">
      <div className="border-b border-[color:var(--border-soft)] p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Badge tone="gold">Campaña visible</Badge>
          <StatusPill status={status} />
        </div>
        <h3 className="mt-4 text-xl font-semibold text-[color:var(--text-primary)]">{title}</h3>
        <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{message}</p>
      </div>
      <div className="grid gap-3 p-5 sm:p-6">
        <div className={`${subtleSurfaceClass} px-4 py-3`}>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[color:var(--text-muted)]">Vigencia</div>
          <div className="mt-2 text-sm text-[color:var(--text-primary)]">{validity}</div>
        </div>
        <div className={`${subtleSurfaceClass} px-4 py-3`}>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[color:var(--text-muted)]">CTA visible</div>
          <div className="mt-2 text-sm text-[color:var(--text-primary)]">{ctaLabel}</div>
        </div>
      </div>
    </ClientPanel>
  );
}

export function ClientBotAttribute({ label, value, description }: { label: string; value: string; description: string }) {
  return (
    <div className={`${subtleSurfaceClass} p-4`}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[color:var(--text-muted)]">{label}</div>
      <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{value}</div>
      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
    </div>
  );
}

export function ClientEmptyBlock({ title, description, href = "/client/resumen", actionLabel = "Volver al resumen" }: { title: string; description: string; href?: string; actionLabel?: string }) {
  return (
    <ClientNotice
      title={title}
      description={description}
      tone="info"
      action={<Link href={href} className="secondary-btn">{actionLabel}</Link>}
    />
  );
}
