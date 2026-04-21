import type { ReactNode } from "react";
import { Badge, Icon } from "../primitives/shared";

export function StatusPill({ status }: { status: string | null | undefined }) {
  const raw = String(status || "sin_dato").toLowerCase();
  let tone: "slate" | "green" | "amber" | "red" | "sky" | "gold" = "slate";
  if (["active", "available", "published", "activo", "ok", "healthy", "connected", "completed", "ready"].includes(raw)) tone = "green";
  else if (["draft", "paused", "scheduled", "warning", "pending", "review", "running", "degraded"].includes(raw)) tone = "amber";
  else if (["failed", "error", "dead_letter", "disconnected", "out_of_stock"].includes(raw)) tone = "red";
  else if (["whatsapp", "instagram_dm", "webchat", "service", "bot"].includes(raw)) tone = "sky";
  return <Badge tone={tone}>{status || "sin dato"}</Badge>;
}

export function ContextTip({ title = "Ayuda breve", children }: { title?: string; children: ReactNode }) {
  return (
    <div className="rounded-3xl border border-[color:var(--info-border)] bg-[color:var(--info-soft)] p-4 text-sm text-[color:var(--info-text)]">
      <div className="font-semibold text-[color:var(--text-primary)]">{title}</div>
      <div className="mt-2 leading-6 text-[color:var(--info-text)]">{children}</div>
    </div>
  );
}

export function SuccessState({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) {
  return (
    <div className="rounded-3xl border border-[color:var(--success-border)] bg-[color:var(--success-soft)] p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-[color:var(--success-border)] bg-[color:var(--surface-strong)] text-[color:var(--success-text)]">
          <Icon name="check" className="h-5 w-5" />
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

export function EmptyActionState({ title, description, primaryAction, secondaryAction }: { title: string; description: string; primaryAction?: ReactNode; secondaryAction?: ReactNode }) {
  return (
    <div className="rounded-3xl border border-dashed border-[color:var(--border-strong)] bg-[color:var(--surface-subtle)] p-6">
      <div className="max-w-2xl">
        <div className="text-xl font-semibold text-[color:var(--text-primary)]">{title}</div>
        <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
      </div>
      {(primaryAction || secondaryAction) ? <div className="mt-4 flex flex-wrap gap-2">{primaryAction}{secondaryAction}</div> : null}
    </div>
  );
}

export function PermissionGate({ allowed, fallback = null, children }: { allowed: boolean; fallback?: ReactNode; children: ReactNode }) {
  return allowed ? <>{children}</> : <>{fallback}</>;
}
