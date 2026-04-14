import { test, expect } from '@playwright/test';

test('genera un reporte desde producto y descarga el PDF', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Correo').fill('admin@acme.test');
  await page.getByLabel('Contraseña').fill('Passw0rd!');
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(/\/organizations/);
  await page.getByLabel('Seleccionar organización').selectOption('org_1');
  await page.goto('/insights');
  await expect(page.getByText('Generar reporte ejecutivo')).toBeVisible();
  await page.getByRole('button', { name: /Generar PDF/i }).click();
  await expect(page.getByText(/rep_org_1_/)).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: /Descargar PDF/i }).first().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
});
