import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import test from "node:test";

const root = path.join(process.cwd());
const read = (file: string) => fs.readFileSync(path.join(root, file), "utf8");

test("AI Command Center loads and passes the real vertical catalog end to end", () => {
  const page = read("app/bot-studio/page.tsx");
  const center = read("features/ai-command-center/AiCommandCenter.tsx");
  const prompt = read("features/ai-command-center/AiCommandPrompt.tsx");
  assert.match(page, /getVerticalCatalog/);
  assert.match(page, /safeVerticals/);
  assert.match(page, /<AiCommandCenter[\s\S]*verticals=\{verticals\}/);
  assert.match(center, /verticals: AiCommandVerticalOption\[\]/);
  assert.match(center, /<AiCommandPrompt[\s\S]*verticals=\{verticals\}/);
  assert.match(prompt, /<select[\s\S]*value=\{payload\.vertical_id \|\| ""\}/);
  assert.match(prompt, /Subvertical \/ tipo de operacion/);
  assert.doesNotMatch(prompt, /Industria opcional<input/);
});

test("AI workflow stream recovers snapshots without requiring manual refresh", () => {
  const center = read("features/ai-command-center/AiCommandCenter.tsx");
  const hook = read("features/ai-command-center/useAiWorkflowStream.ts");
  const timeline = read("features/ai-command-center/AiRunTimeline.tsx");
  assert.match(hook, /snapshot: AiWorkflowRunEnvelope \| null/);
  assert.match(hook, /recoverFromSnapshot/);
  assert.match(hook, /setInterval/);
  assert.match(center, /stream\.snapshot \|\| run/);
  assert.match(timeline, /mergeEvents/);
  assert.doesNotMatch(hook, /usa Actualizar estado para recuperar/);
});


test("AI Command Center generation click never goes silent on missing inputs", () => {
  const center = read("features/ai-command-center/AiCommandCenter.tsx");
  const prompt = read("features/ai-command-center/AiCommandPrompt.tsx");
  const css = read("app/globals.css");
  assert.match(center, /getStartBlockingReason/);
  assert.match(center, /Falta informacion para generar el bot/);
  assert.match(prompt, /submitHint/);
  assert.match(prompt, /disabled=\{busy\}/);
  assert.doesNotMatch(prompt, /disabled=\{!canSubmit\}/);
  assert.match(css, /\.primary-btn:disabled/);
});


test("AI Command Center guards double-submit and resets SSE cursors per run", () => {
  const center = read("features/ai-command-center/AiCommandCenter.tsx");
  const hook = read("features/ai-command-center/useAiWorkflowStream.ts");
  assert.match(center, /startInFlightRef/);
  assert.match(center, /actionInFlightRef/);
  assert.match(center, /if \(startInFlightRef\.current \|\| Boolean\(busy\)\) return/);
  assert.match(center, /if \(!runId \|\| actionInFlightRef\.current \|\| Boolean\(busy\)\) return/);
  assert.match(center, /typeof value === "boolean"\) return null/);
  assert.match(hook, /activeRunIdRef/);
  assert.match(hook, /lastEventIdRef\.current = null/);
  assert.match(hook, /lastSnapshotEvent\?\.id/);
});

test("AI Command Center resolves human confirmations before safe apply", () => {
  const center = read("features/ai-command-center/AiCommandCenter.tsx");
  const types = read("features/ai-command-center/types.ts");
  const helper = read("app/api/ai/route-helpers.ts");
  assert.match(types, /AiHumanConfirmation/);
  assert.match(types, /AiGoLiveReadiness/);
  assert.match(center, /HumanConfirmationsPanel/);
  assert.match(center, /human-confirmations/);
  assert.match(center, /go-live-readiness/);
  assert.match(center, /pendingConfirmations\.length === 0/);
  assert.match(center, /readiness\.can_apply !== false/);
  assert.match(center, /!wizardId/);
  assert.match(center, /Abrir bot/);
  assert.match(helper, /LONG_RUNNING_PROXY_TIMEOUT_MS = 120_000/);
  assert.match(helper, /prepare-apply\|prepare-canary\|go-live-readiness/);
});
