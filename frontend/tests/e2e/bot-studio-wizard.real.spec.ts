import { expect, test, type Page } from '@playwright/test';
import { chooseOrganization, currentCodeFromSecret, login, readSeedSecrets, submitLogin } from './helpers.real';

const seeds = readSeedSecrets();

async function loginToBotStudio(page: Page, mode: 'create' | 'reconfigure' = 'create', options?: { chooseShellOrg?: boolean }) {
  await login(page, seeds.mfa_user_email, seeds.mfa_user_password);
  await submitLogin(page);
  await page.getByLabel('Código MFA').fill(currentCodeFromSecret(seeds.mfa_user_secret));
  await submitLogin(page);
  if (options?.chooseShellOrg !== false) await chooseOrganization(page, 'org_1');
  await page.goto(`/bot-studio?mode=${mode}`);
  await expect(page.getByTestId('sticky-summary-rail')).toBeVisible();
  if (mode === 'create') {
    await expect(page.getByTestId('vertical-picker')).toBeVisible();
  } else {
    await expect(page.getByTestId('reconfigure-select-step')).toBeVisible();
  }
}

async function chooseOrganizationInWizard(page: Page) {
  const select = page.getByTestId('organization-select');
  await expect(select).toBeVisible();
  const currentValue = await select.inputValue();
  if (currentValue) return currentValue;
  const options = await select.locator('option').evaluateAll((nodes: Element[]) => nodes.map((node) => ({
    value: (node as HTMLOptionElement).value,
    disabled: (node as HTMLOptionElement).disabled,
  })));
  const nextOption = options.find((item) => item.value && !item.disabled);
  expect(nextOption?.value).toBeTruthy();
  await select.selectOption(nextOption!.value);
  return nextOption!.value;
}

