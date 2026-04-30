import { requireSession } from "@/app/lib/session";
import type { SessionOrganization } from "@/app/lib/contracts/auth";
import type { BotContract } from "@/app/lib/contracts/bots";
import type { VerticalProfileContract } from "@/app/lib/contracts/verticals";
import { getBot, getBots } from "@/app/lib/data/bots";
import { getStrongestVerticals, getVerticalCatalog } from "@/app/lib/data/verticals";
import { getWizardBlueprint, getWizardInstance, getWizardVerticalProfile } from "@/app/lib/data/wizard";
import type { CreateRouteStep, ReconfigureRouteStep, RouteStep } from "../domain/flowConfig";
import type { WizardBlueprint, WizardInstance, WizardMode } from "../domain/wizardTypes";

export type BotStudioLoadWarning = { source: string; message: string };

export type BotStudioFlowData = {
  organizations: SessionOrganization[];
  verticals: VerticalProfileContract[];
  strongestVerticals: VerticalProfileContract[];
  bots: BotContract[];
  initialSelectedBotId: string;
  initialMode: WizardMode;
  initialOrganizationId: string;
  initialVerticalId: string;
  initialSubvertical: string;
  initialPrimaryObjective: string;
  initialBlueprint: WizardBlueprint | null;
  initialVerticalProfile: VerticalProfileContract | null;
  initialWizardId?: string;
  initialWizard?: WizardInstance | null;
  initialStepOverride?: RouteStep | string;
  loadWarnings?: BotStudioLoadWarning[];
};

type Args = {
  mode?: string | null;
  botId?: string | null;
  wizardId?: string | null;
  organizationId?: string | null;
  verticalId?: string | null;
  subvertical?: string | null;
  primaryObjective?: string | null;
  step?: RouteStep | string | null;
};

type CatalogPickSource = {
  selected_subvertical?: { name?: string };
  recommended_subverticals?: string[];
  subvertical_profiles?: Array<{ name?: string }>;
  subverticals?: string[];
};

type RouteLoadPlan = {
  loadVerticalCatalog: boolean;
  loadStrongestVerticals: boolean;
  loadBotList: boolean;
  loadSelectedBot: boolean;
  loadBlueprintAndProfile: boolean;
};

const CREATE_CONTEXT_STEP: CreateRouteStep = "context";
const CREATE_PREFILL_STEPS = new Set<RouteStep>(["context", "offer", "knowledge", "integrations", "review", "validate", "apply", "success"]);
const RECONFIGURE_SELECT_STEP: ReconfigureRouteStep = "select";

function pickCatalogSubvertical(profile?: CatalogPickSource | null) {
  return profile?.selected_subvertical?.name || profile?.recommended_subverticals?.[0] || profile?.subvertical_profiles?.[0]?.name || profile?.subverticals?.[0] || "";
}

function byId<T extends { id: string }>(items: T[]) {
  return Object.fromEntries(items.map((item) => [item.id, item])) as Record<string, T>;
}

function cleanRouteParam(value?: string | null) {
  const raw = String(value || "").trim();
  const normalized = raw.toLowerCase();
  return raw && raw !== "-" && normalized !== "null" && normalized !== "undefined" && normalized !== "nan" ? raw : "";
}

function buildRouteLoadPlan(mode: WizardMode, step?: RouteStep | string | null): RouteLoadPlan {
  const routeStep = cleanRouteParam(step);
  const isCreate = mode === "create";
  const isContext = isCreate && routeStep === CREATE_CONTEXT_STEP;
  const isCreatePrefill = isCreate && CREATE_PREFILL_STEPS.has(routeStep as RouteStep);
  const isReconfigureSelect = mode === "reconfigure" && routeStep === RECONFIGURE_SELECT_STEP;
  const isReconfigureDetail = mode === "reconfigure" && !isReconfigureSelect;

  return {
    loadVerticalCatalog: isContext,
    loadStrongestVerticals: isContext,
    loadBotList: isReconfigureSelect,
    loadSelectedBot: isReconfigureDetail,
    loadBlueprintAndProfile: isCreatePrefill || isReconfigureDetail,
  };
}

function optionalErrorMessage(source: string, error: unknown) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  return `${source}: ${message}`;
}

async function safeOptional<T>(source: string, warnings: BotStudioLoadWarning[], loader: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await loader();
  } catch (error) {
    warnings.push({ source, message: optionalErrorMessage(source, error) });
    return fallback;
  }
}

async function getSelectedBotOrNull(botId: string, warnings: BotStudioLoadWarning[]) {
  if (!botId) return null;
  const bot = await safeOptional("selected_bot", warnings, () => getBot(botId), null);
  return bot?.id ? bot : null;
}

function pickRouteSelectedBot(botList: BotContract[], routeBotId: string) {
  return botList.find((item) => item.id === routeBotId) || null;
}

function pickWizardSelectedBot(botList: BotContract[], wizardBotId?: string | null) {
  return wizardBotId ? botList.find((item) => item.id === wizardBotId) || null : null;
}

function resolveCatalogVertical({
  verticals,
  wizardVerticalId,
  routeVerticalId,
  selectedBot,
  skipBotMatch,
}: {
  verticals: VerticalProfileContract[];
  wizardVerticalId: string;
  routeVerticalId: string;
  selectedBot: BotContract | null;
  skipBotMatch: boolean;
}) {
  return verticals.find((item) => item.id === wizardVerticalId)
    || verticals.find((item) => item.id === routeVerticalId)
    || (!skipBotMatch ? verticals.find((item) => item.name.toLowerCase() === String(selectedBot?.vertical || "").trim().toLowerCase()) : null)
    || null;
}

