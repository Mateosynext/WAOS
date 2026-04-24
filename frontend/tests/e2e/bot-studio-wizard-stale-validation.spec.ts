import { expect, test, type Page } from "@playwright/test";

const wizardId = "wiz_stale_validation";
let revision = 1;

function wizardPayload(overrides: Record<string, unknown> = {}) {
  return {
    id: wizardId,
    organization_id: "org_1",
    vertical_id: "salud",
    subvertical: "clinica",
    status: "draft",
    current_step: "launch_review",
    wizard_revision: revision,
    answers: {},
    validation_snapshot: overrides.validation_snapshot,
    ...overrides,
  };
}

async function mockWizardApi(page: Page) {
  await page.route("**/api/onboarding/wizard/start", async (route) => route.fulfill({ json: wizardPayload({ current_step: "vertical_fit" }) }));
  await page.route("**/api/onboarding/wizard/*/steps/*", async (route) => {
    revision += 1;
    return route.fulfill({ json: wizardPayload({ wizard_revision: revision }) });
  });
  await page.route("**/api/onboarding/wizard/*/dry-run", async (route) => route.fulfill({ json: wizardPayload({
    wizard_revision: revision,
    validation_snapshot: { apply_ready: true, gate: { status: "green", label: "Listo", detail: "Dry run fresco" } },
  }) }));
  await page.route("**/api/onboarding/wizard/*/apply", async (route) => route.fulfill({ status: 409, json: { error_type: "revision_conflict", server_revision: revision + 1 } }));
}

test("bloquea apply cuando el usuario cambia datos despues de un dry run exitoso", async ({ page }) => {
  await mockWizardApi(page);
  await page.goto("/bot-studio/create/validate?wizard_id=" + wizardId);

  await expect(page.getByTestId("validate-step")).toBeVisible();
  await page.getByTestId("run-dry-run").click();
  await expect(page.getByTestId("continue-to-apply")).toBeEnabled();
  await page.getByTestId("continue-to-apply").click();
  await expect(page).toHaveURL(/\/bot-studio\/create\/apply/);

  await page.goBack();
  await page.goto("/bot-studio/create/offer?wizard_id=" + wizardId);
  await page.getByTestId("services-textarea").fill("Oferta modificada despues del dry run");
  await page.getByTestId("save-offer").click();

  await page.goto("/bot-studio/create/apply?wizard_id=" + wizardId);
  await expect(page.getByTestId("apply-wizard")).toBeDisabled();
  await expect(page.getByText(/dry run|validacion|validación|revision/i)).toBeVisible();

  await page.goto("/bot-studio/create/validate?wizard_id=" + wizardId);
  await page.getByTestId("run-dry-run").click();
  await expect(page.getByTestId("continue-to-apply")).toBeEnabled();
});
