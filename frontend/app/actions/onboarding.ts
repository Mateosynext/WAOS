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

export async function setTenantModeAction(formData: FormData) {
  const target = redirectTo(formData, "/onboarding");
  const organizationId = String(formData.get("organization_id") || await getCurrentOrganizationId() || "").trim();
  const tenantMode = String(formData.get("tenant_mode") || "sandbox").trim();
  if (!organizationId) redirect(target);
  const result = await apiFetchResult("/api/v1/onboarding/tenant-mode", { method: "POST", body: JSON.stringify({ organization_id: organizationId, tenant_mode: tenantMode }) });
  if (!result.ok) redirect(withActionError(target, result.error, "No se pudo actualizar el tenant mode."));
  revalidatePath("/onboarding");
  redirect(target);
}
