import { cookies } from "next/headers";
import { ApiRequestError, apiFetch } from "../lib/api";
import { getServerApiBase } from "../lib/env";
import { ACCESS_COOKIE, BOT_COOKIE, ORG_COOKIE, REFRESH_COOKIE, sessionCookieOptions } from "../lib/session";

export const API_BASE = getServerApiBase();
export const secureCookies = process.env.NODE_ENV === "production" || process.env.SECURE_COOKIES === "true";
export type ActionState = { ok?: boolean; error?: string; data?: unknown; mfaRequired?: boolean; mfaSetupRequired?: boolean; challengeId?: string; mfaSetup?: { qrSvgDataUrl?: string; provisioningUri?: string; recoveryCodes?: string[] }; ssoProviders?: Array<Record<string, unknown>> };
export type ActionRunResult<T = unknown> = { ok: true; data: T; error: null } | { ok: false; data: null; error: string };

export function readString(formData: FormData, key: string): string { return String(formData.get(key) || "").trim(); }

export function normalizeActionError(error: unknown, fallback = "No se pudo completar la acción."): string {
  if (error instanceof ApiRequestError) return error.message || fallback;
  if (error instanceof Error) return error.message || fallback;
  if (typeof error === "string" && error.trim()) return error.trim();
  return fallback;
}

export function withActionError(redirectTo: string, error: unknown, fallback?: string): string {
  const message = normalizeActionError(error, fallback);
  const [pathname, query = ""] = redirectTo.split("?", 2);
  const params = new URLSearchParams(query);
  params.set("error", message);
  return params.toString() ? `${pathname}?${params.toString()}` : pathname;
}

export async function postJson(path: string, body: unknown) { return apiFetch(path, { method: "POST", body: JSON.stringify(body) }); }
export async function patchJson(path: string, body: unknown) { return apiFetch(path, { method: "PATCH", body: JSON.stringify(body) }); }
export async function runAndRefresh<T = unknown>(pathToRevalidate: string, fn: () => Promise<T>): Promise<ActionRunResult<T>> {
  const { revalidatePath } = await import("next/cache");
  try {
    const data = await fn();
    revalidatePath(pathToRevalidate);
    return { ok: true, data, error: null };
  } catch (error) {
    return { ok: false, data: null, error: normalizeActionError(error) };
  }
}
export { ACCESS_COOKIE, BOT_COOKIE, ORG_COOKIE, REFRESH_COOKIE, cookies, sessionCookieOptions };
