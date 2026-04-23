import test from "node:test";
import assert from "node:assert/strict";
import { buildWizardAwareRouteQuery } from "../app/bot-studio/navigationState";

test("wizard-aware route query prioritizes the freshly saved wizard id", () => {
  const query = buildWizardAwareRouteQuery({
    wizardId: "wiz_stale",
    botId: "bot_1",
    organizationId: "org_1",
    verticalId: "dental",
    subvertical: "ortodoncia",
    primaryObjective: "agendar",
  }, "wiz_fresh");

  assert.equal(query.wizard_id, "wiz_fresh");
  assert.equal(query.bot, "bot_1");
  assert.equal(query.organization_id, "org_1");
});
