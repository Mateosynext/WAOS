import "server-only";
import type { ReactNode } from "react";
import { logoutAction } from "@/app/actions/auth";
import AppBreadcrumbs from "../AppBreadcrumbs";
import AppNavLink from "../AppNavLink";
import CommandPalette from "../CommandPalette";
import { UiMessage } from "../UiMessage";
import ThemeToggle from "../ThemeToggle";
import { EmptyActionState } from "../feedback";
import { clientNavigation, superAdminNavigation } from "../navigation/config";
import { Badge, Icon } from "../primitives/shared";
import { getBots } from "../../lib/data/bots";
import { getCurrentBotId, getSession } from "../../lib/session";
import { industryWithValue } from "../../lib/ui-glossary";
import { ClientShell, ModuleOwnershipStrip, PersistentContextHeader, QuickLinks, type AppMode } from "./shellContext";

function formatLabel(label: string) {
  return label.length > 26 ? `${label.slice(0, 26)}…` : label;
}

export async function Shell({
  title,
  subtitle,
  children,
  action,
  mode = "superadmin",
  requireBot = false,
  contextChangeHref = "/organizations?source=context-lock",
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  action?: ReactNode;
  mode?: AppMode;
  requireBot?: boolean;
  contextChangeHref?: string;
}) {
  const session = await getSession();
  const currentBotId = session?.organizationId ? await getCurrentBotId() : null;
  const availableBots = session?.organizationId ? await getBots() : [];
  const organization = session?.user.organizations?.find((item) => item.id === session?.organizationId) || null;

  if (mode === "client") {
    return <ClientShell title={title} subtitle={subtitle} action={action} organization={organization}>{children}</ClientShell>;
  }

  const selectedBot = currentBotId ? availableBots.find((item) => item.id === currentBotId) || null : null;
  const name = session?.user.full_name || session?.user.email || "Sin sesión";
  const organizations = session?.user.organizations || [];
  const hasMultipleOrganizations = Boolean(organizations.length > 1);
  const requiresOrganization = Boolean(hasMultipleOrganizations && !session?.organizationId);
  const requiresBot = Boolean(requireBot);
  const missingBot = requiresBot && !selectedBot;
  const isContextLocked = requiresOrganization || missingBot;
  const contextTitle = requiresOrganization && missingBot
    ? "Primero fija la organización y el asistente operativo"
    : requiresOrganization
      ? "Primero fija una organización"
      : missingBot
        ? "Primero fija un asistente operativo"
        : "Contexto listo";
  const contextDescription = requiresOrganization && missingBot
    ? "Esta vista ya no adivina contexto. Antes de seguir, elige explícitamente la organización y el asistente operativo para no operar sobre el cliente equivocado."
    : requiresOrganization
      ? "Tu cuenta ve varias organizaciones. Antes de seguir, selecciona una explícitamente para no mezclar inbox, asistentes operativos, integraciones ni releases."
      : availableBots.length
        ? "Esta pantalla depende de un asistente operativo explícito. Elige cuál vas a operar para evitar cambios sobre el contexto equivocado."
        : "Todavía no hay asistentes operativos visibles para esta organización. Crea uno o cambia de contexto antes de operar esta pantalla.";

  return (
    <main id="main-content" className="min-h-screen bg-[var(--client-shell-bg)] text-[color:var(--text-primary)]">
      <div className="mx-auto max-w-[1600px] px-4 pb-6 pt-[max(1rem,env(safe-area-inset-top))] sm:px-6 lg:px-8">
        <details className="panel overflow-hidden lg:hidden">
          <summary className="flex cursor-pointer items-center justify-between px-4 py-4 text-sm font-medium text-[color:var(--text-primary)]">
            <span>Menú WAOS</span>
            <span className="text-[color:var(--text-muted)]">Abrir</span>
          </summary>
          <div className="border-t border-[color:var(--border-soft)] px-4 py-4">
            <div className="mb-4 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm text-[color:var(--text-secondary)]">
              <div className="font-medium text-[color:var(--text-primary)]">{organization?.name || "Organización"}</div>
              <div className="mt-1 text-[color:var(--text-muted)]">{industryWithValue(organization?.vertical, "Operación omnicanal")}</div>
            </div>
            <nav className="space-y-4">
              {superAdminNavigation.map((group) => (
                <div key={group.group} className="space-y-2">
                  <div className="px-2 text-[11px] font-medium uppercase tracking-[0.22em] text-[color:var(--text-muted)]">{group.group}</div>
                  <div className="space-y-1.5">
                    {group.items.map((item) => (
                      <AppNavLink key={item.href} href={item.href} exact={"exact" in item ? Boolean(item.exact) : false} className="nav-link flex items-center gap-3" activeClassName="nav-link-active">
                        <span className="grid h-9 w-9 place-items-center rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-primary)]">
                          <Icon name={item.icon} className="h-4 w-4" />
                        </span>
                        <span>{item.label}</span>
                      </AppNavLink>
                    ))}
                  </div>
                </div>
              ))}
            </nav>
          </div>
        </details>

        <div className="grid min-h-[calc(100vh-2rem)] gap-6 lg:grid-cols-[292px_minmax(0,1fr)]">
          <aside className="panel sticky top-4 hidden h-[calc(100vh-2rem)] overflow-hidden lg:flex lg:flex-col">
            <div className="border-b border-[color:var(--border-soft)] px-5 py-5">
              <div className="flex items-center gap-3">
                <div className="grid h-12 w-12 place-items-center rounded-2xl border border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
                  <Icon name="bot" className="h-6 w-6" />
                </div>
                <div>
                  <div className="text-lg font-semibold text-[color:var(--text-primary)]">WAOS</div>
                  <div className="text-sm text-[color:var(--text-muted)]">Opera claro y sin ruido</div>
                </div>
              </div>
              <div className="mt-4 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm text-[color:var(--text-secondary)]">
                <div className="font-medium text-[color:var(--text-primary)]">{organization?.name || "Organización"}</div>
                <div className="mt-1 text-[color:var(--text-muted)]">{industryWithValue(organization?.vertical)}</div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4">
              <nav className="space-y-5">
                {superAdminNavigation.map((group) => (
                  <div key={group.group} className="space-y-2">
                    <div className="px-2 text-[11px] font-medium uppercase tracking-[0.22em] text-[color:var(--text-muted)]">{group.group}</div>
                    <div className="space-y-1.5">
                      {group.items.map((item) => (
                        <AppNavLink key={item.href} href={item.href} exact={"exact" in item ? Boolean(item.exact) : false} className="nav-link flex items-center gap-3" activeClassName="nav-link-active">
                          <span className="grid h-9 w-9 place-items-center rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-primary)]">
                            <Icon name={item.icon} className="h-4 w-4" />
                          </span>
                          <span>{item.label}</span>
                        </AppNavLink>
                      ))}
                    </div>
                  </div>
                ))}
              </nav>
            </div>

            <div className="border-t border-[color:var(--border-soft)] px-4 py-4">
              <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium text-[color:var(--text-primary)]">{formatLabel(name)}</div>
                    <div className="mt-1 text-xs text-[color:var(--text-muted)]">{session?.user.global_role || "super_admin"}</div>
                  </div>
                  <ThemeToggle />
                </div>
                <div className="mt-3 flex gap-2">
                  <CommandPalette />
                  <AppNavLink href="/client/resumen" className="secondary-btn flex-1">Portal cliente</AppNavLink>
                  <form action={logoutAction} className="flex-1">
                    <button type="submit" className="secondary-btn w-full">Salir</button>
                  </form>
                </div>
              </div>
            </div>
          </aside>

          <section className="min-w-0 pb-6">
            <header className="panel px-5 py-5 lg:px-6 lg:py-6">
              <div className="flex flex-col gap-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="green">{"Super admin"}</Badge>
                    {organization?.name ? <Badge tone="slate">{organization.name}</Badge> : null}
                    {organization?.vertical ? <Badge tone="gold">{industryWithValue(organization.vertical)}</Badge> : null}
                  </div>
                  <ThemeToggle />
                </div>

                <AppBreadcrumbs />

                <PersistentContextHeader
                  mode={mode}
                  organization={organization}
                  organizations={organizations}
                  selectedBot={selectedBot}
                  availableBots={availableBots}
                  contextChangeHref={contextChangeHref}
                  isContextLocked={isContextLocked}
                />
                <ModuleOwnershipStrip />

                <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
                  <div className="space-y-3">
                    <h1 className="text-3xl font-semibold tracking-[-0.05em] text-[color:var(--text-primary)] lg:text-4xl">{title}</h1>
                    <p className="max-w-4xl text-sm leading-7 text-[color:var(--text-secondary)] lg:text-[15px]">{subtitle}</p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <CommandPalette />
                    <QuickLinks mode={mode} />
                    {action}
                  </div>
                </div>
              </div>

              {!isContextLocked ? (
                <div className="mt-5 flex flex-wrap gap-2 text-xs text-[color:var(--text-secondary)]">
                  <span className="mono-pill">Usa Ctrl/⌘ K para saltar</span>
                  <span className="mono-pill">Organización, asistente operativo y estado visibles arriba</span>
                  <span className="mono-pill">Portal cliente separado del modo interno</span>
                </div>
              ) : null}
              {isContextLocked ? (
                <div className="mt-5">
                  <UiMessage title={contextTitle} tone="warning">
                    {contextDescription}
                  </UiMessage>
                </div>
              ) : null}
            </header>
            <div className="mt-6 space-y-6">
              {isContextLocked ? (
                <EmptyActionState
                  title={contextTitle}
                  description={contextDescription}
                  primaryAction={<AppNavLink href={contextChangeHref} className="primary-btn">Cambiar contexto</AppNavLink>}
                  secondaryAction={missingBot && !availableBots.length ? <AppNavLink href="/bot-studio" className="secondary-btn">Crear asistente con IA</AppNavLink> : <AppNavLink href="/client/resumen" className="secondary-btn">Abrir vista cliente</AppNavLink>}
                />
              ) : children}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
