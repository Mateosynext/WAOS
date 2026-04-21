import { normalizeCollection } from "../contracts/shared";
import type { VerticalProfileContract } from "../contracts/verticals";
import { normalizeVerticalProfile } from "../contracts/verticals";
import { apiFetchResult } from "../api";
import { orgQuery, selectedBotId } from "./shared";
import { getFallbackVerticalCatalog, getFallbackVerticalProfile } from "../vertical-fallback";

export async function getVerticalCatalog(topOnly = false): Promise<VerticalProfileContract[]> {
  const suffix = topOnly ? "?top_only=1" : "";
  for (const path of [`/api/public/verticals${suffix}`, `/api/v1/verticals${suffix}`]) {
    const result = await apiFetchResult<unknown[]>(path);
    if (!result.ok) continue;
    const items = normalizeCollection(result.data, normalizeVerticalProfile);
    if (items.length) return items;
  }
  return getFallbackVerticalCatalog(topOnly);
}

export async function getStrongestVerticals(): Promise<VerticalProfileContract[]> {
  return getVerticalCatalog(true);
}

export async function getVerticalProfile(vertical?: string, botId?: string, subvertical?: string, organizationId?: string): Promise<VerticalProfileContract> {
  const publicParams = new URLSearchParams();
  if (vertical) publicParams.set("vertical", vertical);
  if (subvertical) publicParams.set("subvertical", subvertical);
  const publicPath = `/api/public/verticals/profile${publicParams.toString() ? `?${publicParams.toString()}` : ""}`;
  const publicResult = await apiFetchResult<unknown>(publicPath);
  if (publicResult.ok) {
    const profile = normalizeVerticalProfile(publicResult.data);
    if (profile.id) return profile;
  }

  const query = organizationId ? `organization_id=${encodeURIComponent(organizationId)}` : await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const params = [query];
  if (vertical) params.push(`vertical=${encodeURIComponent(vertical)}`);
  if (subvertical) params.push(`subvertical=${encodeURIComponent(subvertical)}`);
  if (currentBotId) params.push(`bot_id=${encodeURIComponent(currentBotId)}`);
  const qs = params.filter(Boolean).join("&");
  if (qs) {
    const result = await apiFetchResult<unknown>(`/api/v1/verticals/profile?${qs}`);
    if (result.ok) {
      const profile = normalizeVerticalProfile(result.data);
      if (profile.id) return profile;
    }
  }
  return getFallbackVerticalProfile(vertical, subvertical);
}
