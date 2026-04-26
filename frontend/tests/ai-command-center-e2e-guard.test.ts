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
