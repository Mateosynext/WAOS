import { expect, test } from "@playwright/test";

const canonicalCreateSteps = ["context", "identity", "offer", "knowledge", "integrations", "review", "validate"];

test.describe("bot studio navigation recovery", () => {
  test("refresh conserva cada paso canonico de create", async ({ page }) => {
    for (const step of canonicalCreateSteps) {
      await page.goto(`/bot-studio/create/${step}`);
      await page.reload();
      await expect(page).toHaveURL(new RegExp(`/bot-studio/create/${step}`));
    }
  });

  test("abrir apply sin dry run recupera a validate", async ({ page }) => {
    await page.goto("/bot-studio/create/apply");
    await expect(page).toHaveURL(/\/bot-studio\/create\/validate|\/bot-studio\/create\/context/);
    await expect(page.getByText(/ruta recuperada|valid/i)).toBeVisible();
  });

  test("abrir success sin apply recupera a validate o context", async ({ page }) => {
    await page.goto("/bot-studio/create/success");
    await expect(page).toHaveURL(/\/bot-studio\/create\/(validate|context)/);
  });

  test("back desde apply no habilita confirmacion sin validacion fresca", async ({ page }) => {
    await page.goto("/bot-studio/create/validate");
    await page.goto("/bot-studio/create/apply");
    await page.goBack();
    await expect(page).toHaveURL(/\/bot-studio\/create\/validate|\/bot-studio\/create\/context/);
  });

  test("forward despues de recovery se mantiene en ruta segura", async ({ page }) => {
    await page.goto("/bot-studio/create/apply");
    await page.goForward().catch(() => undefined);
    await expect(page).not.toHaveURL(/\/bot-studio\/create\/success/);
  });

  test("reconfigure sin bot seleccionado vuelve a select", async ({ page }) => {
    await page.goto("/bot-studio/reconfigure/diff");
    await expect(page).toHaveURL(/\/bot-studio\/reconfigure\/select/);
    await expect(page.getByTestId("reconfigure-select-step")).toBeVisible();
  });
});
