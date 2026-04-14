import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { expect, Page, BrowserContext, APIRequestContext } from '@playwright/test';
import { parseOtpSecret, totpFromSecret } from './totp';
const apiPort = Number(process.env.PLAYWRIGHT_API_PORT || 4100);
export const backendBaseUrl = `http://127.0.0.1:${apiPort}`;
export type SeedSecrets = { owner_email: string; owner_password: string; client_email: string; client_password: string; mfa_user_email: string; mfa_user_password: string; mfa_user_secret: string; };
export function readSeedSecrets(): SeedSecrets { return JSON.parse(fs.readFileSync(path.resolve(process.cwd(), 'tests/e2e/.real-secrets.json'), 'utf8')) as SeedSecrets; }
export async function login(page: Page, email: string, password = 'Passw0rd!') { await page.goto('/login'); await page.getByLabel('Correo').fill(email); await page.getByLabel('Contraseña').fill(password); }
export async function submitLogin(page: Page) { await page.getByRole('button', { name: /Entrar|Validar y entrar/i }).click(); }
export async function getCookieValue(context: BrowserContext, name: string): Promise<string | undefined> { const cookies = await context.cookies(); return cookies.find((item) => item.name === name)?.value; }
export async function apiHeaders(context: BrowserContext) { const token = await getCookieValue(context, 'waos_access_token'); if (!token) throw new Error('Missing waos_access_token cookie'); return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }; }
export async function apiRequest(api: APIRequestContext, context: BrowserContext, method: string, routePath: string, body?: unknown) { const headers = await apiHeaders(context); return api.fetch(`${backendBaseUrl}${routePath}`, { method, headers, data: body }); }
export async function chooseOrganization(page: Page, orgId: string) { const select = page.getByLabel('Seleccionar organización'); await expect(select).toBeVisible(); await select.selectOption(orgId); await page.waitForLoadState('networkidle'); }
export async function setBrokenAccessTokenButKeepRefresh(context: BrowserContext) { const cookies = await context.cookies(); await context.clearCookies(); await context.addCookies(cookies.map((item) => item.name === 'waos_access_token' ? { ...item, value: `expired-${crypto.randomUUID()}` } : item)); }
export function currentCodeFromUri(provisioningUri: string): string { return totpFromSecret(parseOtpSecret(provisioningUri)); }
export function currentCodeFromSecret(secret: string): string { return totpFromSecret(secret); }
export function buildStripeSignature(payload: string, secret: string, timestamp = '1710000000') { const signedPayload = `${timestamp}.${payload}`; const digest = crypto.createHmac('sha256', secret).update(signedPayload).digest('hex'); return `t=${timestamp},v1=${digest}`; }
