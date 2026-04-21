import "server-only";
import type { ReactNode } from "react";
import { logoutAction, switchOrganizationAction } from "../../actions";
import AppBreadcrumbs from "../AppBreadcrumbs";
import AppNavLink from "../AppNavLink";
import BotScopeSwitcher from "../BotScopeSwitcher";
import OrganizationSwitcher from "../OrganizationSwitcher";
import CommandPalette from "../CommandPalette";
import { UiMessage } from "../UiMessage";
import ThemeToggle from "../ThemeToggle";
import { EmptyActionState } from "../feedback";
import { clientNavigation, superAdminNavigation } from "../navigation/config";
import { Badge, Icon, toneClass } from "../primitives/shared";
import { getBots } from "../../lib/data/bots";
import { getCurrentBotId, getSession } from "../../lib/session";
import type { BotContract, SessionOrganization } from "../../lib/contracts";
import { UI_GLOSSARY, industryWithValue, operationTypeWithValue, operationalAssistantWithValue, organizationWithValue } from "../../lib/ui-glossary";

export type AppMode = "superadmin" | "client";

function formatLabel(label: string) {
  return label.length > 26 ? `${label.slice(0, 26)}…` : label;
}

function QuickLinks({ mode }: { mode: AppMode }) {
  if (mode === "client") {
    return (
      <>
        <AppNavLink href="/client/resumen" className="primary-btn" exact>Inicio cliente</AppNavLink>
        <AppNavLink href="/client/solicitudes" className="secondary-btn">Solicitudes</AppNavLink>
      </>
    );
  }
  return (
    <>
      <AppNavLink href="/" className="primary-btn" exact>Inicio</AppNavLink>
      <AppNavLink href="/onboarding" className="secondary-btn">Onboarding</AppNavLink>
      <AppNavLink href="/bot-studio" className="secondary-btn">Bot Studio</AppNavLink>
      <AppNavLink href="/inbox" className="secondary-btn">Inbox</AppNavLink>
      <AppNavLink href="/client/resumen" className="secondary-btn">Portal cliente</AppNavLink>
    </>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function firstText(...values: unknown[]) {
  for (const value of values) {
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (trimmed) return trimmed;
      continue;
    }
    if (typeof value === "number" || typeof value === "boolean") {
      return String(value);
    }
  }
  return "";
}

function botDraftValue(bot: BotContract | null | undefined, keys: string[]) {
  const draft = asRecord(bot?.config_draft);
  const confirmedSelection = asRecord(draft.confirmed_selection);
  const candidateSelection = asRecord(draft.candidate_selection);
  return firstText(
    ...keys.map((key) => confirmedSelection[key]),
    ...keys.map((key) => draft[key]),
    ...keys.map((key) => candidateSelection[key]),
  );
}

function resolveIndustry(bot: BotContract | null, organization: SessionOrganization | null) {
  return firstText(bot?.vertical, organization?.vertical);
}

function resolveOperationType(bot: BotContract | null, organization: SessionOrganization | null) {
  return firstText(
    botDraftValue(bot, ["subvertical", "selected_subvertical", "operation_type", "selected_operation_type"]),
    organization?.subvertical,
  );
}

function resolveLifecycleState(bot: BotContract | null): "draft" | "applied" | "published" | null {
  if (!bot) return null;
  const draft = asRecord(bot.config_draft);
  const raw = [
    firstText((bot as BotContract & { current_state?: string | null }).current_state),
    firstText((bot as BotContract & { published_version_id?: string | null }).published_version_id),
    firstText(bot.status),
    firstText(draft.current_state),
    firstText(draft.release_state),
    firstText(draft.status),
  ].join(" ").toLowerCase();
  const versionStates = Array.isArray(bot.versions)
    ? bot.versions.map((item) => firstText(item?.status).toLowerCase()).filter(Boolean)
    : [];

  if (versionStates.includes("published") || raw.includes("publish") || Boolean(bot.last_release_at)) return "published";
  if (raw.includes("applied") || raw.includes("approved") || raw.includes("ready") || Boolean(firstText(draft.applied_at))) return "applied";
  return "draft";
}

function lifecycleTone(state: "draft" | "applied" | "published" | null): "gold" | "sky" | "green" {
  if (state === "published") return "green";
  if (state === "applied") return "sky";
  return "gold";
}

function ContextSnapshotCard({ label, value, detail, tone = "slate" }: { label: string; value: string; detail: string; tone?: "slate" | "green" | "gold" | "sky" }) {
  return (
    <div className={`rounded-2xl border px-4 py-3 ${toneClass(tone)}`}>
      <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-[color:var(--text-muted)]">{label}</div>
      <div className="mt-2 text-sm font-semibold text-[color:var(--text-primary)]">{value}</div>
      <div className="mt-1 text-xs leading-5 text-[color:var(--text-secondary)]">{detail}</div>
    </div>
  );
}

const superAdminModuleOwnership = [
  { label: "Onboarding", href: "/onboarding", role: "Readiness + checklist + estado" },
  { label: "Bot Studio", href: "/bot-studio", role: "Crear o reconfigurar" },
  { label: "Integraciones", href: "/integrations", role: "Conectar y probar" },
  { label: "Releases", href: "/releases", role: "Publicar" },
  { label: "Inbox", href: "/inbox", role: "Operar" },
] as const;

function ModuleOwnershipStrip() {
  return (
    <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Arquitectura del journey</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Cada módulo ya tiene un rol único para que readiness, setup, conexión, publicación y operación no compitan entre sí.</p>
        </div>
        <span className="mono-pill">CTAs cruzados sin competir</span>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {superAdminModuleOwnership.map((item) => (
          <AppNavLink key={item.href} href={item.href} className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-4 py-3 text-left transition hover:border-[color:var(--accent-border)] hover:bg-[color:var(--accent-soft)]">
            <div className="text-sm font-semibold text-[color:var(--text-primary)]">{item.label}</div>
            <div className="mt-1 text-xs leading-5 text-[color:var(--text-secondary)]">{item.role}</div>
          </AppNavLink>
        ))}
      </div>
    </div>
  );
}

function PersistentContextHeader({
  mode,
  organization,
  organizations,
  selectedBot,
  availableBots,
  contextChangeHref,
  isContextLocked,
}: {
  mode: AppMode;
  organization: SessionOrganization | null;
  organizations: SessionOrganization[];
  selectedBot: BotContract | null;
  availableBots: BotContract[];
  contextChangeHref: string;
  isContextLocked: boolean;
}) {
  const industry = resolveIndustry(selectedBot, organization);
  const operationType = resolveOperationType(selectedBot, organization);
  const lifecycle = resolveLifecycleState(selectedBot);
  const showOrganizationSwitcher = organizations.length > 1;
  const compactRedirect = contextChangeHref;

  return (
    <div className="sticky top-4 z-20">
      <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)]/95 p-4 shadow-[var(--shadow-soft)] backdrop-blur">
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={isContextLocked ? "gold" : "green"}>{isContextLocked ? "Contexto pendiente" : "Contexto visible"}</Badge>
            <Badge tone={organization ? "green" : "gold"}>{organizationWithValue(organization?.name)}</Badge>
            <Badge tone={selectedBot ? "sky" : "gold"}>{operationalAssistantWithValue(selectedBot?.name)}</Badge>
            <Badge tone={lifecycleTone(lifecycle)}>Estado · {lifecycle || "draft"}</Badge>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <ContextSnapshotCard
              label="Organización actual"
              value={organization?.name || "Organización pendiente"}
              detail={organization ? "Esta organización gobierna inbox, integraciones y releases visibles." : "Selecciona una organización explícita para fijar el módulo activo."}
              tone={organization ? "green" : "gold"}
            />
            <ContextSnapshotCard
              label="Asistente operativo actual"
              value={selectedBot?.name || "Asistente operativo pendiente"}
              detail={selectedBot ? "El cambio aplica sobre este asistente operativo y no sobre el primero disponible." : "Selecciona un asistente operativo antes de operar pantallas sensibles."}
              tone={selectedBot ? "sky" : "gold"}
            />
            <ContextSnapshotCard
              label="Industria / tipo de operación"
              value={industry ? `${industry}${operationType ? ` · ${operationType}` : ""}` : operationType || "Sin clasificación confirmada"}
              detail={`${industryWithValue(industry, "Industria pendiente")} · ${operationTypeWithValue(operationType, "Tipo de operación pendiente")}`}
              tone={industry || operationType ? "slate" : "gold"}
            />
            <ContextSnapshotCard
              label="Estado del contexto"
              value={lifecycle || "draft"}
              detail={lifecycle === "published" ? "Hay una salida publicada visible para este asistente operativo." : lifecycle === "applied" ? "El cambio ya fue aplicado, pero todavía no está publicado." : "Todavía estás operando sobre draft hasta publicar."}
              tone={lifecycle === "published" ? "green" : lifecycle === "applied" ? "sky" : "gold"}
            />
          </div>

          <div className="flex flex-col gap-2 xl:flex-row xl:flex-wrap xl:items-center xl:justify-between">
            <div className="flex flex-1 flex-col gap-2 xl:flex-row xl:flex-wrap">
              {showOrganizationSwitcher ? (
                <OrganizationSwitcher
                  organizations={organizations.map((item) => ({ id: item.id, name: item.name, vertical: item.vertical, botCount: undefined, channelCount: undefined, pendingCount: undefined }))}
                  selectedId={organization?.id || null}
                  redirectTo={compactRedirect}
                  action={switchOrganizationAction}
                  compact
                />
              ) : null}
              {availableBots.length ? <BotScopeSwitcher bots={availableBots} selectedBotId={selectedBot?.id || null} redirectTo={compactRedirect} compact /> : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <AppNavLink href={contextChangeHref} className="secondary-btn">Cambiar contexto</AppNavLink>
              {mode === "superadmin" ? <AppNavLink href="/client/resumen" className="secondary-btn">Ver portal cliente</AppNavLink> : <AppNavLink href="/" className="secondary-btn">Volver a operación interna</AppNavLink>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ClientShell({ title, subtitle, children, action, organization }: { title: string; subtitle: string; children: ReactNode; action?: ReactNode; organization: SessionOrganization | null }) {
  return (
    <main id="main-content" className="min-h-screen bg-[var(--client-shell-bg)] text-[color:var(--text-primary)]">
      <div className="mx-auto max-w-[1440px] px-4 pb-8 pt-[max(1rem,env(safe-area-inset-top))] sm:px-6 lg:px-8">
        <div className="rounded-[34px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] shadow-[var(--shadow-xl)] backdrop-blur">
          <header className="border-b border-[color:var(--border-soft)] px-4 py-5 sm:px-6 sm:py-6 lg:px-8">
            <div className="flex flex-col gap-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="sky">Portal cliente</Badge>
                    {organization?.name ? <Badge tone="slate">{organization.name}</Badge> : null}
                    {organization?.vertical ? <Badge tone="gold">{industryWithValue(organization.vertical)}</Badge> : null}
                  </div>
                  <AppBreadcrumbs />
                  <div>
                    <h1 className="text-3xl font-semibold tracking-[-0.05em] text-[color:var(--text-primary)] sm:text-[2.5rem]">{title}</h1>
                    <p className="mt-3 max-w-4xl text-sm leading-7 text-[color:var(--text-secondary)] sm:text-[15px]">{subtitle}</p>
                  </div>
                </div>
                <div className="flex w-full flex-col gap-3 sm:w-auto sm:items-end">
                  <ThemeToggle />
                  <div className="flex w-full flex-wrap gap-3 sm:w-auto sm:justify-end">
                    <QuickLinks mode="client" />
                    {action}
                  </div>
                </div>
              </div>

              <PersistentContextHeader
                mode="client"
                organization={organization}
                organizations={organization ? [organization] : []}
                selectedBot={null}
                availableBots={[]}
                contextChangeHref={`/organizations?source=${encodeURIComponent(clientNavigation[0]?.href || "/client/resumen")}`}
                isContextLocked={false}
              />
            </div>
          </header>
          <div className="px-4 py-6 sm:px-6 sm:py-8 lg:px-8">{children}</div>
        </div>
      </div>
    </main>
  );
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
                  secondaryAction={missingBot && !availableBots.length ? <AppNavLink href="/bot-studio" className="secondary-btn">Crear asistente operativo</AppNavLink> : <AppNavLink href="/client/resumen" className="secondary-btn">Abrir vista cliente</AppNavLink>}
                />
              ) : children}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
