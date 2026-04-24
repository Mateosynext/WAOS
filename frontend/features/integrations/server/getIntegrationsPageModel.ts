import { getBots } from "@/app/lib/data/bots";
import { getPayments } from "@/app/lib/data/commerce";
import { getGoogleCalendars, getIntegrationCenter, getIntegrationEvents, getIntegrationObservability, getIntegrations, getIntegrationSyncRuns } from "@/app/lib/data/integrations";
import { getVerticalProfile } from "@/app/lib/data/verticals";
import { canManageSecrets, canOperateIntegrations, roleLabel } from "@/app/lib/permissions";
import { getCurrentBotId, getSession } from "@/app/lib/session";
import type { IntegrationContract, IntegrationEventContract, IntegrationObservabilityContract, SyncRunContract } from "@/app/lib/contracts/integrations";
import type { VerticalProfileContract } from "@/app/lib/contracts/verticals";

export type IntegrationsSearchParams = Record<string, string | string[] | undefined>;
export type IntegrationSection = "estado" | "configuracion" | "riesgo" | "sync" | "credenciales" | "observabilidad";

type BotList = Awaited<ReturnType<typeof getBots>>;
type PaymentList = Awaited<ReturnType<typeof getPayments>>;
type IntegrationCenter = Awaited<ReturnType<typeof getIntegrationCenter>>;
type GoogleCalendars = Awaited<ReturnType<typeof getGoogleCalendars>>;

export type IntegrationsPageModel = {
  section: IntegrationSection;
  oauthStatus?: string;
  focusIntegrationId: string;
  role?: string;
  roleLabel: string;
  permissions: {
    canOperateIntegrations: boolean;
    canManageSecrets: boolean;
  };
  organizationId: string | null;
  currentBotId: string | null;
  bots: BotList;
  selectedBot: BotList[number] | null;
  selectedVertical: VerticalProfileContract | null;
  integrations: IntegrationContract[];
  whatsappIntegration: IntegrationContract | null;
  googleIntegration: IntegrationContract | null;
  stripeIntegration: IntegrationContract | null;
  googleCalendars: GoogleCalendars;
  syncRuns: SyncRunContract[];
  observability: IntegrationObservabilityContract;
  events: IntegrationEventContract[];
  payments: PaymentList;
  center: IntegrationCenter;
  stats: {
    active: number;
    risk: IntegrationContract[];
    expiring: IntegrationContract[];
    observedEvents: number;
    pendingPayments: PaymentList;
    failedReceipts: Array<Record<string, unknown>>;
    retryHotspots: Array<Record<string, unknown>>;
  };
};

export function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export function normalizeIntegrationSection(value: string | undefined): IntegrationSection {
  switch (String(value || "estado").toLowerCase()) {
    case "configuration":
    case "configuracion":
      return "configuracion";
    case "risk":
    case "riesgo":
      return "riesgo";
    case "payments":
    case "sync":
      return "sync";
    case "credentials":
    case "credenciales":
      return "credenciales";
    case "events":
    case "observability":
    case "observabilidad":
      return "observabilidad";
    case "status":
    case "estado":
    default:
      return "estado";
  }
}

const emptyObservability: IntegrationObservabilityContract = {
  totals: { ok: 0, warning: 0, failed: 0 },
  latest_error: null,
  providers: [],
  recent: [],
};

const emptyCenter = { failed_receipts: [], retry_hotspots: [], dependency_map: [] } as IntegrationCenter;

export async function getIntegrationsPageModel(searchParams?: IntegrationsSearchParams): Promise<IntegrationsPageModel> {
  const params = searchParams || {};
  const section = normalizeIntegrationSection(first(params.section));
  const oauthStatus = first(params.google_oauth);
  const focusIntegrationId = first(params.integration_id) || "";
  const session = await getSession();
  const role = session?.user.global_role;
  const organizationId = session?.organizationId || null;
  const integrations = await getIntegrations();

  const whatsappIntegration = integrations.find((item) => item.provider === "meta_cloud_api" || item.integration_type === "whatsapp") || null;
  const googleIntegration = integrations.find((item) => item.provider === "google_calendar") || null;
  const stripeIntegration = integrations.find((item) => item.provider === "stripe") || null;

  let currentBotId: string | null = null;
  let bots: BotList = [];
  let selectedBot: BotList[number] | null = null;
  let selectedVertical: VerticalProfileContract | null = null;
  let googleCalendars: GoogleCalendars = [];
  let syncRuns: SyncRunContract[] = [];
  let observability: IntegrationObservabilityContract = emptyObservability;
  let events: IntegrationEventContract[] = [];
  let payments: PaymentList = [];
  let center: IntegrationCenter = emptyCenter;

  const selectedOrganization = session?.user.organizations.find((item) => item.id === organizationId) || null;

  if (section === "configuracion") {
    [currentBotId, bots] = await Promise.all([getCurrentBotId(), getBots()]);
    selectedBot = bots.find((item) => item.id === currentBotId) || null;
    const selectedVerticalId = selectedBot?.vertical || selectedOrganization?.vertical || undefined;
    selectedVertical = selectedVerticalId ? await getVerticalProfile(selectedVerticalId, selectedBot?.id) : null;
    googleCalendars = googleIntegration && ["connected", "configured"].includes(String(googleIntegration.credential_status || "").toLowerCase()) ? await getGoogleCalendars(googleIntegration.id) : [];
  } else if (section === "sync") {
    [syncRuns, payments] = await Promise.all([getIntegrationSyncRuns(), getPayments()]);
  } else if (section === "riesgo") {
    center = await getIntegrationCenter();
  } else if (section === "observabilidad") {
    [observability, events, center] = await Promise.all([getIntegrationObservability(), getIntegrationEvents(), getIntegrationCenter()]);
  }

  const active = integrations.filter((item) => ["active", "connected", "configured"].includes(String(item.status || "").toLowerCase())).length;
  const risk = integrations.filter((item) => !["healthy", "connected", "ok"].includes(String(item.health_status || item.status || "").toLowerCase()));
  const expiring = integrations.filter((item) => item.expires_at || item.credential_expires_at);
  const observedEvents = Number(observability.totals?.ok || 0) + Number(observability.totals?.warning || 0) + Number(observability.totals?.failed || 0);
  const pendingPayments = payments.filter((item) => ["pending", "pending_provider"].includes(String(item.status || "").toLowerCase()));
  const failedReceipts = (center.failed_receipts || []) as Array<Record<string, unknown>>;
  const retryHotspots = (center.retry_hotspots || []) as Array<Record<string, unknown>>;

  return {
    section,
    oauthStatus,
    focusIntegrationId,
    role,
    roleLabel: roleLabel(role),
    permissions: {
      canOperateIntegrations: canOperateIntegrations(role),
      canManageSecrets: canManageSecrets(role),
    },
    organizationId,
    currentBotId,
    bots,
    selectedBot,
    selectedVertical,
    integrations,
    whatsappIntegration,
    googleIntegration,
    stripeIntegration,
    googleCalendars,
    syncRuns,
    observability,
    events,
    payments,
    center,
    stats: { active, risk, expiring, observedEvents, pendingPayments, failedReceipts, retryHotspots },
  };
}
