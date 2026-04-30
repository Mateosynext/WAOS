import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
function read(file) { return fs.readFileSync(path.join(root, file), "utf8"); }
function assert(condition, message) { if (!condition) throw new Error(message); }

const botStudioPage = read("app/bot-studio/page.tsx");
assert(!botStudioPage.includes("async function safeBots"), "Bot Studio page must not swallow bot loader errors into []");
assert(!botStudioPage.includes("async function safeVerticals"), "Bot Studio page must not swallow vertical loader errors into []");
assert(botStudioPage.includes("loadWithNotice"), "Bot Studio page must surface loader failures");
assert(botStudioPage.includes("datos incompletos"), "Bot Studio page must render an operator-visible degraded warning");

const routeLoader = read("features/bot-studio/server/loadBotStudioRoute.ts");
assert(routeLoader.includes("loadWarnings"), "Bot Studio route loader must return load warnings");
assert(!routeLoader.includes("catch {\n    return fallback;\n  }"), "safeOptional must not silently return fallback");
assert(routeLoader.includes("optionalErrorMessage"), "safeOptional must capture failure context");

const api = read("app/lib/api.ts");
assert(api.includes("fallbackReason"), "apiFetchOrDefault fallbacks must require auditable context");
assert(api.includes("console.warn"), "apiFetchOrDefault must emit a visible degraded-mode warning");

const prepareApplyRoute = read("app/api/ai/workflows/[runId]/prepare-apply/route.ts");
assert(!prepareApplyRoute.includes("export async function GET"), "prepare-apply frontend proxy must not expose unsupported GET");
assert(prepareApplyRoute.includes("export async function POST"), "prepare-apply frontend proxy must expose POST");

const routeHelpers = read("app/api/ai/route-helpers.ts");
for (const header of ["X-WAOS-Org-Id", "X-WAOS-Bot-Id", "X-Request-Id", "X-Correlation-Id"]) {
  assert(routeHelpers.includes(header), `AI proxy must forward ${header}`);
}

const eventsRoute = read("app/api/ai/workflows/[runId]/events/route.ts");
assert(eventsRoute.includes("X-WAOS-Stream-Error"), "SSE proxy failures must be observable by monitors");
assert(!eventsRoute.includes("status: 200"), "SSE proxy must not return HTTP 200 on upstream failure");
assert(eventsRoute.includes("status,"), "SSE failure response must preserve the failing status code");

console.log("[OK] P1 operational guardrails are enforced");

if (!process.exitCode) process.exit(0);
