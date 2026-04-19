import { test, expect, Page } from '@playwright/test';
import { chooseOrganization, currentCodeFromSecret, login, readSeedSecrets, submitLogin } from './helpers.real';

const seeds = readSeedSecrets();

async function loginToBotStudio(page: Page, mode: 'create' | 'reconfigure' = 'create', options?: { chooseShellOrg?: boolean }) {
  await login(page, seeds.mfa_user_email, seeds.mfa_user_password);
  await submitLogin(page);
  await page.getByLabel('Código MFA').fill(currentCodeFromSecret(seeds.mfa_user_secret));
  await submitLogin(page);
  if (options?.chooseShellOrg !== false) await chooseOrganization(page, 'org_1');
  await page.goto(`/bot-studio?mode=${mode}`);
  await expect(page.getByTestId('vertical-picker')).toBeVisible();
  await expect(page.getByTestId('sticky-summary-rail')).toBeVisible();
}

async function chooseOrganizationInWizard(page: Page) {
  const select = page.getByTestId('organization-select');
  await expect(select).toBeVisible();
  const currentValue = await select.inputValue();
  if (currentValue) return currentValue;
  const options = await select.locator('option').evaluateAll((nodes) => nodes.map((node) => ({
    value: (node as HTMLOptionElement).value,
    disabled: (node as HTMLOptionElement).disabled,
  })));
  const nextOption = options.find((item) => item.value && !item.disabled);
  expect(nextOption?.value).toBeTruthy();
  await select.selectOption(nextOption!.value);
  return nextOption!.value;
}

async function confirmFirstVertical(page: Page) {
  const cards = page.locator('[data-testid^="vertical-card-"]');
  await expect(cards.first()).toBeVisible();
  const testId = await cards.first().getAttribute('data-testid');
  expect(testId).toBeTruthy();
  const id = testId!.replace('vertical-card-', '');
  await cards.first().click();
  await page.getByTestId(`confirm-vertical-${id}`).click();
  return id;
}

async function confirmFirstSubvertical(page: Page) {
  const cards = page.locator('[data-testid^="subvertical-card-"]');
  await expect(cards.first()).toBeVisible();
  const testId = await cards.first().getAttribute('data-testid');
  expect(testId).toBeTruthy();
  const id = testId!.replace('subvertical-card-', '');
  await cards.first().click();
  await page.getByTestId(`confirm-subvertical-${id}`).click();
  return id;
}

async function prepareExplicitScope(page: Page) {
  await chooseOrganizationInWizard(page);
  await confirmFirstVertical(page);
  await expect(page.getByTestId('save-scope')).toBeDisabled();
  await confirmFirstSubvertical(page);
}

test('@critical bot studio no usa defaults silenciosos en create y exige confirmación explícita', async ({ page }) => {
  await loginToBotStudio(page, 'create');

  await expect(page.getByTestId('organization-select')).toHaveValue('');
  await expect(page.getByTestId('save-scope')).toBeDisabled();
  await page.locator('[data-testid^="vertical-card-"]').first().click();
  await expect(page.getByText(/falta pulsar “Usar esta industria”/i)).toBeVisible();
  await expect(page.getByTestId('save-scope')).toBeDisabled();

  await prepareExplicitScope(page);
  await expect(page.getByTestId('summary-industry')).not.toContainText('Pendiente');
  await expect(page.getByTestId('summary-operation')).not.toContainText('Pendiente');
});

test('@critical bot studio crea un asistente operativo sin salir del wizard y valida al final', async ({ page }) => {
  await loginToBotStudio(page, 'create');
  await prepareExplicitScope(page);

  const suffix = Date.now().toString().slice(-6);
  await page.getByTestId('business-name-input').fill(`Negocio QA ${suffix}`);
  await page.getByTestId('bot-name-input').fill(`Asistente QA ${suffix}`);
  await page.getByTestId('save-scope').click();

  await expect(page.getByTestId('save-basics')).toBeVisible();
  await page.getByTestId('save-basics').click();

  const services = page.getByLabel('Servicios base');
  if (!((await services.inputValue()).trim())) {
    await services.fill('Consulta inicial\nSeguimiento');
  }
  await page.getByTestId('save-offer').click();

  const faq = page.getByLabel('FAQ base');
  if (!((await faq.inputValue()).trim())) {
    await faq.fill('Atienden sábados? | Sí');
  }
  await page.getByTestId('save-knowledge').click();

  await page.getByTestId('save-integrations').click();
  await expect(page.getByTestId('apply-wizard')).toBeVisible();
  await page.getByTestId('apply-wizard').click();

  await expect(page).toHaveURL(/\/bot-studio/);
  await expect(page.getByTestId('simulate-step')).toBeVisible();
  await page.getByTestId('run-simulation').click();
  await expect(page.getByTestId('simulation-result')).toBeVisible();
  await page.getByTestId('go-publish').click();
  await expect(page.getByTestId('publish-step')).toBeVisible();
});

