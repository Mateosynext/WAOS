import type { ReactNode } from "react";
import { switchOrganizationAction } from "../../actions";
import AppBreadcrumbs from "../AppBreadcrumbs";
import AppNavLink from "../AppNavLink";
import BotScopeSwitcher from "../BotScopeSwitcher";
import OrganizationSwitcher from "../OrganizationSwitcher";
import ThemeToggle from "../ThemeToggle";
import { clientNavigation } from "../navigation/config";
import { Badge, toneClass } from "../primitives/shared";
import type { BotContract, SessionOrganization } from "../../lib/contracts";
import { industryWithValue, operationTypeWithValue, operationalAssistantWithValue, organizationWithValue } from "../../lib/ui-glossary";
export type AppMode = "superadmin" | "client";

export function QuickLinks({ mode }: { mode: AppMode }) {
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

export function ModuleOwnershipStrip() {
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

export function PersistentContextHeader({
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

export function ClientShell({ title, subtitle, children, action, organization }: { title: string; subtitle: string; children: ReactNode; action?: ReactNode; organization: SessionOrganization | null }) {
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

