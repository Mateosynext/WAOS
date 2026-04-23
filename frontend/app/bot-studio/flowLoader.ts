import { requireSession } from "../lib/session";
import { getBots, getStrongestVerticals, getVerticalCatalog } from "../lib/waos";
import { getWizardBlueprint, getWizardInstance, getWizardVerticalProfile } from "../lib/data/wizard";
import type { BotContract, SessionOrganization, VerticalProfileContract } from "../lib/contracts";
import type { RouteStep } from "./flowConfig";
import type { WizardBlueprint, WizardInstance, WizardMode } from "./wizard-types";

export type BotStudioFlowData = {
  organizations: SessionOrganization[]; verticals: VerticalProfileContract[]; strongestVerticals: VerticalProfileContract[]; bots: BotContract[];
  initialSelectedBotId: string; initialMode: WizardMode; initialOrganizationId: string; initialVerticalId: string; initialSubvertical: string; initialPrimaryObjective: string;
  initialBlueprint: WizardBlueprint | null; initialVerticalProfile: VerticalProfileContract | null; initialWizardId?: string; initialWizard?: WizardInstance | null; initialStepOverride?: RouteStep | string;
};

type Args = { mode?: string | null; botId?: string | null; wizardId?: string | null; organizationId?: string | null; verticalId?: string | null; subvertical?: string | null; primaryObjective?: string | null; step?: RouteStep | string | null };
function pickCatalogSubvertical(profile?: { selected_subvertical?: { name?: string }; recommended_subverticals?: string[]; subvertical_profiles?: Array<{ name?: string }>; subverticals?: string[] } | null) { return profile?.selected_subvertical?.name || profile?.recommended_subverticals?.[0] || profile?.subvertical_profiles?.[0]?.name || profile?.subverticals?.[0] || ""; }

export async function loadBotStudioFlowData(args: Args): Promise<BotStudioFlowData> {
  const routeMode = String(args.mode || "").trim();
  const routeBotId = String(args.botId || "").trim();
  const routeWizardId = String(args.wizardId || "").trim();
  const routeOrganizationId = String(args.organizationId || "").trim();
  const routeVerticalId = String(args.verticalId || "").trim();
  const routeSubvertical = String(args.subvertical || "").trim();
  const routePrimaryObjective = String(args.primaryObjective || "").trim();
  const session = await requireSession();
  const [verticals, strongestVerticals, bots, initialWizard] = await Promise.all([getVerticalCatalog(), getStrongestVerticals(), getBots(), routeWizardId ? getWizardInstance(routeWizardId) : Promise.resolve(null)]);
  const organizations = session?.user.organizations || [];
  const organizationsById = Object.fromEntries(organizations.map((item) => [item.id, item]));
  const routeSelectedBot = bots.find((item) => item.id === routeBotId) || null;
  const initialMode: WizardMode = routeMode === "reconfigure" || Boolean(routeBotId) || Boolean(initialWizard?.bot_id) ? "reconfigure" : "create";
  const initialSelectedBot = initialMode === "reconfigure" ? (routeSelectedBot || (initialWizard?.bot_id ? bots.find((item) => item.id === initialWizard.bot_id) || null : null)) : null;
  const waitingForExplicitBotSelection = initialMode === "reconfigure" && !initialSelectedBot && !initialWizard?.bot_id;
  const explicitWizardOrganization = initialWizard?.organization_id ? organizationsById[initialWizard.organization_id] || null : null;
  const explicitRouteOrganization = routeOrganizationId ? organizationsById[routeOrganizationId] || null : null;
  const botOrganization = initialSelectedBot ? organizationsById[initialSelectedBot.organization_id] || null : null;
  const wizardOrganization = waitingForExplicitBotSelection ? null : explicitWizardOrganization || explicitRouteOrganization || botOrganization || null;
  const initialOrganizationId = initialMode === "create" ? (explicitWizardOrganization?.id || explicitRouteOrganization?.id || "") : (wizardOrganization?.id || "");
  const wizardFit = (initialWizard?.answers?.vertical_fit || {}) as Record<string, unknown>;
  const catalogVertical = waitingForExplicitBotSelection ? null : verticals.find((item) => item.id === String(wizardFit.vertical_id || "")) || verticals.find((item) => item.id === routeVerticalId) || verticals.find((item) => item.name.toLowerCase() === String(initialSelectedBot?.vertical || "").trim().toLowerCase()) || null;
  const initialVerticalId = catalogVertical?.id || "";
  const initialSubvertical = waitingForExplicitBotSelection ? "" : String(wizardFit.subvertical || routeSubvertical || initialWizard?.subvertical || pickCatalogSubvertical(catalogVertical));
  const initialPrimaryObjective = waitingForExplicitBotSelection ? "agendar" : String(wizardFit.primary_objective || routePrimaryObjective || initialWizard?.primary_objective || initialSelectedBot?.objective || "agendar");
  const initialSelectedBotId = initialMode === "reconfigure" ? initialSelectedBot?.id || String(initialWizard?.bot_id || "") : "";
  const [initialBlueprint, initialVerticalProfile] = initialOrganizationId && initialVerticalId ? await Promise.all([
    getWizardBlueprint({ organizationId: initialOrganizationId, verticalId: initialVerticalId, subvertical: initialSubvertical, primaryObjective: initialPrimaryObjective, botId: initialSelectedBotId || undefined }),
    getWizardVerticalProfile({ organizationId: initialOrganizationId, verticalId: initialVerticalId, subvertical: initialSubvertical || undefined, botId: initialSelectedBotId || undefined, mode: initialMode }),
  ]) : [null, null];
  return { organizations, verticals, strongestVerticals, bots, initialSelectedBotId, initialMode, initialOrganizationId, initialVerticalId, initialSubvertical, initialPrimaryObjective, initialBlueprint, initialVerticalProfile, initialWizardId: routeWizardId || undefined, initialWizard: initialWizard || null, initialStepOverride: args.step || undefined };
}
