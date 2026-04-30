import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const frontendRoot = process.cwd();

function read(relativePath: string) {
  return fs.readFileSync(path.join(frontendRoot, relativePath), "utf8");
}

test("legacy global barrels and Bot Studio shims stay deleted", () => {
  for (const legacyPath of [
    "app/actions.ts",
    "app/components.tsx",
    "app/lib/waos.ts",
    "app/lib/contracts.ts",
    "app/bot-studio/BotStudioFlowClient.tsx",
    "app/bot-studio/BotStudioWizardClient.tsx",
    "app/bot-studio/BotStudioFlow.tsx",
    "app/bot-studio/useBotStudioWizardState.ts",
    "app/bot-studio/createScreens.tsx",
    "app/bot-studio/wizardReviewSections.tsx",
    "features/bot-studio/services/wizardClient.ts",
    "features/bot-studio/ui/WizardErrorPanel.tsx",
  ]) {
    assert.equal(fs.existsSync(path.join(frontendRoot, legacyPath)), false, legacyPath);
  }
});

test("eslint blocks legacy Bot Studio shims and global barrels", () => {
  const eslint = read(".eslintrc.json");
  const config = JSON.parse(eslint);
  const rule = config.rules["no-restricted-imports"];
  assert.equal(rule[0], "error");
  const patterns = rule[1].patterns;
  for (const forbidden of [
    "@/app/lib/waos",
    "@/app/lib/contracts",
    "@/app/components",
    "@/app/actions",
    "@/app/bot-studio/*",
    "../components",
    "../actions",
    "../lib/waos",
    "../lib/contracts",
  ]) {
    assert.equal(patterns.includes(forbidden), true, forbidden);
  }
});

test("wizard route response preserves transport metadata", () => {
  const helper = read("app/api/onboarding/wizard/route-helpers.ts");
  assert.match(helper, /X-Request-Id/);
  assert.match(helper, /X-Correlation-Id/);
  assert.match(helper, /X-Error-Code/);
  assert.match(helper, /error_type/);
  assert.match(helper, /request_id/);
  assert.match(helper, /correlation_id/);
  assert.match(helper, /status,/);
});

test("Bot Studio route loader keeps create mode explicit", () => {
  const loader = read("features/bot-studio/server/loadBotStudioRoute.ts");
  assert.match(loader, /function cleanRouteParam\(value\?: string \| null\)/);
  assert.match(loader, /const routeBotId = cleanRouteParam\(args\.botId\);/);
  assert.match(loader, /const initialMode: WizardMode = routeMode === "reconfigure" \? "reconfigure" : "create";/);
  assert.doesNotMatch(loader, /Boolean\(routeBotId\)/);
  assert.doesNotMatch(loader, /Boolean\(initialWizard\?\.bot_id\)/);
});

