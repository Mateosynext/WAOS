import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath: string) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

test("status support and launch-center are real pages instead of redirects", () => {
  const status = read("app/status/page.tsx");
  const support = read("app/support/page.tsx");
  const launchCenter = read("app/launch-center/page.tsx");

  assert.doesNotMatch(status, /redirect\(/);
  assert.doesNotMatch(support, /redirect\(/);
  assert.doesNotMatch(launchCenter, /redirect\(/);
  assert.match(status, /Estado interno/);
  assert.match(support, /Soporte operativo/);
  assert.match(launchCenter, /Launch center/);
});

test("api layer sends internal console context and only retries safe methods", () => {
  const api = read("app/lib/api.ts");
  assert.match(api, /x-waos-frontend/);
  assert.match(api, /x-waos-request-method/);
  assert.match(api, /x-waos-org-id/);
  assert.match(api, /x-waos-bot-id/);
  assert.match(api, /GET", "HEAD", "OPTIONS/);
});

test("session keeps org and bot scope consistent", () => {
  const session = read("app/lib/session.ts");
  assert.match(session, /keepScopeConsistent/);
  assert.match(session, /store\.delete\(BOT_COOKIE\)/);
});

test("critical chrome uses tokenized surfaces in refactored screens", () => {
  const login = read("app/login/page.tsx");
  const recovery = read("app/login/recovery/page.tsx");
  const errorBoundary = read("app/error.tsx");
  const notFound = read("app/not-found.tsx");
  const commandPalette = read("app/components/CommandPalette.tsx");

  assert.match(login, /var\(--client-shell-bg\)/);
  assert.match(recovery, /var\(--client-shell-bg\)/);
  assert.match(errorBoundary, /var\(--client-shell-bg\)/);
  assert.match(notFound, /var\(--client-shell-bg\)/);
  assert.match(commandPalette, /var\(--surface-subtle\)/);
});


test("wizard reactive loader is centralized in feature services", () => {
  const shared = read("features/bot-studio/services/wizardReactiveData.ts");
  const stateModel = read("features/bot-studio/flow/useBotStudioFlowStateModel.ts");
  const reactiveConfigurator = read("app/components/ReactiveVerticalConfigurator.tsx");

  assert.match(shared, /WIZARD_BLUEPRINT_ENDPOINT/);
  assert.match(shared, /WIZARD_VERTICAL_PROFILE_ENDPOINT/);
  assert.match(shared, /loadWizardReactiveSelection/);
  assert.match(stateModel, /createLatestWizardReactiveSelectionLoader/);
  assert.match(reactiveConfigurator, /loadWizardReactiveSelection/);

  for (const source of [stateModel, reactiveConfigurator]) {
    assert.doesNotMatch(source, new RegExp("/api/onboarding/wizard/blueprint\\?"));
    assert.doesNotMatch(source, new RegExp("/api/onboarding/wizard/vertical-profile\\?"));
  }
});

test("bot studio app routes stay thin and feature modules own implementation", () => {
  const entryPage = read("app/bot-studio/page.tsx");
  const routePage = read("app/bot-studio/[mode]/[[...slug]]/page.tsx");
  const featureRoute = read("features/bot-studio/BotStudioRoute.tsx");
  const featureCreateScreens = read("features/bot-studio/context/screens/CreateContextScreen.tsx");
  const featureReviewSections = read("features/bot-studio/review/ValidationSnapshotPanel.tsx");
  const featureSummaryRail = read("features/bot-studio/review/StickySummaryRail.tsx");
  const featureState = read("features/bot-studio/context/useBotStudioWizardState.ts");

  assert.match(entryPage, new RegExp("features/bot-studio/domain/flowConfig"));
  assert.match(routePage, new RegExp("features/bot-studio/server/loadBotStudioRoute"));
  assert.match(routePage, new RegExp("features/bot-studio/BotStudioRoute"));
  assert.match(featureCreateScreens, /export function CreateContextScreen/);
  assert.match(featureReviewSections, /export function ValidationSnapshotPanel/);
  assert.match(featureSummaryRail, /export function StickySummaryRail/);
  assert.match(featureState, /export function useBotStudioWizardState/);
  assert.match(featureRoute, /useBotStudioFlowController/);
  assert.match(featureRoute, /BotStudioFlowBody/);
  assert.doesNotMatch(featureRoute, new RegExp("app/bot-studio"));
});

test("global components barrel is removed and callers use focused component modules", () => {
  assert.equal(fs.existsSync(path.join(root, "app/components.tsx")), false);
  const shell = read("app/components/layout/shell.tsx");
  const shared = read("app/components/primitives/shared.tsx");
  const cards = read("app/components/primitives/cards.tsx");
  const navigation = read("app/components/navigation/index.tsx");
  const feedback = read("app/components/feedback/index.tsx");
  const domain = read("app/components/domain/WhatsAppPreview.tsx");
  const home = read("app/page.tsx");

  assert.match(home, /components\/layout\/shell/);
  assert.match(home, /components\/primitives\/cards/);
  assert.match(home, /components\/feedback/);
  assert.match(shell, /export async function Shell/);
  assert.match(shared, /export function Icon/);
  assert.match(cards, /export function Section/);
  assert.match(navigation, /export function PortalTabs/);
  assert.match(feedback, /export function SuccessState/);
  assert.match(domain, /export function WhatsAppPreview/);
});

test("waos compatibility barrel is removed and routes import data access directly", () => {
  assert.equal(fs.existsSync(path.join(root, "app/lib/waos.ts")), false);
  const home = read("app/page.tsx");
  const botsPage = read("app/bots/page.tsx");
  const bots = read("app/lib/data/bots.ts");
  const verticals = read("app/lib/data/verticals.ts");
  const inbox = read("app/lib/data/inbox.ts");
  const onboarding = read("app/lib/data/onboarding.ts");
  const clientPortal = read("app/lib/data/client-portal.ts");

  assert.match(home, /app\/lib\/data\/analytics/);
  assert.match(home, /app\/lib\/data\/bots/);
  assert.match(home, /app\/lib\/data\/verticals/);
  assert.match(botsPage, /app\/lib\/data\/bots/);
  assert.match(bots, /export async function getBots/);
  assert.match(verticals, /export async function getVerticalProfile/);
  assert.match(inbox, /export async function getConversations/);
  assert.match(onboarding, /export async function getActivationSummary/);
  assert.match(clientPortal, /export async function getClientPortalData/);
});


test("contracts compatibility barrel is removed and modules consume bounded contracts directly", () => {
  assert.equal(fs.existsSync(path.join(root, "app/lib/contracts.ts")), false);
  const shared = read("app/lib/contracts/shared.ts");
  const auth = read("app/lib/contracts/auth.ts");
  const bots = read("app/lib/contracts/bots.ts");
  const onboarding = read("app/lib/contracts/onboarding.ts");
  const inbox = read("app/lib/contracts/inbox.ts");
  const verticals = read("app/lib/contracts/verticals.ts");
  const analytics = read("app/lib/contracts/analytics.ts");
  const integrations = read("app/lib/contracts/integrations.ts");
  const commerce = read("app/lib/contracts/commerce.ts");
  const portal = read("app/lib/contracts/portal.ts");
  const talent = read("app/lib/contracts/talent.ts");

  assert.match(shared, /export function unwrapApiEnvelope/);
  assert.match(auth, /export function normalizeSessionUser/);
  assert.match(bots, /export function normalizeBot/);
  assert.match(onboarding, /export function normalizeActivationSummary/);
  assert.match(inbox, /export function normalizeConversationDetail/);
  assert.match(verticals, /export function normalizeVerticalProfile/);
  assert.match(analytics, /export function normalizeDashboard/);
  assert.match(integrations, /export function normalizeIntegrationCenter/);
  assert.match(commerce, /export function normalizeCommerceInsights/);
  assert.match(portal, /export function normalizePortalRequest/);
  assert.match(talent, /export function normalizeTalentOverview/);

  const botsData = read("app/lib/data/bots.ts");
  const onboardingData = read("app/lib/data/onboarding.ts");
  const inboxData = read("app/lib/data/inbox.ts");
  const analyticsData = read("app/lib/data/analytics.ts");
  const integrationsData = read("app/lib/data/integrations.ts");
  const commerceData = read("app/lib/data/commerce.ts");
  const session = read("app/lib/session.ts");

  assert.match(botsData, /from "\.\.\/contracts\/bots"/);
  assert.match(botsData, /from "\.\.\/contracts\/talent"/);
  assert.match(onboardingData, /from "\.\.\/contracts\/onboarding"/);
  assert.match(inboxData, /from "\.\.\/contracts\/inbox"/);
  assert.match(inboxData, /from "\.\.\/contracts\/portal"/);
  assert.match(analyticsData, /from "\.\.\/contracts\/analytics"/);
  assert.match(integrationsData, /from "\.\.\/contracts\/integrations"/);
  assert.match(integrationsData, /from "\.\.\/contracts\/auth"/);
  assert.match(commerceData, /from "\.\.\/contracts\/commerce"/);
  assert.match(session, /from "\.\/contracts\/auth"/);
});
test("client portal content consumes shared view models instead of embedding summary selectors inline", () => {
  const portalContent = read("app/client/ClientPortalContent.tsx");
  const portalViewModel = read("app/client/clientPortalViewModel.ts");
  assert.match(portalContent, /from "\.\/clientPortalViewModel"/);
  assert.match(portalViewModel, /export function buildClientPortalSummaryViewModel/);
  assert.match(portalViewModel, /export function buildClientPortalTimeline/);
  assert.match(portalViewModel, /export function buildAgendaViewModel/);
  assert.doesNotMatch(portalContent, /const sectionMeta:/);
  assert.doesNotMatch(portalContent, /function buildTimeline\(/);
  assert.doesNotMatch(portalContent, /function hasPendingRequests\(/);
});

test("reactive vertical configurator consumes a shared preview view model instead of local selector soup", () => {
  const configurator = read("app/components/ReactiveVerticalConfigurator.tsx");
  const viewModel = read("app/components/reactiveVerticalViewModel.ts");
  assert.match(configurator, /from "\.\/reactiveVerticalViewModel"/);
  assert.match(viewModel, /export function buildReactiveVerticalPreviewModel/);
  assert.match(viewModel, /export function buildSubverticalProfiles/);
  assert.match(viewModel, /export function pickRecommendedIntegrations/);
  assert.doesNotMatch(configurator, /function buildSubverticalProfiles\(/);
  assert.doesNotMatch(configurator, /function pickRecommendedIntegrations\(/);
  assert.doesNotMatch(configurator, /function pickTemplateLabels\(/);
});


test("client portal operations use typed data access instead of inline any-shaped fetch parsing", () => {
  const portalContent = read("app/client/ClientPortalContent.tsx");
  const operationsData = read("app/lib/data/client-operations.ts");
  const portalContracts = read("app/lib/contracts/portal.ts");

  assert.match(portalContent, /from "\.\.\/lib\/data\/client-operations"/);
  assert.match(operationsData, /export async function getClientOperationsData/);
  assert.match(portalContracts, /export function normalizeClientOperationsSummary/);
  assert.match(portalContracts, /export function normalizeClientOperationsAvailability/);
  assert.doesNotMatch(portalContent, /as any/);
  assert.equal(portalContent.includes("apiFetchOrDefault(`/api/v1/client/operations/"), false);
});

test("bot studio routes and flow client share wizard gateway modules instead of hand-rolled proxy duplication", () => {
  const page = read("app/bot-studio/page.tsx");
  const flowClient = read("features/bot-studio/BotStudioRoute.tsx");
  const wizardApi = read("features/bot-studio/services/wizardApi.ts");
  const wizardData = read("app/lib/data/wizard.ts");
  const routeHelpers = read("app/api/onboarding/wizard/route-helpers.ts");
  const startRoute = read("app/api/onboarding/wizard/start/route.ts");
  const blueprintRoute = read("app/api/onboarding/wizard/blueprint/route.ts");

  assert.match(page, /features\/bot-studio\/domain\/flowConfig/);
  assert.match(flowClient, /useBotStudioFlowController/);
  assert.match(wizardApi, /export function startWizardRequest/);
  assert.match(wizardData, /export async function getWizardBlueprint/);
  assert.match(routeHelpers, /export async function wizardRouteResponse/);
  assert.match(startRoute, /wizardRouteResponse/);
  assert.match(blueprintRoute, /getWizardBlueprint/);
  assert.doesNotMatch(flowClient, /"\/api\/onboarding\/wizard\/start"/);
  assert.doesNotMatch(flowClient, /steps\/\$\{stepKey\}/);
});

test("vertical fallback catalog is modularized behind indexed loaders instead of one giant TypeScript blob", () => {
  const verticalsData = read("app/lib/data/verticals.ts");
  const fallbackIndex = read("app/lib/vertical-fallback/index.ts");
  const fallbackCatalog = read("app/lib/vertical-fallback/index.json");
  const legacyBlob = path.join(root, "app/lib/vertical-fallback.ts");

  assert.match(verticalsData, /await getFallbackVerticalCatalog/);
  assert.match(verticalsData, /await getFallbackVerticalProfile/);
  assert.match(fallbackIndex, /import indexData from "\.\/index\.json"/);
  assert.match(fallbackIndex, /const profileLoaders:/);
  assert.match(fallbackIndex, /loadProfileById/);
  assert.match(fallbackIndex, /normalizeVerticalProfile/);
  assert.match(fallbackCatalog, /"file": "profiles\//);
  assert.equal(fs.existsSync(legacyBlob), false);
});
