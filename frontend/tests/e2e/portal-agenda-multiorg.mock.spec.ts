import { test, expect } from '@playwright/test';

test('redirecciona a selector de organización y cambia el tenant visible', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Correo').fill('admin@acme.test');
  await page.getByLabel('Contraseña').fill('Passw0rd!');
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(/\/organizations/);
  await page.getByLabel('Seleccionar organización').selectOption('org_2');
  await page.goto('/agenda');
  await expect(page.getByText('Seguimiento premium')).toBeVisible();
  await expect(page.getByText('Demo comercial')).toHaveCount(0);
});

test('portal cliente muestra resumen, solicitudes y agenda con evidencia visible', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Correo').fill('client@acme.test');
  await page.getByLabel('Contraseña').fill('Passw0rd!');
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(/\/client/);
  await expect(page.getByText('Qué pasó esta semana')).toBeVisible();
  await expect(page.getByText('Solicitudes recientes')).toBeVisible();
  await page.goto('/client?section=agenda');
  await expect(page.getByText('Demo comercial')).toBeVisible();
  await page.goto('/client?section=solicitudes');
  await expect(page.getByText('Actualizar copy de bienvenida')).toBeVisible();
});