test("Bot Studio route loader keeps RSC work scoped to the active step", () => {
  const loader = read("features/bot-studio/server/loadBotStudioRoute.ts");
  const page = read("app/bot-studio/[mode]/[[...slug]]/page.tsx");
  assert.match(loader, /type RouteLoadPlan/);
  assert.match(loader, /function buildRouteLoadPlan\(mode: WizardMode, step\?: RouteStep \| string \| null\)/);
  assert.match(loader, /loadBotList: isReconfigureSelect/);
  assert.match(loader, /loadSelectedBot: isReconfigureDetail/);
  assert.match(loader, /loadBlueprintAndProfile: isCreatePrefill \|\| isReconfigureDetail/);
    assert.match(loader, /loadPlan\.loadBotList \? safeOptional\("bot_list", loadWarnings, \(\) => getBots\(\), \[\]\) : Promise\.resolve\(\[\]\)/);
  assert.match(loader, /loadPlan\.loadSelectedBot \? getSelectedBotOrNull\(selectedBotIdFromRouteOrWizard, loadWarnings\) : Promise\.resolve\(null\)/);
    assert.match(loader, /async function safeOptional<T>\(source: string, warnings: BotStudioLoadWarning\[\], loader: \(\) => Promise<T>, fallback: T\): Promise<T>/);
  assert.match(loader, /safeOptional\("wizard_blueprint", loadWarnings, \(\) => getWizardBlueprint/);
  assert.match(page, /mode === "create" && normalizedStep === "context" && !model\.verticals\.length/);
  assert.doesNotMatch(loader, /Promise\.all\(\[\s*getVerticalCatalog\(\),\s*getStrongestVerticals\(\),\s*getBots\(\),\s*routeWizardId/);
});


test("Bot Studio flow reuses server-hydrated preview on first matching selection", () => {
  const flow = read("features/bot-studio/flow/useBotStudioFlowStateModel.ts");
  const previewSeed = read("features/bot-studio/flow/wizardPreviewSeed.ts");
  assert.ok(previewSeed.includes("function buildReactiveSelectionKey(input: ReactiveSelectionKeyInput)"));
  assert.ok(flow.includes("const didHydrateInitialPreview = useRef(false);"));
  assert.ok(flow.includes("const initialPreviewSelectionKey = useMemo(() => buildReactiveSelectionKey({"));
  assert.ok(flow.includes("const currentPreviewSelectionKey = buildReactiveSelectionKey(selectionRequest);"));
  assert.ok(flow.includes("const hasInitialPreview = Boolean(props.initialBlueprint || props.initialVerticalProfile);"));
  assert.ok(flow.includes("const hasLocalPreviewForSameSelection = Boolean(preview.blueprint || preview.verticalProfile) && lastLoadedPreviewKey.current === currentPreviewSelectionKey;"));
  assert.ok(flow.includes("!didHydrateInitialPreview.current && hasInitialPreview && currentPreviewSelectionKey === initialPreviewSelectionKey"));

  const skipIndex = flow.indexOf("currentPreviewSelectionKey === initialPreviewSelectionKey");
  const fetchIndex = flow.indexOf("loader.current.load(selectionRequest)");
  assert.ok(skipIndex > -1, "missing hydration skip guard");
  assert.ok(fetchIndex > -1, "missing reactive fetch call");
  assert.ok(skipIndex < fetchIndex, "hydration skip must run before the client preview fetch");
});

test("Bot Studio initial FAQ text renders in the same pipe format parsed by guards and payloads", () => {
  const state = read("features/bot-studio/context/useBotStudioWizardState.ts");
  assert.ok(state.includes("return q && a ? `${q} | ${a}` : \"\";"));
  assert.ok(state.includes(".join(\"\\n\");"));
  assert.doesNotMatch(state, /Q: \${q}\\nA: \${a}/);
});

test("Bot Studio canonical href strips placeholder query values", () => {
  const flowConfig = read("features/bot-studio/domain/flowConfig.ts");
  assert.match(flowConfig, /export function cleanRouteSearchValue\(value: unknown\)/);
  assert.match(flowConfig, /normalized !== "null" && normalized !== "undefined" && normalized !== "nan"/);
  assert.match(flowConfig, /const rendered = cleanRouteSearchValue\(value\);/);
});

test("Bot Studio AI-first entry hides manual create and preserves sanitized run resume", () => {
  const rootPage = read("app/bot-studio/page.tsx");
  const dynamicPage = read("app/bot-studio/[mode]/[[...slug]]/page.tsx");

  assert.match(rootPage, /WAOS AI Command Center/);
  assert.match(rootPage, /const runId = cleanParam\(resolvedParams\.run_id\);/);
  assert.doesNotMatch(rootPage, /Crear desde cero/);
  assert.doesNotMatch(rootPage, /Rutas canónicas/);

  assert.match(dynamicPage, /NEXT_PUBLIC_ENABLE_MANUAL_BOT_CREATE === "true"/);
  assert.match(dynamicPage, /if \(!MANUAL_ENABLED\)/);
  assert.match(dynamicPage, /redirect\(`\/bot-studio\$\{query\}`\)/);
});

test("Bot Studio create prefill is available on editable direct-entry steps", () => {
  const loader = read("features/bot-studio/server/loadBotStudioRoute.ts");
  assert.match(loader, /const CREATE_PREFILL_STEPS = new Set<RouteStep>\(\["context", "offer", "knowledge", "integrations", "review", "validate", "apply", "success"\]\);/);
  assert.match(loader, /const isCreatePrefill = isCreate && CREATE_PREFILL_STEPS\.has\(routeStep as RouteStep\);/);
  assert.match(loader, /loadBlueprintAndProfile: isCreatePrefill \|\| isReconfigureDetail/);
});

test("Bot Studio client preview can seed empty editable steps after reactive load", () => {
  const flow = read("features/bot-studio/flow/useBotStudioFlowStateModel.ts");
  const previewSeed = read("features/bot-studio/flow/wizardPreviewSeed.ts");
  assert.ok(previewSeed.includes("function buildBlueprintSeedPatch("));
  assert.ok(previewSeed.includes("function hasBlueprintSeedPatch(patch: DeepPartial<BotStudioWizardState>)"));
  assert.ok(flow.includes("if (hasBlueprintSeedPatch(seedPatch)) state.patchState(seedPatch);"));
  assert.ok(flow.includes("lastSeededPreviewKey.current = currentPreviewSelectionKey;"));
});

test("Bot Studio navigation callbacks and guard redirects are deduped", () => {
  const navigation = read("features/bot-studio/flow/useBotStudioFlowNavigation.ts");
  const runtime = read("features/bot-studio/shared/useWizardRuntime.ts");

  assert.match(navigation, /import \{ useCallback, useMemo \} from "react";/);
  assert.match(navigation, /const buildRouteQuery = useCallback\(/);
  assert.match(navigation, /const goTo = useCallback\(/);
  assert.match(navigation, /\}, \[buildRouteQuery, props\.routeMode, router\]\);/);
  assert.doesNotMatch(navigation, /const goTo = \(step: RouteStep/);

  assert.match(runtime, /const lastRedirectRef = useRef\(""\);/);
  assert.match(runtime, /const redirectKey = `\$\{props\.routeMode\}:\$\{props\.routeStep\}:\$\{targetStep\}:\$\{wizard\?\.id \|\| ""\}`;/);
  assert.match(runtime, /if \(lastRedirectRef\.current === redirectKey\) return;/);
  assert.match(runtime, /redirectOnce\(routeGuard\.blockingRoute, activeWizard\);/);
  assert.match(runtime, /redirectOnce\(recovery\.routeStep, activeWizard\);/);
});

