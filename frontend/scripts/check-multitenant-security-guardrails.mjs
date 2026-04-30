import fs from "node:fs";
import path from "node:path";

const frontendRoot = process.cwd();
const repoRoot = path.resolve(frontendRoot, "..");
function readRepo(file) { return fs.readFileSync(path.join(repoRoot, file), "utf8"); }
function assert(condition, message) { if (!condition) throw new Error(message); }
function assertIncludes(file, needles) {
  const source = readRepo(file);
  for (const needle of needles) assert(source.includes(needle), `${file} must include ${needle}`);
  return source;
}

assertIncludes("frontend/app/api/ai/route-helpers.ts", ["X-WAOS-Org-Id", "X-WAOS-Bot-Id", "X-Request-Id", "X-Correlation-Id"]);

const security = assertIncludes("backend/app/security.py", [
  "ensure_request_scope_matches",
  "tenant_context_mismatch",
  "bot_context_mismatch",
  "ensure_org_access",
  "ensure_bot_access",
]);
assert(security.includes("organization_id not in user.get"), "ensure_org_access must still validate membership, not only request context");

assertIncludes("backend/app/ai_workflows/hardening.py", [
  "require_authorized_run",
  "ensure_org_access",
  "ensure_request_scope_matches",
  "ai_workflow_run",
]);

const workflowRouter = assertIncludes("backend/app/api/routers/ai_workflows.py", [
  "HumanConfirmationPayload",
  "ConfigDict(extra=\"forbid\"",
  "field_key: str",
  "audit_note",
  "actor_user_id",
  "idempotency_key",
  "require_authorized_run",
]);
assert(!workflowRouter.includes("payload: dict = Body(...)"), "human confirmations must not accept raw dict payloads");

const persistence = assertIncludes("backend/app/ai_workflows/persistence.py", [
  "_assert_run_exists",
  "dedupe_key",
  "sequence",
  "ux_ai_workflow_events_run_dedupe",
  "FOREIGN KEY(run_id) REFERENCES ai_workflow_runs(id)",
]);
for (const fn of ["upsert_step", "record_event", "record_cost", "save_json_artifact", "save_simulation_report", "save_go_live_readiness", "upsert_human_confirmation", "start_workflow_action", "complete_workflow_action"]) {
  assert(persistence.includes(`def ${fn}`), `persistence must define ${fn}`);
}
assert((persistence.match(/_assert_run_exists\(conn, run_id\)/g) || []).length >= 8, "workflow child writes must assert parent run existence");

assertIncludes("backend/app/application/bot_service.py", ["ensure_org_access", "ensure_bot_access", "client_request_id"]);
assertIncludes("backend/app/application/conversation_service.py", ["_get_accessible_conversation", "ensure_org_access"]);
assertIncludes("backend/app/application/conversation_handlers/add_message_or_note.py", ["_get_accessible_conversation", "require_permission"]);
assertIncludes("backend/app/application/tool_execution_handlers/execute.py", ["ensure_org_access", "_validate_bot_access", "idempotency_key"]);
assertIncludes("backend/app/application/knowledge_ingestion_service.py", ["ensure_org_access"]);
assertIncludes("backend/app/api/handlers/crm_sales.py", ["confirm_payment_route", "ensure_org_access", "refresh_payment_status"]);

const requiredFuzzTargets = [
  "/api/v1/bots",
  "/api/v1/bots/{bot_id}",
  "/api/v1/ai/workflows/{run_id}",
  "/api/v1/ai/workflows/{run_id}/apply",
  "/api/v1/ai/workflows/{run_id}/prepare-canary",
  "/api/v1/ai/workflows/{run_id}/human-confirmations",
  "/api/v1/conversations/{conversation_id}/messages",
  "/api/v1/tool-executions/execute",
  "/api/v1/sales/payments/{payment_id}/confirm",
  "/api/v1/knowledge/sources/{source_connection_id}/sync",
];
const riskRegister = readRepo("MULTITENANT_SECURITY_FUZZ_REGISTER_2026-04-26.md");
for (const target of requiredFuzzTargets) assert(riskRegister.includes(target), `fuzz register must include ${target}`);
assert(riskRegister.includes("NO VERIFICADO") && riskRegister.includes("provider"), "fuzz register must preserve no-claim provider gaps");

console.log("[OK] multi-tenant security guardrails are enforced");

if (!process.exitCode) process.exit(0);
