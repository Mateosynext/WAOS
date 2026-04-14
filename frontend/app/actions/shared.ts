import { cookies } from "next/headers";
import { apiFetch } from "../lib/api";
import { getServerApiBase } from "../lib/env";
import { ACCESS_COOKIE, BOT_COOKIE, ORG_COOKIE, REFRESH_COOKIE, sessionCookieOptions } from "../lib/session";

export const API_BASE = getServerApiBase();
export const secureCookies = process.env.NODE_ENV === "production" || process.env.SECURE_COOKIES === "true";
export type ActionState = { ok?: boolean; error?: string; data?: unknown; mfaRequired?: boolean; mfaSetupRequired?: boolean; challengeId?: string; mfaSetup?: { qrSvgDataUrl?: string; provisioningUri?: string; recoveryCodes?: string[] }; ssoProviders?: Array<Record<string, unknown>> };
export function readString(formData: FormData, key: string): string { return String(formData.get(key) || "").trim(); }
export async function postJson(path: string, body: unknown) { return apiFetch(path, { method: "POST", body: JSON.stringify(body) }); }
export async function patchJson(path: string, body: unknown) { return apiFetch(path, { method: "PATCH", body: JSON.stringify(body) }); }
export async function runAndRefresh(pathToRevalidate: string, fn: () => Promise<unknown>) { const { revalidatePath } = await import("next/cache"); await fn(); revalidatePath(pathToRevalidate); }
export { ACCESS_COOKIE, BOT_COOKIE, ORG_COOKIE, REFRESH_COOKIE, cookies, sessionCookieOptions };
