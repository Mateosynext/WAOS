import { test, expect } from '@playwright/test';
import { chooseOrganization, currentCodeFromSecret, login, readSeedSecrets, submitLogin } from './helpers.real';
const seeds = readSeedSecrets();
async function loginAsRealAdmin(page: import('@playwright/test').Page) {
  await login(page, seeds.mfa_user_email, seeds.mfa_user_password);
  await submitLogin(page);
  await expect(page.getByText(/Confirma con MFA/i)).toBeVisible();
  await page.getByLabel('Código MFA').fill(currentCodeFromSecret(seeds.mfa_user_secret));
  await submitLogin(page);
  await expect(page).toHaveURL(/\/organizations/);
  await chooseOrganization(page, 'org_1');
}
test('@critical genera reporte real y descarga PDF desde backend vivo', async ({ page }) => {
  await loginAsRealAdmin(page);
  await page.goto('/insights');
  await expect(page.getByText(/Generar reporte ejecutivo/i)).toBeVisible();
  await page.getByRole('button', { name: /Generar PDF/i }).click();
  await expect(page.getByText(/rep_/i)).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: /Descargar PDF/i }).first().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
});
test('@critical cubre release gating real desde frontend con backend vivo', async ({ page }) => {
  page.on('dialog', (dialog) => dialog.accept());
  await loginAsRealAdmin(page);
  await page.goto('/releases?stage=all&bot_id=bot_1');
  await expect(page.getByText(/Checklist de salida/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /Solicitar release/i })).toBeVisible();
  await page.getByLabel('Título de release').fill('Release real Playwright');
  await page.getByRole('button', { name: /Solicitar release/i }).click();
  await expect(page.getByRole('button', { name: /Aprobar/i }).first()).toBeVisible();
  await page.getByRole('button', { name: /Aprobar/i }).first().click();
  await expect(page.getByText('approved')).toBeVisible();
  await page.getByRole('button', { name: /Publicar/i }).first().click();
  await expect(page.getByText('published')).toBeVisible();
});
