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


export type OperationalStateLike = {
  ok: boolean;
  endpoint: string;
  error: { status?: number | null; code?: string | null; message?: string | null } | null;
};

export function hasOperationalFailures(states: OperationalStateLike[]): boolean {
  return states.some((state) => !state.ok);
}

export function OperationalDegradedBanner({
  states,
  title = "Backend degradado",
  description = "Esta vista no va a mostrar datos vacíos como si fueran sanos. Revisa los endpoints fallidos antes de tomar decisiones operativas.",
  block = false,
}: {
  states: OperationalStateLike[];
  title?: string;
  description?: string;
  block?: boolean;
}) {
  const failures = states.filter((state) => !state.ok);
  if (!failures.length) return null;
  return (
    <div className="rounded-3xl border border-[color:var(--danger-border)] bg-[color:var(--danger-soft)] p-5 text-[color:var(--danger-text)]">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Badge tone="red">{block ? "BLOQUEADO" : "DEGRADADO"}</Badge>
            <div className="text-lg font-semibold text-[color:var(--text-primary)]">{title}</div>
          </div>
          <p className="mt-2 max-w-4xl text-sm leading-6">{description}</p>
          {block ? <p className="mt-2 text-sm font-semibold">Los KPIs y tablas críticas quedan bloqueados para evitar decisiones con datos incompletos.</p> : null}
        </div>
      </div>
      <div className="mt-4 grid gap-2">
        {failures.slice(0, 8).map((state) => (
          <div key={state.endpoint} className="rounded-2xl border border-[color:var(--danger-border)] bg-[color:var(--surface-strong)] p-3 text-sm">
            <div className="font-mono text-xs text-[color:var(--text-primary)]">{state.endpoint}</div>
            <div className="mt-1 text-[color:var(--danger-text)]">
              {state.error?.status ?? "sin_status"} · {state.error?.code || "api_error"} · {state.error?.message || "Backend no respondió correctamente"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
