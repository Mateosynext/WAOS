import test from "node:test";
import assert from "node:assert/strict";
import { normalizeWizardError, parseWizardError, requestWizardJson, wizardErrorToMessage } from "../../features/bot-studio/services/wizardClient";

test("normalizes 500 dry run failures as network_error", () => {
  const error = parseWizardError(500, { detail: "dry run exploded" });
  assert.deepEqual(error, { type: "network_error", message: "dry run exploded" });
  assert.equal(wizardErrorToMessage(error), "dry run exploded");
});

test("normalizes 409 revision conflict with server revision", () => {
  const error = parseWizardError(409, { server_revision: 7 });
  assert.deepEqual(error, { type: "revision_conflict", serverRevision: 7 });
  assert.match(wizardErrorToMessage(error), /7/);
});

test("normalizes validation failed payloads with issues", () => {
  const error = parseWizardError(422, { issues: [{ key: "offer", message: "Falta oferta", severity: "blocking" }] });
  assert.equal(error.type, "validation_failed");
  assert.deepEqual(error.issues, [{ key: "offer", field: undefined, message: "Falta oferta", severity: "blocking" }]);
});

test("normalizes partial apply failures", () => {
  const error = parseWizardError(207, { completed: ["behavior"], failed: ["knowledge"] });
  assert.deepEqual(error, { type: "partial_failure", completed: ["behavior"], failed: ["knowledge"] });
});

test("request client throws typed errors instead of generic Error", async () => {
  const response = new Response(JSON.stringify({ error_type: "revision_conflict", server_revision: 12 }), { status: 409 });
  await assert.rejects(
    requestWizardJson("/api/onboarding/wizard/wiz_1/apply", {}, { fetcher: async () => response }),
    (error: unknown) => {
      assert.deepEqual(error, { type: "revision_conflict", serverRevision: 12 });
      return true;
    },
  );
});

test("network exceptions become normalized wizard errors", () => {
  assert.deepEqual(normalizeWizardError(new TypeError("Failed to fetch")), { type: "network_error", message: "Failed to fetch" });
});
