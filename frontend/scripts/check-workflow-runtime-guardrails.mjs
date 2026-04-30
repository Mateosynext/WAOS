import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");
function readRepo(file) { return fs.readFileSync(path.join(repoRoot, file), "utf8"); }
function read(file) { return fs.readFileSync(path.join(root, file), "utf8"); }
function assert(condition, message) { if (!condition) throw new Error(message); }
function includes(source, needle, label) { assert(source.includes(needle), `${label} must include ${needle}`); }

const persistence = readRepo("backend/app/ai_workflows/persistence.py");
includes(persistence, "ai_workflow_event_cursors", "workflow persistence");
includes(persistence, "def _claim_event_sequence", "workflow persistence");
includes(persistence, "INSERT OR IGNORE INTO ai_workflow_event_cursors", "workflow persistence");
includes(persistence, "ON CONFLICT (run_id) DO NOTHING", "workflow persistence");
includes(persistence, "def event_cursor_exists", "workflow persistence");
includes(persistence, "def get_latest_event_id", "workflow persistence");
includes(persistence, "Unknown/stale Last-Event-ID must not replay the whole stream", "workflow persistence");
includes(persistence, "def recover_stale_running_runs", "workflow persistence");
assert(!persistence.includes("def _next_event_sequence"), "workflow events must not use MAX(sequence)+1 helper");
assert(!persistence.includes("sequence=_next_event_sequence"), "record_event must claim sequence atomically");

const router = readRepo("backend/app/api/routers/ai_workflows.py");
includes(router, "workflow.cursor_not_found", "workflow router");
includes(router, "event_cursor_exists", "workflow router");
includes(router, "get_latest_event_id", "workflow router");
includes(router, "/api/v1/ai/workflow-recovery/stale-runs", "workflow router");
includes(router, "recover_stale_running_runs", "workflow router");
includes(router, "background_tasks.add_task(run_bot_autopilot_background", "workflow router");
includes(router, "rerun-failed-step", "workflow router");

const sseProxy = read("app/api/ai/workflows/[runId]/events/route.ts");
includes(sseProxy, "X-WAOS-Stream-Error", "frontend SSE proxy");
includes(sseProxy, "X-WAOS-Upstream-Status", "frontend SSE proxy");
includes(sseProxy, "Last-Event-ID", "frontend SSE proxy");

const hook = read("features/ai-command-center/useAiWorkflowStream.ts");
includes(hook, "function eventSequence", "AI workflow stream hook");
includes(hook, "function orderEvents", "AI workflow stream hook");
includes(hook, "workflow.cursor_not_found", "AI workflow stream hook");
includes(hook, "lastOrderedEvent", "AI workflow stream hook");

console.log("[OK] workflow runtime/recovery guardrails are enforced");

if (!process.exitCode) process.exit(0);
