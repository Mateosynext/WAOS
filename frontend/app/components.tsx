import Link from "next/link";
import { ReactNode } from "react";
import { logoutAction, switchOrganizationAction } from "./actions";
import OrganizationSwitcher from "./components/OrganizationSwitcher";
import { UiMessage } from "./components/UiMessage";
import { getSession } from "./lib/session";

export type AppMode = "superadmin" | "client";

type IconName =
  | "dashboard"
  | "briefcase"
  | "catalog"
  | "image"
  | "promo"
  | "bot"
  | "insights"
  | "sales"
  | "flow"
  | "calendar"
  | "channel"
  | "client"
  | "stack"
  | "chat"
  | "logs"
  | "rocket"
  | "clock"
  | "plug"
  | "shield"
  | "gear"
  | "usage"
  | "spark"
  | "check"
  | "alert"
  | "money"
  | "stats"
  | "play"
  | "target"
  | "wand"
  | "route"
  | "palette"
  | "layers"
  | "folder"
  | "tool"
  | "support"
  | "refresh";

const superAdminNavigation = [
  {
    group: "Inicio y enfoque",
    items: [
      { label: "Home", href: "/", icon: "dashboard" as const },
      { label: "Onboarding", href: "/onboarding", icon: "route" as const },
      { label: "Verticales", href: "/verticals", icon: "layers" as const },
      { label: "Búsqueda", href: "/search", icon: "target" as const },
    ],
  },
  {
    group: "Trabajo diario",
    items: [
      { label: "Inbox", href: "/inbox", icon: "chat" as const },
      { label: "Agenda", href: "/agenda", icon: "calendar" as const },
      { label: "Resultados", href: "/insights", icon: "insights" as const },
      { label: "Clientes", href: "/client", icon: "client" as const },
    ],
  },
  {
    group: "Configuración y salida",
    items: [
      { label: "Bots", href: "/bots", icon: "bot" as const },
      { label: "Integraciones", href: "/integrations", icon: "plug" as const },
      { label: "Releases", href: "/releases", icon: "layers" as const },
    ],
  },
  {
    group: "Mantenimiento",
    items: [
      { label: "Estado", href: "/status", icon: "stats" as const },
      { label: "Seguridad", href: "/security", icon: "shield" as const },
      { label: "Scheduler", href: "/scheduler", icon: "clock" as const },
      { label: "Soporte", href: "/support", icon: "support" as const },
    ],
  },
] as const;

const clientNavigation = [
  { label: "Resumen", href: "/client?section=resumen", icon: "dashboard" as const },
  { label: "Conversaciones", href: "/client?section=conversaciones", icon: "chat" as const },
  { label: "Agenda", href: "/client?section=agenda", icon: "calendar" as const },
  { label: "Promociones", href: "/client?section=promociones", icon: "promo" as const },
  { label: "Solicitudes", href: "/client?section=solicitudes", icon: "folder" as const },
  { label: "Estado del bot", href: "/client?section=bot", icon: "bot" as const },
] as const;

