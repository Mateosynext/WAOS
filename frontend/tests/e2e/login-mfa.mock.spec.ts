import { test, expect } from '@playwright/test';

async function login(page: import('@playwright/test').Page, email: string, password = 'Passw0rd!') {
  await page.goto('/login');
  await page.getByLabel('Correo').fill(email);
  await page.getByLabel('Contraseña').fill(password);
}

test('cubre descubrimiento SSO y challenge MFA', async ({ page }) => {
  await login(page, 'sso@enterprise.test');
  await page.getByLabel('Correo').blur();
  await expect(page.getByRole('link', { name: /Entrar con SSO Acme/i })).toBeVisible();
  await login(page, 'mfa@acme.test');
  await page.getByRole('button', { name: /Entrar/i }).click();
  await expect(page.getByText(/Confirma con MFA/i)).toBeVisible();
  await page.getByLabel('Código MFA').fill('123456');
  await page.getByRole('button', { name: /Validar y entrar/i }).click();
  await expect(page).toHaveURL(/client|organizations|\/$/);
});

test('muestra onboarding MFA setup real desde login', async ({ page }) => {
  await login(page, 'setup@acme.test');
  await page.getByRole('button', { name: /Entrar/i }).click();
  await expect(page.getByText(/Activa MFA para continuar/i)).toBeVisible();
  await expect(page.getByAltText('QR MFA')).toBeVisible();
  await page.getByLabel('Código inicial de MFA').fill('123456');
  await page.getByRole('button', { name: /Validar y entrar/i }).click();
  await expect(page).toHaveURL(/client|organizations|\/$/);
});

test('recupera sesión con refresh token cuando el access token expira', async ({ context, page, baseURL }) => {
  const url = new URL(baseURL || 'http://127.0.0.1:3000');
  await context.addCookies([
    { name: 'waos_access_token', value: 'expired-once', domain: url.hostname, path: '/' },
    { name: 'waos_refresh_token', value: 'refresh-admin', domain: url.hostname, path: '/' },
    { name: 'waos_org_id', value: 'org_1', domain: url.hostname, path: '/' },
  ]);
  await page.goto('/agenda');
  await expect(page.getByText('Agenda')).toBeVisible();
  await expect(page.getByText('Demo comercial')).toBeVisible();
});