async function chooseFirstBotForReconfigure(page: Page) {
  const select = page.getByTestId('reconfigure-bot-select');
  await expect(select).toBeVisible();
  const options = await select.locator('option').evaluateAll((nodes: Element[]) => nodes.map((node) => ({
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
  await expect(page.getByTestId('save-scope')).toBeEnabled();
}

test('@critical bot studio no usa defaults silenciosos en create y exige confirmación explícita', async ({ page }: { page: Page }) => {
  await loginToBotStudio(page, 'create');

  await expect(page.getByTestId('organization-select')).toHaveValue('');
  await expect(page.getByTestId('save-scope')).toBeDisabled();
  await page.locator('[data-testid^="vertical-card-"]').first().click();
  await expect(page.getByText(/falta pulsar “usar esta industria”|preview/i)).toBeVisible();
  await expect(page.getByTestId('summary-industry')).toContainText('Pendiente');
  await expect(page.getByTestId('save-scope')).toBeDisabled();

  await prepareExplicitScope(page);
  await expect(page.getByTestId('summary-industry')).not.toContainText('Pendiente');
  await expect(page.getByTestId('summary-operation')).not.toContainText('Pendiente');
});

test('@critical bot studio no avanza de identidad si backend mantiene business_basics incompleto', async ({ page }: { page: Page }) => {
  await loginToBotStudio(page, 'create');
  await prepareExplicitScope(page);
  await page.getByTestId('save-scope').click();

  await expect(page).toHaveURL(/\/bot-studio\/create\/identity/);
  await expect(page.getByTestId('save-basics')).toBeDisabled();
  await page.getByTestId('business-name-input').fill(`Negocio parcial ${Date.now().toString().slice(-6)}`);
  await expect(page.getByTestId('save-basics')).toBeDisabled();

  await page.getByTestId('bot-name-input').fill(`Bot parcial ${Date.now().toString().slice(-4)}`);
  await expect(page.getByTestId('save-basics')).toBeEnabled();
  await page.getByTestId('tone-input').fill('');
  await expect(page.getByTestId('save-basics')).toBeDisabled();
});

test('@critical bot studio crea un asistente operativo con rutas separadas y validación antes del apply', async ({ page }: { page: Page }) => {
  await loginToBotStudio(page, 'create');
  await prepareExplicitScope(page);

  const suffix = Date.now().toString().slice(-6);
  await page.getByTestId('save-scope').click();
  await expect(page).toHaveURL(/\/bot-studio\/create\/identity/);

  await page.getByTestId('business-name-input').fill(`Negocio QA ${suffix}`);
  await page.getByTestId('bot-name-input').fill(`Asistente QA ${suffix}`);
  if (!((await page.getByTestId('tone-input').inputValue()).trim())) {
    await page.getByTestId('tone-input').fill('amable');
  }
  if (!((await page.getByTestId('timezone-input').inputValue()).trim())) {
    await page.getByTestId('timezone-input').fill('America/Mexico_City');
  }
  await page.getByTestId('save-basics').click();

  await expect(page).toHaveURL(/\/bot-studio\/create\/offer/);
  const services = page.getByTestId('services-textarea');
  if (!((await services.inputValue()).trim())) {
    await services.fill('Consulta inicial\nSeguimiento');
  }
  const ctas = page.getByTestId('primary-ctas-textarea');
  if (!((await ctas.inputValue()).trim())) {
    await ctas.fill('Agendar valoración');
  }
  await page.getByTestId('save-offer').click();

  await expect(page).toHaveURL(/\/bot-studio\/create\/knowledge/);
  const faq = page.getByTestId('faq-textarea');
  if (!((await faq.inputValue()).trim())) {
    await faq.fill('Atienden sábados? | Sí');
  }
  const policies = page.getByTestId('policies-textarea');
  if (!((await policies.inputValue()).trim())) {
    await policies.fill('No prometer diagnóstico sin valoración');
  }
  const sources = page.getByTestId('knowledge-sources-textarea');
  if (!((await sources.inputValue()).trim())) {
    await sources.fill('Drive operativa');
  }
  await page.getByTestId('save-knowledge').click();

  await expect(page).toHaveURL(/\/bot-studio\/create\/integrations/);
  const escalate = page.getByTestId('escalate-when-textarea');
  if (!((await escalate.inputValue()).trim())) {
    await escalate.fill('Urgencia\nReclamo');
  }
  await page.getByTestId('save-integrations').click();

  await expect(page).toHaveURL(/\/bot-studio\/create\/review/);
  await page.getByTestId('save-review').click();

  await expect(page).toHaveURL(/\/bot-studio\/create\/validate/);
  await expect(page.getByTestId('validate-step')).toBeVisible();
  await page.getByTestId('run-dry-run').click();
  await expect(page.getByText(/dry run listo|dry run completado/i)).toBeVisible();
  await expect(page.getByTestId('continue-to-apply')).toBeEnabled();
  await page.getByTestId('continue-to-apply').click();

  await expect(page).toHaveURL(/\/bot-studio\/create\/apply/);
  await expect(page.getByTestId('apply-step')).toBeVisible();
  await page.getByTestId('apply-wizard').click();

  await expect(page).toHaveURL(/\/bot-studio\/create\/success/);
  await expect(page.getByTestId('success-step')).toBeVisible();
});

test('@critical bot studio reconfigure bloquea avance sin bot explícito y refleja el gate real del dry run', async ({ page }: { page: Page }) => {
  await loginToBotStudio(page, 'reconfigure');
  await expect(page.getByTestId('prepare-reconfigure')).toBeDisabled();

  await chooseFirstBotForReconfigure(page);
  await expect(page.getByTestId('prepare-reconfigure')).toBeEnabled();
  await page.getByTestId('prepare-reconfigure').click();

  await expect(page).toHaveURL(/\/bot-studio\/reconfigure\/diff/);
  await expect(page.getByTestId('diff-step')).toBeVisible();
  await page.getByTestId('continue-diff').click();

  await expect(page).toHaveURL(/\/bot-studio\/reconfigure\/dry-run/);
  await expect(page.getByTestId('dry-run-step')).toBeVisible();
  await page.getByTestId('run-dry-run').click();

  const continueButton = page.getByTestId('continue-confirmation');
  const gateText = await page.locator('body').textContent();
  if (/apto para confirmar|lista para apply|ya puede pasar a confirmación/i.test(gateText || '')) {
    await expect(continueButton).toBeEnabled();
    await continueButton.click();
    await expect(page).toHaveURL(/\/bot-studio\/reconfigure\/confirm/);
    await expect(page.getByTestId('confirm-step')).toBeVisible();
    await expect(page.getByTestId('apply-wizard')).toBeEnabled();
  } else {
    await expect(continueButton).toBeDisabled();
  }
});
