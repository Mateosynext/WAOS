import { test, expect } from '@playwright/test';
import { chooseOrganization, currentCodeFromSecret, login, readSeedSecrets, submitLogin } from './helpers.real';
const seeds = readSeedSecrets();
test('carga integraciones reales con backend vivo y muestra providers conectados', async ({ page }) => {
  await login(page, seeds.mfa_user_email, seeds.mfa_user_password);
  await submitLogin(page);
  await page.getByLabel('Código MFA').fill(currentCodeFromSecret(seeds.mfa_user_secret));
  await submitLogin(page);
  await chooseOrganization(page, 'org_1');
  await page.goto('/integrations');
  await expect(page.getByText(/Pagos pendientes|Google Calendar|Stripe/i).first()).toBeVisible();
  await expect(page.getByText(/Google Calendar/i)).toBeVisible();
  await expect(page.getByText(/Stripe/i)).toBeVisible();
});
