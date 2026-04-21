import test from "node:test";
import assert from "node:assert/strict";
import { buildReactiveVerticalPreviewModel, isSelectedSubverticalValid, normalizeName } from "../app/components/reactiveVerticalViewModel";
import { normalizeVerticalProfile } from "../app/lib/contracts/verticals";
import type { WizardBlueprint } from "../app/bot-studio/wizard-types";

const verticalProfile = normalizeVerticalProfile({
  id: "vertical_dental",
  name: "Dental",
  description: "Seguimiento y recuperación de pacientes",
  problem: "Poca conversión a tratamientos",
  short_name: "Dental",
  flows: ["follow_up"],
  recommended_integrations: ["Google Calendar", "HubSpot"],
  selected_subvertical: { name: "Ortodoncia", promise: "Más valoraciones convertidas", qualification_questions: ["¿Buscas brackets o alineadores?"], service_bundle: ["Valoración", "Radiografía"] },
  subvertical_profiles: [{ name: "Ortodoncia", promise: "Más valoraciones convertidas", qualification_questions: ["¿Buscas brackets o alineadores?"], service_bundle: ["Valoración", "Radiografía"], templates: [{ title: "Seguimiento valoración" }] }],
  pipeline: { templates: [{ title: "Template pipeline" }] },
});

const blueprint: WizardBlueprint = {
  profile: { name: "Dental premium", problem: "Poca recuperación post consulta", recommended_subverticals: ["Ortodoncia", "Implantes"] },
  setup: { personality: { tone: "cálido" }, wizard: { selected_subvertical: "Ortodoncia", recommended_integrations: [{ name: "WhatsApp" }], recommended_playbooks: [{ label: "Reactivación" }] }, response_templates: [{ title: "Template setup" }] },
};

test("reactive vertical preview model merges blueprint and vertical fallbacks", () => {
  const model = buildReactiveVerticalPreviewModel({ selectedSubvertical: "Ortodoncia", verticalProfile, blueprint, activeCatalogVertical: verticalProfile });
  assert.equal(model.previewVerticalName, "Dental premium");
  assert.equal(model.previewSubverticalName, "Ortodoncia");
  assert.match(model.previewIntegrations, /WhatsApp/);
  assert.match(model.previewPlaybooks, /Reactivación/);
  assert.match(model.previewTemplates, /Template setup/);
  assert.match(model.previewQuestions, /alineadores/);
  assert.equal(model.previewTone, "cálido");
  assert.equal(model.subverticalOptions.includes("Implantes"), true);
});

test("reactive vertical helper validates subvertical selection without coupling to the component", () => {
  const model = buildReactiveVerticalPreviewModel({ selectedSubvertical: "Ortodoncia", verticalProfile, blueprint, activeCatalogVertical: verticalProfile });
  assert.equal(isSelectedSubverticalValid("ortodoncia", model.subverticalOptions), true);
  assert.equal(isSelectedSubverticalValid("Pediatría", model.subverticalOptions), false);
  assert.equal(normalizeName("  ORTODONCIA "), "ortodoncia");
});
