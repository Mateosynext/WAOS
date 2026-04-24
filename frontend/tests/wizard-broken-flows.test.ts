import test from "node:test";
import assert from "node:assert/strict";
import { normalizeDisplayError } from "../app/lib/error-display";
import { createLatestWizardReactiveSelectionLoader, loadWizardReactiveSelection } from "../features/bot-studio/services/wizardReactiveData";
import { saveWizardStepRequest } from "../features/bot-studio/services/wizardApi";

type FetchCall = { url: string; init?: RequestInit };

function withMockFetch(handler: (url: string, init?: RequestInit) => Promise<Response>) {
  const original = globalThis.fetch;
  const calls: FetchCall[] = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init });
    return handler(url, init);
  }) as typeof fetch;
  return {
    calls,
    restore() {
      globalThis.fetch = original;
    },
  };
}

test("login success paths never surface raw NEXT_REDIRECT to the UI", () => {
  assert.equal(normalizeDisplayError(new Error("NEXT_REDIRECT"), "Acceso correcto"), "Acceso correcto");
  const redirectLike = new Error("opaque");
  (redirectLike as Error & { digest?: string }).digest = "NEXT_REDIRECT;replace;/";
  assert.equal(normalizeDisplayError(redirectLike, "Acceso correcto"), "Acceso correcto");
});

test("wizard reactive preview can fail partially without hiding the successful payload", async () => {
  const mock = withMockFetch(async (url) => {
    if (url.includes("/api/onboarding/wizard/blueprint")) {
      return new Response(JSON.stringify({ profile: { id: "dental" }, steps: [] }), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    return new Response(JSON.stringify({ detail: "gateway timeout" }), { status: 504, headers: { "Content-Type": "application/json" } });
  });
  try {
    const result = await loadWizardReactiveSelection({ organizationId: "org_1", verticalId: "dental", subvertical: "ortodoncia" });
    assert.equal(result.blueprint?.profile?.id, "dental");
    assert.equal(result.verticalProfile, null);
    assert.match(result.errors.join(" "), /gateway timeout/i);
    assert.equal(mock.calls.length, 2);
  } finally {
    mock.restore();
  }
});

test("manual save can still succeed after an autosave failure", async () => {
  let attempt = 0;
  const mock = withMockFetch(async (_url) => {
    attempt += 1;
    if (attempt === 1) {
      return new Response(JSON.stringify({ detail: "autosave timeout" }), { status: 504, headers: { "Content-Type": "application/json" } });
    }
    return new Response(JSON.stringify({ id: "wiz_1", wizard_revision: 2, current_step: "offer" }), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  try {
    await assert.rejects(
      () => saveWizardStepRequest("wiz_1", "business_basics", { business_name: "Clínica Demo" }, { expectedRevision: 1 }),
      /autosave timeout/i,
    );
    const saved = await saveWizardStepRequest("wiz_1", "business_basics", { business_name: "Clínica Demo" }, { expectedRevision: 1 });
    assert.equal(saved.id, "wiz_1");
    assert.equal(saved.current_step, "offer");
  } finally {
    mock.restore();
  }
});

test("rapid vertical changes abort the stale preview and only keep the latest state", async () => {
  const seenSignals: AbortSignal[] = [];
  type FirstResult = { blueprint: null; verticalProfile: null; errors: string[] };
  type SecondResult = { blueprint: { profile: { id: string } }; verticalProfile: null; errors: string[] };
  let resolveFirst: ((value: FirstResult) => void) | undefined;
  let resolveSecond: ((value: SecondResult) => void) | undefined;

  const loader = createLatestWizardReactiveSelectionLoader(async (request, signal) => {
    if (signal) seenSignals.push(signal);
    if (request.verticalId === "dental") {
      return await new Promise((resolve) => {
        resolveFirst = resolve as (value: FirstResult) => void;
      });
    }
    return await new Promise((resolve) => {
      resolveSecond = resolve as (value: SecondResult) => void;
    });
  });

  const firstPromise = loader.load({ organizationId: "org_1", verticalId: "dental" });
  const secondPromise = loader.load({ organizationId: "org_1", verticalId: "medspa" });

  assert.equal(seenSignals[0]?.aborted, true);
  if (!resolveFirst || !resolveSecond) throw new Error('Resolvers were not captured');
  resolveFirst({ blueprint: null, verticalProfile: null, errors: ["stale"] });
  resolveSecond({ blueprint: { profile: { id: "medspa" } }, verticalProfile: null, errors: [] });

  const [first, second] = await Promise.all([firstPromise, secondPromise]);
  assert.equal(first, null);
  assert.equal(second?.blueprint?.profile?.id, "medspa");
});