export function Icon({ name, className = "h-4 w-4" }: { name: IconName; className?: string }) {
  const shared = {
    className,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (name) {
    case "dashboard": return <svg {...shared}><rect x="3" y="3" width="8" height="8" rx="2" /><rect x="13" y="3" width="8" height="5" rx="2" /><rect x="13" y="10" width="8" height="11" rx="2" /><rect x="3" y="13" width="8" height="8" rx="2" /></svg>;
    case "briefcase": return <svg {...shared}><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><rect x="3" y="7" width="18" height="13" rx="3" /><path d="M3 12h18" /></svg>;
    case "catalog": return <svg {...shared}><path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 0-3 3z" /><path d="M5 4v16a3 3 0 0 1 3-3h11" /></svg>;
    case "image": return <svg {...shared}><rect x="3" y="4" width="18" height="16" rx="3" /><circle cx="9" cy="10" r="1.5" /><path d="m21 16-4.5-4.5a2 2 0 0 0-2.8 0L7 18" /></svg>;
    case "promo": return <svg {...shared}><path d="M20 12V8a2 2 0 0 0-2-2h-4l-2-3-2 3H6a2 2 0 0 0-2 2v4l-1.5 2L4 16v4a2 2 0 0 0 2 2h4l2 3 2-3h4a2 2 0 0 0 2-2v-4l1.5-2z" /><path d="M9 12h6" /></svg>;
    case "bot": return <svg {...shared}><rect x="6" y="8" width="12" height="10" rx="3" /><path d="M9 8V5a3 3 0 0 1 6 0v3" /><circle cx="10" cy="13" r="1" /><circle cx="14" cy="13" r="1" /><path d="M9 17h6" /></svg>;
    case "insights": return <svg {...shared}><path d="M4 19V5" /><path d="M20 19H4" /><rect x="7" y="11" width="3" height="6" rx="1" /><rect x="12" y="8" width="3" height="9" rx="1" /><rect x="17" y="5" width="3" height="12" rx="1" /></svg>;
    case "sales": return <svg {...shared}><path d="M12 2v20" /><path d="M17 6.5c0-1.7-2.2-3-5-3s-5 1.3-5 3 1.5 2.6 5 3 5 1.3 5 3-2.2 3-5 3-5-1.3-5-3" /></svg>;
    case "flow": return <svg {...shared}><circle cx="6" cy="6" r="2" /><circle cx="18" cy="6" r="2" /><circle cx="18" cy="18" r="2" /><path d="M8 6h8" /><path d="M18 8v8" /><path d="M16 18H8" /><path d="m8 18-2-2" /></svg>;
    case "calendar": return <svg {...shared}><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M8 3v4" /><path d="M16 3v4" /><path d="M3 10h18" /></svg>;
    case "channel": return <svg {...shared}><path d="M7 7h10" /><path d="M7 12h10" /><path d="M7 17h6" /><rect x="3" y="4" width="18" height="16" rx="3" /></svg>;
    case "client": return <svg {...shared}><rect x="7" y="2.5" width="10" height="19" rx="3" /><path d="M10 6h4" /><circle cx="12" cy="18" r="0.7" /></svg>;
    case "stack": return <svg {...shared}><path d="m12 3 8 4-8 4-8-4 8-4Z" /><path d="m4 12 8 4 8-4" /><path d="m4 17 8 4 8-4" /></svg>;
    case "chat": return <svg {...shared}><path d="M7 18l-4 3V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3H7z" /><path d="M8 9h8" /><path d="M8 13h5" /></svg>;
    case "logs": return <svg {...shared}><path d="M8 6h12" /><path d="M8 12h12" /><path d="M8 18h12" /><path d="M4 6h.01" /><path d="M4 12h.01" /><path d="M4 18h.01" /></svg>;
    case "rocket": return <svg {...shared}><path d="M5 19c2.5-1 4-2.5 5-5" /><path d="M14 10 9 15" /><path d="m12 4 8 8" /><path d="M20 8c0-2-2-4-4-4-3 0-6 2-7 4l-2 5 5-2c2-1 4-4 4-7Z" /></svg>;
    case "clock": return <svg {...shared}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>;
    case "plug": return <svg {...shared}><path d="M9 8V3" /><path d="M15 8V3" /><path d="M8 8h8v3a4 4 0 0 1-4 4v6" /><path d="M8 8v3" /><path d="M16 8v3" /></svg>;
    case "shield": return <svg {...shared}><path d="M12 3 5 6v5c0 5 3.5 8.5 7 10 3.5-1.5 7-5 7-10V6l-7-3Z" /><path d="m9.5 12 1.7 1.7 3.8-3.8" /></svg>;
    case "gear": return <svg {...shared}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a2 2 0 1 1-4 0v-.2a1 1 0 0 0-.6-.9 1 1 0 0 0-1.1.2l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H4a2 2 0 1 1 0-4h.2a1 1 0 0 0 .9-.6 1 1 0 0 0-.2-1.1l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1 1 0 0 0 1.1.2 1 1 0 0 0 .6-.9V4a2 2 0 1 1 4 0v.2a1 1 0 0 0 .6.9 1 1 0 0 0 1.1-.2l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1 1 0 0 0-.2 1.1 1 1 0 0 0 .9.6H20a2 2 0 1 1 0 4h-.2a1 1 0 0 0-.9.6Z" /></svg>;
    case "usage": return <svg {...shared}><path d="M12 3v18" /><path d="M6 8h8a3 3 0 0 1 0 6H10a3 3 0 0 0 0 6h8" /></svg>;
    case "spark": return <svg {...shared}><path d="m12 3 2.2 5.8L20 11l-5.8 2.2L12 19l-2.2-5.8L4 11l5.8-2.2L12 3Z" /></svg>;
    case "check": return <svg {...shared}><circle cx="12" cy="12" r="9" /><path d="m8.5 12.5 2.2 2.2 4.8-5" /></svg>;
    case "alert": return <svg {...shared}><path d="M12 3 2.5 19.5h19Z" /><path d="M12 9v4" /><path d="M12 16h.01" /></svg>;
    case "money": return <svg {...shared}><rect x="3" y="6" width="18" height="12" rx="3" /><circle cx="12" cy="12" r="2.5" /><path d="M7 12h.01" /><path d="M17 12h.01" /></svg>;
    case "stats": return <svg {...shared}><path d="M4 19h16" /><path d="m6 16 4-5 3 2 5-7" /><path d="M18 6h0" /></svg>;
    case "play": return <svg {...shared}><circle cx="12" cy="12" r="9" /><path d="m10 9 5 3-5 3z" /></svg>;
    case "target": return <svg {...shared}><circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="4.5" /><circle cx="12" cy="12" r="1" /></svg>;
    case "wand": return <svg {...shared}><path d="m4 20 7-7" /><path d="m14 6 4-4" /><path d="m15 3 1 2" /><path d="m20 8 1 2" /><path d="M10 5l1.5 3.5L15 10l-3.5 1.5L10 15l-1.5-3.5L5 10l3.5-1.5L10 5Z" /></svg>;
    case "route": return <svg {...shared}><circle cx="6" cy="6" r="2" /><circle cx="18" cy="18" r="2" /><path d="M8 6h5a3 3 0 0 1 3 3v3" /><path d="m15 15 3 3" /><path d="M18 15v3h-3" /></svg>;
    case "palette": return <svg {...shared}><path d="M12 3a9 9 0 1 0 0 18h1.2a2.8 2.8 0 0 0 0-5.6H12a2 2 0 0 1 0-4h4a5 5 0 0 0 0-10Z" /><circle cx="7.5" cy="11" r="1" /><circle cx="9.5" cy="7.5" r="1" /><circle cx="14" cy="7" r="1" /></svg>;
    case "layers": return <svg {...shared}><path d="m12 4 8 4-8 4-8-4 8-4Z" /><path d="m4 12 8 4 8-4" /><path d="m4 16 8 4 8-4" /></svg>;
    case "folder": return <svg {...shared}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3z" /></svg>;
    case "tool": return <svg {...shared}><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17v3h3l5.3-5.3a4 4 0 0 0 5.4-5.4l-2.3 2.3-3-1 1-3z" /></svg>;
    case "support": return <svg {...shared}><path d="M12 17v.01" /><path d="M9.1 9a3 3 0 1 1 5.8 1c0 2-3 2-3 5" /><circle cx="12" cy="12" r="9" /></svg>;
    case "refresh": return <svg {...shared}><path d="M20 11a8 8 0 1 0 2 5.3" /><path d="M20 4v7h-7" /></svg>;
    default: return <svg {...shared}><circle cx="12" cy="12" r="9" /></svg>;
  }
}

function toneClass(tone: string) {
  const tones: Record<string, string> = {
    slate: "border-white/[0.10] bg-white/[0.04] text-slate-100",
    green: "border-emerald-400/[0.20] bg-emerald-400/[0.10] text-emerald-50",
    blue: "border-sky-400/[0.20] bg-sky-400/[0.10] text-sky-50",
    gold: "border-amber-400/[0.20] bg-amber-400/[0.10] text-amber-50",
    red: "border-rose-400/[0.20] bg-rose-400/[0.10] text-rose-50",
    sky: "border-sky-400/[0.20] bg-sky-400/[0.10] text-sky-50",
    amber: "border-amber-400/[0.20] bg-amber-400/[0.10] text-amber-50",
  };
  return tones[tone] || tones.slate;
}

function formatLabel(label: string) {
  return label.length > 26 ? `${label.slice(0, 26)}…` : label;
}

export async function Shell({
  title,
  subtitle,
  children,
  action,
  mode = "superadmin",
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  action?: ReactNode;
  mode?: AppMode;
}) {
  const session = await getSession();
  const org = session?.user.organizations?.find((item) => item.id === session?.organizationId) || null;
  const name = session?.user.full_name || session?.user.email || "Sin sesión";
  const navigation = mode === "client" ? [] : superAdminNavigation;

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.12),_transparent_24%),radial-gradient(circle_at_right,_rgba(34,197,94,0.12),_transparent_18%),linear-gradient(180deg,#07111f_0%,#0b1220_100%)] text-slate-50">
      <div className="mx-auto grid min-h-screen max-w-[1600px] gap-6 px-4 py-4 lg:grid-cols-[292px_minmax(0,1fr)] lg:px-6">
        {mode === "superadmin" ? (
          <aside className="panel sticky top-4 hidden h-[calc(100vh-2rem)] overflow-hidden lg:flex lg:flex-col">
            <div className="border-b border-white/[0.08] px-5 py-5">
              <div className="flex items-center gap-3">
                <div className="grid h-12 w-12 place-items-center rounded-2xl border border-emerald-400/[0.25] bg-emerald-400/[0.12] text-emerald-200">
                  <Icon name="bot" className="h-6 w-6" />
                </div>
                <div>
                  <div className="text-lg font-semibold text-white">WAOS</div>
                  <div className="text-sm text-slate-400">Modo super admin</div>
                </div>
              </div>
              <div className="mt-4 rounded-2xl border border-white/[0.08] bg-white/[0.04] px-4 py-3 text-sm text-slate-300">
                <div className="font-medium text-white">{org?.name || "Organización"}</div>
                <div className="mt-1 text-slate-400">{org?.vertical || "Operación omnicanal"}</div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4">
              <nav className="space-y-5">
                {navigation.map((group) => (
                  <div key={group.group} className="space-y-2">
                    <div className="px-2 text-[11px] font-medium uppercase tracking-[0.22em] text-slate-500">{group.group}</div>
                    <div className="space-y-1.5">
                      {group.items.map((item) => (
                        <Link key={item.href} href={item.href} className="nav-link flex items-center gap-3">
                          <span className="grid h-9 w-9 place-items-center rounded-xl border border-white/[0.08] bg-white/[0.04] text-slate-200">
                            <Icon name={item.icon} className="h-4 w-4" />
                          </span>
                          <span>{item.label}</span>
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}
              </nav>
            </div>

            <div className="border-t border-white/[0.08] px-4 py-4">
              <div className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-4">
                <div className="text-sm font-medium text-white">{formatLabel(name)}</div>
                <div className="mt-1 text-xs text-slate-400">{session?.user.global_role || "super_admin"}</div>
                <div className="mt-3 flex gap-2">
                  <Link href="/search" className="secondary-btn flex-1">Buscar</Link>
                  <Link href="/client" className="secondary-btn flex-1">Portal cliente</Link>
                  <form action={logoutAction} className="flex-1">
                    <button type="submit" className="secondary-btn w-full">Salir</button>
                  </form>
                </div>
              </div>
            </div>
          </aside>
        ) : null}

        <section className="min-w-0 pb-6">
          <header className="panel px-5 py-5 lg:px-6 lg:py-6">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={mode === "client" ? "sky" : "green"}>{mode === "client" ? "Portal cliente" : "Modo super admin"}</Badge>
                  {org?.name ? <Badge tone="slate">{org.name}</Badge> : null}
                  {session?.user.organizations && session.user.organizations.length > 1 ? (
                    <OrganizationSwitcher organizations={session.user.organizations.map((item) => ({ id: item.id, name: item.name }))} selectedId={session.organizationId || null} redirectTo={mode === "client" ? "/client" : "/"} action={switchOrganizationAction} />
                  ) : null}
                </div>
                <div>
                  <h1 className="text-3xl font-semibold tracking-[-0.05em] text-white lg:text-4xl">{title}</h1>
                  <p className="mt-3 max-w-4xl text-sm leading-7 text-slate-300 lg:text-[15px]">{subtitle}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-3">{action}</div>
            </div>
            {mode === "superadmin" && session?.user.organizations && session.user.organizations.length > 1 && !session.organizationId ? (
              <div className="mt-5"><UiMessage title="Selecciona una organización" tone="warning">Tu sesión tiene más de una organización disponible. Elige una arriba o ve a <a className="underline" href="/organizations">/organizations</a> para fijar el contexto antes de operar.</UiMessage></div>
            ) : null}
            <div className="mt-5 flex flex-wrap gap-3 border-t border-white/[0.08] pt-5">
              {mode === "superadmin" ? (
                <>
                  <Link href="/" className="primary-btn">Home super admin</Link>
                  <Link href="/onboarding" className="secondary-btn">Onboarding</Link>
                  <Link href="/client" className="secondary-btn">Portal cliente</Link>
                </>
              ) : (
                <>
                  <Link href="/client?section=resumen" className="primary-btn">Home cliente</Link>
                  <Link href="/client?section=solicitudes" className="secondary-btn">Solicitudes</Link>
                </>
              )}
            </div>
          </header>
          <div className="mt-6 space-y-6">{children}</div>
        </section>
      </div>
    </main>
  );
}

export function Section({ title, subtitle, children, icon = "spark", aside }: { title: string; subtitle?: string; children: ReactNode; icon?: IconName; aside?: ReactNode }) {
  return (
    <section className="panel p-5 lg:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="eyebrow">Sección</div>
          <div className="mt-2 flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-2xl border border-white/[0.08] bg-white/[0.04] text-slate-100">
              <Icon name={icon} className="h-5 w-5" />
            </span>
            <h2 className="text-2xl font-semibold tracking-[-0.04em] text-white">{title}</h2>
          </div>
          {subtitle ? <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">{subtitle}</p> : null}
        </div>
        {aside ? <div>{aside}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function StatCard({ label, value, hint, icon = "spark", tone = "slate" }: { label: string; value: string | number | null | undefined; hint?: string; icon?: IconName; tone?: "slate" | "green" | "gold" | "red" | "blue"; }) {
  return (
    <div className={`panel p-5 ${toneClass(tone)}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="eyebrow">{label}</div>
          <div className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-white">{value ?? "-"}</div>
        </div>
        <div className="grid h-11 w-11 place-items-center rounded-2xl border border-white/[0.08] bg-white/[0.04] text-slate-100">
          <Icon name={icon} className="h-5 w-5" />
        </div>
      </div>
      {hint ? <div className="mt-3 text-sm leading-6 text-slate-300">{hint}</div> : null}
    </div>
  );
}

export function ModuleCard({ title, description, tone = "slate", icon = "spark", footer }: { title: string; description: string; tone?: "slate" | "green" | "gold" | "red" | "blue"; icon?: IconName; footer?: ReactNode; }) {
  return (
    <div className={`rounded-3xl border p-4 transition duration-200 hover:-translate-y-0.5 ${toneClass(tone)}`}>
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-white/[0.08] bg-white/[0.04] text-slate-100">
          <Icon name={icon} className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <div className="text-base font-semibold text-white">{title}</div>
          <p className="mt-2 text-sm leading-6 text-slate-300">{description}</p>
        </div>
      </div>
      {footer ? <div className="mt-4 flex flex-wrap gap-2">{footer}</div> : null}
    </div>
  );
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "green" | "amber" | "red" | "sky" | "gold"; }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.16em] ${toneClass(tone)}`}>{children}</span>;
}

export function StatusPill({ status }: { status: string | null | undefined }) {
  const raw = String(status || "sin_dato").toLowerCase();
  let tone: "slate" | "green" | "amber" | "red" | "sky" | "gold" = "slate";
  if (["active", "available", "published", "activo", "ok", "healthy", "connected", "completed", "ready"].includes(raw)) tone = "green";
  else if (["draft", "paused", "scheduled", "warning", "pending", "review", "running", "degraded"].includes(raw)) tone = "amber";
  else if (["failed", "error", "dead_letter", "disconnected", "out_of_stock"].includes(raw)) tone = "red";
  else if (["whatsapp", "instagram_dm", "webchat", "service", "bot"].includes(raw)) tone = "sky";
  return <Badge tone={tone}>{status || "sin dato"}</Badge>;
}

export function EmptyState({ title, description }: { title: string; description: string; }) {
  return (
    <div className="rounded-3xl border border-dashed border-white/[0.15] bg-white/[0.03] px-5 py-8 text-sm text-slate-300">
      <div className="text-xl font-semibold text-white">{title}</div>
      <div className="mt-2 max-w-2xl leading-6 text-slate-300">{description}</div>
    </div>
  );
}

export function DataTable({ columns, rows }: { columns: string[]; rows: Array<Array<ReactNode>>; }) {
  if (!rows.length) return <EmptyState title="Todavía no hay datos" description="Cuando haya información disponible, aparecerá aquí de forma clara y ordenada." />;
  return (
    <div className="overflow-hidden rounded-3xl border border-white/[0.08]">
      <table className="min-w-full divide-y divide-white/[0.08] text-left text-sm">
        <thead className="bg-white/[0.05] text-slate-300">
          <tr>{columns.map((column) => <th key={column} className="px-4 py-3 text-[11px] font-medium uppercase tracking-[0.18em]">{column}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-white/[0.08] bg-slate-950/20 text-slate-100">
          {rows.map((row, index) => (
            <tr key={index} className="transition hover:bg-white/[0.03]">{row.map((cell, cellIndex) => <td key={cellIndex} className="px-4 py-3 align-top text-sm text-slate-100">{cell}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SegmentedLinks({ items }: { items: Array<{ href: string; label: string; active?: boolean }> }) {
  return <div className="flex flex-wrap gap-2">{items.map((item) => <Link key={`${item.href}-${item.label}`} href={item.href} className={item.active ? "primary-btn" : "secondary-btn"}>{item.label}</Link>)}</div>;
}

export function ThemeBadge({ label, tone = "slate" }: { label: string; tone?: "slate" | "green" | "gold" | "red" | "blue" | "sky"; }) {
  return <Badge tone={tone === "blue" ? "sky" : tone}>{label}</Badge>;
}

export function KeyValueList({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.label} className="surface-row flex items-center justify-between gap-4">
          <span className="text-sm text-slate-300">{item.label}</span>
          <span className="text-right text-sm font-medium text-white">{item.value}</span>
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
            <div className="grid h-8 w-8 place-items-center rounded-full bg-white/[0.10] text-sm font-semibold text-white">{index + 1}</div>
            <div>
              <div className="font-medium text-white">{item.title}</div>
              <div className="mt-1 text-sm leading-6 text-slate-300">{item.detail}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function PortalTabs({ current }: { current: string }) {
  return <SegmentedLinks items={clientNavigation.map((item) => ({ ...item, active: item.href.includes(`section=${current}`) || (current === "resumen" && item.href.endsWith("resumen")) }))} />;
}

export function StoryBeat({ step, title, description, outcome, tone = "slate" }: { step: string; title: string; description: string; outcome?: string; tone?: "slate" | "green" | "gold" | "red" | "blue" }) {
  return (
    <div className={`rounded-3xl border p-5 ${toneClass(tone)}`}>
      <div className="eyebrow">{step}</div>
      <div className="mt-2 text-lg font-semibold text-white">{title}</div>
      <p className="mt-2 text-sm leading-6 text-slate-300">{description}</p>
      {outcome ? <div className="mt-4 rounded-2xl border border-white/[0.08] bg-white/[0.04] px-4 py-3 text-sm text-slate-200">{outcome}</div> : null}
    </div>
  );
}

export function StageRail({ steps, activeStep }: { steps: Array<{ id: string; label?: string; title?: string; detail?: string }>; activeStep?: string }) {
  return (
    <div className="space-y-3">
      {steps.map((step, index) => {
        const active = activeStep ? step.id === activeStep : index === 0;
        return (
          <div key={step.id} className={`rounded-2xl border px-4 py-3 ${active ? "border-emerald-400/[0.25] bg-emerald-400/[0.10]" : "border-white/[0.08] bg-white/[0.03]"}`}>
            <div className="flex items-center gap-3">
              <span className={`grid h-8 w-8 place-items-center rounded-full text-sm font-semibold ${active ? "bg-emerald-400 text-slate-950" : "bg-white/[0.10] text-white"}`}>{index + 1}</span>
              <div>
                <div className="font-medium text-white">{step.label || step.title || `Paso ${index + 1}`}</div>
                {step.detail ? <div className="text-sm text-slate-300">{step.detail}</div> : null}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function WhatsAppPreview({ title, scenario, userPrompt, blocks, footer, themeTone = "green", stageLabel, objective, proofLabel, highlights = [], quickReplies = [] }: { title: string; scenario: string; userPrompt: string; blocks: Array<Record<string, unknown> & { type?: string; label?: string; text?: string }>; footer: string; themeTone?: "green" | "blue" | "gold" | "red" | "slate"; stageLabel?: string; objective?: string; proofLabel?: string; highlights?: string[]; quickReplies?: string[]; }) {
  const bubbleTone = themeTone === "blue" ? "bg-sky-400/[0.16] border-sky-400/[0.25]" : themeTone === "gold" ? "bg-amber-400/[0.14] border-amber-400/[0.25]" : themeTone === "red" ? "bg-rose-400/[0.14] border-rose-400/[0.25]" : "bg-emerald-400/[0.14] border-emerald-400/[0.25]";
  return (
    <Section title={title} subtitle={scenario} icon="chat" aside={proofLabel ? <Badge tone={themeTone === "gold" ? "gold" : themeTone === "blue" ? "sky" : themeTone === "red" ? "red" : "green"}>{proofLabel}</Badge> : null}>
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-4">
          {objective ? <ModuleCard title="Objetivo de esta vista" description={objective} icon="target" tone="blue" /> : null}
          {highlights.length ? <TimelineList items={highlights.map((item, index) => ({ title: `Punto ${index + 1}`, detail: item, tone: index === 0 ? "green" : "slate" }))} /> : null}
          {quickReplies.length ? <ModuleCard title="Respuestas rápidas sugeridas" description="Botones claros para acelerar la conversación y ayudar a cerrar sin ruido." icon="spark" tone="gold" footer={quickReplies.map((reply) => <span key={reply} className="mono-pill">{reply}</span>)} /> : null}
        </div>
        <div className="rounded-[32px] border border-white/[0.10] bg-slate-950/70 p-4 shadow-[0_18px_60px_rgba(2,6,23,0.45)]">
          <div className="rounded-[28px] border border-white/[0.10] bg-[#0f172a] p-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <div className="text-sm font-semibold text-white">{stageLabel || "Vista previa"}</div>
                <div className="text-xs text-slate-400">Flujo de conversación</div>
              </div>
              <Badge tone="green">En vivo</Badge>
            </div>
            <div className="space-y-3 py-4">
              <div className="ml-auto max-w-[85%] rounded-3xl rounded-br-lg border border-white/[0.10] bg-white/[0.04] px-4 py-3 text-sm text-slate-100">{userPrompt}</div>
              {blocks.map((block, index) => {
                if (block.type === "image") return <div key={index} className={`max-w-[88%] rounded-3xl border ${bubbleTone} overflow-hidden`}><div className="h-40 bg-[linear-gradient(135deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02))]" /><div className="px-4 py-3 text-sm text-slate-100">{block.label || "Imagen"}</div></div>;
                if (block.type === "text") return <div key={index} className={`max-w-[88%] rounded-3xl rounded-bl-lg border px-4 py-3 text-sm text-slate-100 ${bubbleTone}`}>{block.text}</div>;
                return <div key={index} className="max-w-[88%] rounded-3xl border border-white/[0.10] bg-white/[0.03] px-4 py-3 text-sm text-slate-100">{Object.entries(block).filter(([k]) => k !== "type").slice(0, 5).map(([k, v]) => <div key={k} className="flex justify-between gap-3 py-1"><span className="text-slate-400">{k}</span><span>{typeof v === "object" ? JSON.stringify(v) : String(v)}</span></div>)}</div>;
              })}
            </div>
            <div className="border-t border-white/[0.08] pt-3 text-xs text-slate-400">{footer}</div>
          </div>
        </div>
      </div>
    </Section>
  );
}


export function SecondaryNav({ items }: { items: Array<{ href: string; label: string; active?: boolean }> }) {
  return (
    <div className="flex flex-wrap gap-2 rounded-3xl border border-white/[0.08] bg-white/[0.03] p-2">
      {items.map((item) => (
        <Link key={`${item.href}-${item.label}`} href={item.href} className={item.active ? "primary-btn" : "secondary-btn"}>
          {item.label}
        </Link>
      ))}
    </div>
  );
}

export function ContextTip({ title = "Ayuda breve", children }: { title?: string; children: ReactNode }) {
  return (
    <div className="rounded-3xl border border-sky-400/[0.20] bg-sky-400/[0.10] p-4 text-sm text-sky-50">
      <div className="font-semibold text-white">{title}</div>
      <div className="mt-2 leading-6 text-slate-100">{children}</div>
    </div>
  );
}

export function SuccessState({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) {
  return (
    <div className="rounded-3xl border border-emerald-400/[0.20] bg-emerald-400/[0.10] p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-emerald-400/[0.25] bg-emerald-400 text-slate-950">
          <Icon name="check" className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <div className="text-lg font-semibold text-white">{title}</div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-100">{description}</p>
          {actions ? <div className="mt-4 flex flex-wrap gap-2">{actions}</div> : null}
        </div>
      </div>
    </div>
  );
}

export function EmptyActionState({ title, description, primaryAction, secondaryAction }: { title: string; description: string; primaryAction?: ReactNode; secondaryAction?: ReactNode }) {
  return (
    <div className="rounded-3xl border border-dashed border-white/[0.15] bg-white/[0.03] p-6">
      <div className="max-w-2xl">
        <div className="text-xl font-semibold text-white">{title}</div>
        <p className="mt-2 text-sm leading-6 text-slate-300">{description}</p>
      </div>
      {(primaryAction || secondaryAction) ? <div className="mt-4 flex flex-wrap gap-2">{primaryAction}{secondaryAction}</div> : null}
    </div>
  );
}


export function PermissionGate({ allowed, fallback = null, children }: { allowed: boolean; fallback?: ReactNode; children: ReactNode }) {
  return allowed ? <>{children}</> : <>{fallback}</>;
}
