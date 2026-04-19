"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { apiFetchResult } from "../lib/api";
import { getCurrentOrganizationId } from "../lib/session";
import { withActionError } from "./shared";

function redirectTo(formData: FormData, fallback: string) {
  const value = formData.get("redirect_to");
  return typeof value === "string" && value ? value : fallback;
}

export async function saveInboxViewAction(formData: FormData) {
  const target = redirectTo(formData, "/inbox");
  const organizationId = String(formData.get("organization_id") || await getCurrentOrganizationId() || "").trim();
  const name = String(formData.get("name") || "").trim();
  const filtersRaw = String(formData.get("filters") || "{}");
  const isDefault = String(formData.get("is_default") || "0") === "1";
  if (!organizationId || !name) redirect(target);
  let filters: Record<string, unknown> = {};
  try { filters = JSON.parse(filtersRaw); } catch { filters = {}; }
  const result = await apiFetchResult("/api/v1/inbox/saved-views", { method: "POST", body: JSON.stringify({ organization_id: organizationId, name, filters, is_default: isDefault }) });
  if (!result.ok) redirect(withActionError(target, result.error, "No se pudo guardar la vista del inbox."));
  revalidatePath("/inbox");
  redirect(target);
}