export async function loadBotStudioRoute(args: Args): Promise<BotStudioFlowData> {
  const routeMode = cleanRouteParam(args.mode);
  const routeBotId = cleanRouteParam(args.botId);
  const routeWizardId = cleanRouteParam(args.wizardId);
  const routeOrganizationId = cleanRouteParam(args.organizationId);
  const routeVerticalId = cleanRouteParam(args.verticalId);
  const routeSubvertical = cleanRouteParam(args.subvertical);
  const routePrimaryObjective = cleanRouteParam(args.primaryObjective);
  const routeStep = cleanRouteParam(args.step);
  const initialMode: WizardMode = routeMode === "reconfigure" ? "reconfigure" : "create";
  const loadPlan = buildRouteLoadPlan(initialMode, routeStep);
  const loadWarnings: BotStudioLoadWarning[] = [];

  const [session, initialWizard] = await Promise.all([
    requireSession(),
    routeWizardId ? safeOptional("wizard_instance", loadWarnings, () => getWizardInstance(routeWizardId), null) : Promise.resolve(null),
  ]);

  const selectedBotIdFromRouteOrWizard = initialMode === "reconfigure" ? routeBotId || cleanRouteParam(initialWizard?.bot_id) : "";
  const [verticals, strongestVerticals, botList, selectedBotFromDetailRoute] = await Promise.all([
    loadPlan.loadVerticalCatalog ? safeOptional("vertical_catalog", loadWarnings, () => getVerticalCatalog(), []) : Promise.resolve([]),
    loadPlan.loadStrongestVerticals ? safeOptional("strongest_verticals", loadWarnings, () => getStrongestVerticals(), []) : Promise.resolve([]),
    loadPlan.loadBotList ? safeOptional("bot_list", loadWarnings, () => getBots(), []) : Promise.resolve([]),
    loadPlan.loadSelectedBot ? getSelectedBotOrNull(selectedBotIdFromRouteOrWizard, loadWarnings) : Promise.resolve(null),
  ]);

  const organizations = session?.user.organizations || [];
  const organizationsById = byId(organizations);
  const routeSelectedBot = pickRouteSelectedBot(botList, routeBotId) || selectedBotFromDetailRoute;
  const initialSelectedBot = initialMode === "reconfigure"
    ? (routeSelectedBot || pickWizardSelectedBot(botList, initialWizard?.bot_id) || selectedBotFromDetailRoute)
    : null;
  const waitingForExplicitBotSelection = initialMode === "reconfigure" && !initialSelectedBot && !initialWizard?.bot_id;
  const explicitWizardOrganization = initialWizard?.organization_id ? organizationsById[initialWizard.organization_id] || null : null;
  const explicitRouteOrganization = routeOrganizationId ? organizationsById[routeOrganizationId] || null : null;
  const botOrganization = initialSelectedBot ? organizationsById[initialSelectedBot.organization_id] || null : null;
  const wizardOrganization = waitingForExplicitBotSelection ? null : explicitWizardOrganization || explicitRouteOrganization || botOrganization || null;
  const initialOrganizationId = initialMode === "create" ? (explicitWizardOrganization?.id || explicitRouteOrganization?.id || "") : (wizardOrganization?.id || "");
  const wizardFit = (initialWizard?.answers?.vertical_fit || {}) as Record<string, unknown>;
  const wizardVerticalId = cleanRouteParam(String(wizardFit.vertical_id || initialWizard?.vertical_id || ""));
  const catalogVertical = waitingForExplicitBotSelection
    ? null
    : resolveCatalogVertical({
      verticals,
      wizardVerticalId,
      routeVerticalId,
      selectedBot: initialSelectedBot,
      skipBotMatch: initialMode === "create",
    });
  const initialVerticalId = catalogVertical?.id || wizardVerticalId || routeVerticalId || "";
  const initialSubvertical = waitingForExplicitBotSelection ? "" : String(wizardFit.subvertical || routeSubvertical || initialWizard?.subvertical || pickCatalogSubvertical(catalogVertical));
  const initialPrimaryObjective = waitingForExplicitBotSelection ? "agendar" : String(wizardFit.primary_objective || routePrimaryObjective || initialWizard?.primary_objective || initialSelectedBot?.objective || "agendar");
  const initialSelectedBotId = initialMode === "reconfigure" ? initialSelectedBot?.id || cleanRouteParam(initialWizard?.bot_id) : "";
  const shouldLoadPreview = loadPlan.loadBlueprintAndProfile && initialOrganizationId && initialVerticalId;
  const [initialBlueprint, initialVerticalProfile] = shouldLoadPreview ? await Promise.all([
    safeOptional("wizard_blueprint", loadWarnings, () => getWizardBlueprint({ organizationId: initialOrganizationId, verticalId: initialVerticalId, subvertical: initialSubvertical, primaryObjective: initialPrimaryObjective, botId: initialSelectedBotId || undefined }), null),
    safeOptional("wizard_vertical_profile", loadWarnings, () => getWizardVerticalProfile({ organizationId: initialOrganizationId, verticalId: initialVerticalId, subvertical: initialSubvertical || undefined, botId: initialSelectedBotId || undefined, mode: initialMode }), null),
  ]) : [null, null];

  return {
    organizations,
    verticals,
    strongestVerticals,
    bots: initialSelectedBot && !botList.some((item) => item.id === initialSelectedBot.id) ? [initialSelectedBot] : botList,
    initialSelectedBotId,
    initialMode,
    initialOrganizationId,
    initialVerticalId,
    initialSubvertical,
    initialPrimaryObjective,
    initialBlueprint,
    initialVerticalProfile,
    initialWizardId: routeWizardId || undefined,
    initialWizard: initialWizard || null,
    initialStepOverride: routeStep || undefined,
    loadWarnings,
  };
}

export const loadBotStudioFlowData = loadBotStudioRoute;