test('@critical bot studio reconfigure bloquea avance sin asistente operativo explícito', async ({ page }) => {
  await loginToBotStudio(page, 'reconfigure');
  await expect(page.getByTestId('prepare-reconfigure')).toBeDisabled();
  await expect(page.getByText(/Elige el asistente operativo exacto/i)).toBeVisible();

  const botCards = page.locator('[data-testid^="bot-card-"]');
  await expect(botCards.first()).toBeVisible();
  await botCards.first().click();
  await expect(page.getByTestId('prepare-reconfigure')).toBeEnabled();
});

test('@critical bot studio mantiene preview de industria/tipo de operación bloqueado hasta confirmar', async ({ page }) => {
  await loginToBotStudio(page, 'create');
  await chooseOrganizationInWizard(page);

  await page.locator('[data-testid^="vertical-card-"]').first().click();
  await expect(page.getByTestId('summary-industry')).toContainText('Pendiente');
  await expect(page.getByTestId('save-scope')).toBeDisabled();
  await confirmFirstVertical(page);

  await page.locator('[data-testid^="subvertical-card-"]').first().click();
  await expect(page.getByTestId('summary-operation')).toContainText('Pendiente');
  await expect(page.getByTestId('save-scope')).toBeDisabled();
  await confirmFirstSubvertical(page);
});

test('@critical bot studio reconfigura con dry run obligatorio y no deja salir con checklist rojo', async ({ page }) => {
  await loginToBotStudio(page, 'reconfigure');

  const botCards = page.locator('[data-testid^="bot-card-"]');
  await expect(botCards.first()).toBeVisible();
  await botCards.first().click();

  await expect(page.getByTestId('prepare-reconfigure')).toBeEnabled();
  await page.getByTestId('prepare-reconfigure').click();
  await expect(page.getByText(/Esto no es un ajuste menor/i)).toBeVisible();

  await page.getByTestId('run-dry-run').click();
  await expect(page.getByTestId('dry-run-step')).toBeVisible();
  await expect(page.getByText(/Prevalidación antes del apply real/i)).toBeVisible();
  await expect(page.getByTestId('continue-confirmation')).toBeDisabled();
  await expect(page.getByTestId('apply-wizard')).toBeDisabled();
  await expect(page.getByText(/Bloqueado|semáforo/i).first()).toBeVisible();
});

test('@critical bot studio reconfigura con diff, confirmación y salida hacia rollback por versiones', async ({ page }) => {
  await loginToBotStudio(page, 'reconfigure');

  const botCards = page.locator('[data-testid^="bot-card-"]');
  await expect(botCards.first()).toBeVisible();
  await botCards.first().click();

  const prepare = page.getByTestId('prepare-reconfigure');
  await expect(prepare).toBeEnabled();
  await prepare.click();

  await expect(page.getByText(/Esto no es un ajuste menor/i)).toBeVisible();
  await page.getByTestId('run-dry-run').click();
  await expect(page.getByTestId('dry-run-step')).toBeVisible();
  await expect(page.getByText(/Prevalidación antes del apply real/i)).toBeVisible();

  const gateSummary = page.getByText(/Apto para confirmar|Bloqueado/i).first();
  await expect(gateSummary).toBeVisible();
  const gateText = (await gateSummary.textContent()) || '';
  if (/Apto para confirmar/i.test(gateText)) {
    await page.getByTestId('continue-confirmation').click();
    await page.locator('input[type="checkbox"]').last().check();
    await page.getByTestId('apply-wizard').click();

    await expect(page.getByTestId('publish-step')).toBeVisible();
    await expect(page.getByTestId('simulate-step')).toBeVisible();
    await page.getByRole('link', { name: /Revisar versiones/i }).click();
    await expect(page).toHaveURL(/\/versions/);
    await expect(page.getByText(/Historial de builds|Cambios detectados/i).first()).toBeVisible();
  }
});
