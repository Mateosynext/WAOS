import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");
function read(file) { return fs.readFileSync(path.join(root, file), "utf8"); }
function readRepo(file) { return fs.readFileSync(path.join(repoRoot, file), "utf8"); }
function assert(condition, message) { if (!condition) throw new Error(message); }
function assertIncludes(file, needles) {
  const source = file.startsWith("../") ? readRepo(file.slice(3)) : read(file);
  for (const needle of needles) assert(source.includes(needle), `${file} must include ${needle}`);
  return source;
}

const middleware = assertIncludes("middleware.ts", ["x-waos-session-error", "x-waos-scope-repair", "invalid-selected-org-cleared", "organization-auto-selected"]);
assert(middleware.includes("VerifiedSession | null"), "middleware session verification must be typed and observable");

const sharedSession = assertIncludes("app/lib/auth/shared-session.ts", ["SessionFetchError", "auth_me_failed", "auth_me_network_error", "console.error"]);
assert(!sharedSession.includes("catch {\n    return null;\n  }"), "session user loader must not turn upstream failures into null silently");

assertIncludes("app/lib/session.ts", ["getSession failed; clearing scope cookies", "clearSessionCookies"]);
assertIncludes("app/lib/api.ts", ["fallbackReason", "console.warn", "x-waos-org-id", "x-waos-bot-id"]);
assertIncludes("app/api/ai/route-helpers.ts", ["X-WAOS-Org-Id", "X-WAOS-Bot-Id", "X-Request-Id", "X-Correlation-Id"]);

const botStudioPage = read("app/bot-studio/page.tsx");
assert(!botStudioPage.includes("async function safeBots"), "Bot Studio page must not hide bots loader failures");
assert(!botStudioPage.includes("async function safeVerticals"), "Bot Studio page must not hide vertical loader failures");
assert(botStudioPage.includes("datos incompletos"), "Bot Studio must render a degraded-mode warning");

const createBotAction = assertIncludes("app/actions/bots.ts", ["client_request_id", "stableBotCreateRequestId", "Idempotency-Key"]);
assert(!createBotAction.includes("JSON.stringify(payload)"), "manual bot creation must not POST raw payload without client_request_id");

const aiCommandCenter = assertIncludes("features/ai-command-center/AiCommandCenter.tsx", ["client_request_id", "prepare-apply", "idempotency_key", "confirm"]);
const aiPersistence = assertIncludes("../backend/app/ai_workflows/persistence.py", ["dedupe_key", "sequence", "INSERT OR IGNORE", "ON CONFLICT", "next_sequence"]);
const workflowHardening = assertIncludes("../backend/app/ai_workflows/hardening.py", ["explicit_partial_apply_override", "completed_partial"]);
assert(workflowHardening.includes("explicit_partial_apply_override"), "completed_partial requires explicit override path");
const workflowRouter = assertIncludes("../backend/app/api/routers/ai_workflows.py", ["prepare_apply", "confirmation_token", "run_bot_autopilot_background", "rerun-failed-step", "background_tasks.add_task"]);

assertIncludes("../backend/app/application/tool_execution_handlers/execute.py", ["idempotency_key", "tool_execution_already_running", "mark_job_completed", "mark_job_failed"]);
assertIncludes("../backend/app/job_idempotency.py", ["INSERT OR IGNORE", "ON CONFLICT (dedupe_key) DO NOTHING"]);
assertIncludes("../backend/app/security.py", ["ensure_request_scope_matches", "tenant_context_mismatch", "bot_context_mismatch", "No access to organization"]);
assertIncludes("../backend/app/application/conversation_service.py", ["_get_accessible_conversation", "ensure_org_access"]);
assertIncludes("../backend/app/application/knowledge_ingestion_service.py", ["ensure_org_access"]);
assertIncludes("../backend/app/api/handlers/webhooks.py", ["webhook_signature_missing", "verify_hub_signature", "register_whatsapp_event_receipt"]);
assertIncludes("../backend/app/application/appointment_service.py", ["blocked_slot_invalid_range", "blocked_slot_overlaps_existing", "ensure_org_access"]);

for (const file of ["../backend/scripts/check_repo_hygiene.py", "../backend/scripts/release_gate.py", "../scripts/validate_release_in_ci.sh"]) {
  assert(fs.existsSync(path.join(repoRoot, file.slice(3))), `${file} must exist`);
}

console.log("[OK] critical flow guardrails are enforced");

if (!process.exitCode) process.exit(0);
