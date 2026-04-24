import test from "node:test";
import assert from "node:assert/strict";
import { buildBotStudioHref } from "../features/bot-studio/domain/flowConfig";
import { buildWizardAwareRouteQuery } from "../features/bot-studio/domain/navigationState";

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

test("wizard-aware route query does not leak placeholder route values", () => {
  const query = buildWizardAwareRouteQuery({
    wizardId: "",
    botId: null,
    organizationId: undefined,
    verticalId: "-",
    subvertical: "null",
    primaryObjective: "undefined",
  }, "-");

  assert.equal(query.wizard_id, "");
  assert.equal(query.bot, "");
  assert.equal(query.organization_id, "");
  assert.equal(query.vertical, "");
  assert.equal(query.subvertical, "");
  assert.equal(query.primary_objective, "");
});


test("Bot Studio href builder strips legacy placeholder route values", () => {
  const href = buildBotStudioHref("create", "knowledge", {
    wizard_id: "-",
    bot: "-",
    organization_id: "org_1",
    vertical: "waos-bot",
    subvertical: "null",
    primary_objective: "undefined",
  });

  assert.equal(href, "/bot-studio/create/knowledge?organization_id=org_1&vertical=waos-bot");
});
