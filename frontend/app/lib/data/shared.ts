import { ApiRequestError, apiFetchOrDefault, apiFetchResult, recordApiFallback } from "../api";
import { normalizeCollection } from "../contracts/shared";
import { getCurrentBotId, getCurrentOrganizationId } from "../session";

export type LooseRecord = Record<string, unknown>;

export type PortalModuleState<T> = {
  ok: boolean;
  data: T;
  error: ApiRequestError | null;
  endpoint: string;
};

export async function orgQuery(): Promise<string> {
  const organizationId = await getCurrentOrganizationId();
  return organizationId ? `organization_id=${encodeURIComponent(organizationId)}` : "";
}

export async function selectedBotId(botId?: string): Promise<string | null> {
  if (botId) return botId;
  return await getCurrentBotId();
}

export async function fetchArray<T>(path: string, fallback: unknown[], normalizeItem: (value: unknown) => T): Promise<T[]> {
  const raw = await apiFetchOrDefault<unknown>(path, fallback, { fallbackReason: `non-critical collection fallback for ${path}` });
  return normalizeCollection(raw, normalizeItem);
}

export async function fetchRecord<T>(path: string, fallback: unknown, normalizeItem: (value: unknown) => T): Promise<T> {
  const raw = await apiFetchOrDefault<unknown>(path, fallback, { fallbackReason: `non-critical record fallback for ${path}` });
  return normalizeItem(raw);
}

export function normalizeLooseRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

export function portalDisabledState<T>(data: T, endpoint: string): PortalModuleState<T> {
  return { ok: true, data, error: null, endpoint };
}

export async function fetchArrayState<T>(endpoint: string, fallback: unknown[], normalizeItem: (value: unknown) => T): Promise<PortalModuleState<T[]>> {
  const result = await apiFetchResult<unknown>(endpoint);
  if (!result.ok) {
    await recordApiFallback(endpoint, result.error, { reason: `operator-visible collection degradation for ${endpoint}`, severity: "operator_visible" });
    return { ok: false, data: normalizeCollection(fallback, normalizeItem), error: result.error, endpoint };
  }
  return { ok: true, data: normalizeCollection(result.data, normalizeItem), error: null, endpoint };
}

export async function fetchRecordState<T>(endpoint: string, fallback: unknown, normalizeItem: (value: unknown) => T): Promise<PortalModuleState<T>> {
  const result = await apiFetchResult<unknown>(endpoint);
  if (!result.ok) {
    await recordApiFallback(endpoint, result.error, { reason: `operator-visible record degradation for ${endpoint}`, severity: "operator_visible" });
    return { ok: false, data: normalizeItem(fallback), error: result.error, endpoint };
  }
  return { ok: true, data: normalizeItem(result.data), error: null, endpoint };
}

export function hasModuleFailures(states: Array<PortalModuleState<unknown>>): boolean {
  return states.some((state) => !state.ok);
}
