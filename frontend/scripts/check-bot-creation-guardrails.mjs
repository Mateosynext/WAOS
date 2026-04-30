#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const read = (path) => readFileSync(join(root, path), 'utf8');
let failed = false;
function assertContains(path, needle, message) {
  const body = read(path);
  if (!body.includes(needle)) {
    failed = true;
    console.error(`FAIL ${path}: ${message}`);
    console.error(`  Missing: ${needle}`);
  } else {
    console.log(`OK   ${path}: ${message}`);
  }
}
function assertNotContains(path, needle, message) {
  const body = read(path);
  if (body.includes(needle)) {
    failed = true;
    console.error(`FAIL ${path}: ${message}`);
    console.error(`  Forbidden: ${needle}`);
  } else {
    console.log(`OK   ${path}: ${message}`);
  }
}

assertContains('features/ai-command-center/AiCommandCenter.tsx', 'pickFreshestRun(run, stream.snapshot)', 'local refresh and SSE snapshot are merged by freshness, not stream-first');
assertNotContains('features/ai-command-center/AiCommandCenter.tsx', 'stream.snapshot || run', 'stale terminal stream snapshots cannot override refreshed run data');
assertContains('features/ai-command-center/AiCommandCenter.tsx', 'organizations.length === 1 ? organizations[0] : undefined', 'multi-org creation requires explicit organization selection');
assertContains('features/ai-command-center/AiCommandCenter.tsx', 'getStartBlockingReason(payload)', 'start action is guarded before network calls');
assertContains('features/ai-command-center/AiCommandCenter.tsx', 'currentBlockReason = actionBlockReason', 'prepare/apply actions are guarded inside JS handlers, not only by disabled buttons');
assertContains('features/ai-command-center/AiCommandCenter.tsx', 'pendingConfirmations.length === 0', 'apply is blocked while human confirmations remain pending');
assertContains('features/ai-command-center/AiCommandCenter.tsx', 'auto_apply: false', 'frontend never sends auto_apply=true');

assertContains('features/ai-command-center/useAiWorkflowStream.ts', 'workflow.stream_error', 'transport failures are not represented as workflow.failed');
assertContains('features/ai-command-center/useAiWorkflowStream.ts', 'allowTerminal?: boolean', 'stream can fetch one final snapshot after terminal events');
assertContains('features/ai-command-center/useAiWorkflowStream.ts', 'finalSnapshotFetchedRef', 'terminal snapshot recovery is one-shot and cannot poll forever');
assertContains('features/ai-command-center/useAiWorkflowStream.ts', 'if (terminalRef.current) return;', 'regular polling stops after terminal state');
assertNotContains('features/ai-command-center/useAiWorkflowStream.ts', 'workflow.failed" ? String(event.message || "Error temporal', 'transport errors must not be collapsed into workflow failure');

const routePath = 'app/api/ai/workflows/[runId]/events/route.ts';
assertContains(routePath, 'workflow.stream_error', 'Next SSE proxy emits non-terminal stream errors');
assertNotContains(routePath, 'event_type: "workflow.failed"', 'Next SSE proxy must not fabricate terminal workflow.failed events');
assertContains(routePath, 'signal: request.signal', 'SSE upstream fetch is abortable when the client disconnects');

if (failed) {
  console.error('\nBot creation guardrails failed. Fix the regression before shipping.');
  process.exit(1);
}
console.log('\nBot creation guardrails passed.');

if (!process.exitCode) process.exit(0);
