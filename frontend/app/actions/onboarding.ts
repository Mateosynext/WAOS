"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { apiFetch } from "../lib/api";
import { getCurrentOrganizationId } from "../lib/session";

function redirectTo(formData: FormData, fallback: string) {
  const value = formData.get("redirect_to");
  return typeof value === "string" && value ? value : fallback;
}

export async function setTenantModeAction(formData: FormData) {
  const organizationId = String(formData.get("organization_id") || await getCurrentOrganizationId() || "").trim();
  const tenantMode = String(formData.get("tenant_mode") || "sandbox").trim();
  if (!organizationId) redirect(redirectTo(formData, "/onboarding"));
  await apiFetch("/api/v1/onboarding/tenant-mode", { method: "POST", body: JSON.stringify({ organization_id: organizationId, tenant_mode: tenantMode }) });
  revalidatePath("/onboarding");
  redirect(redirectTo(formData, "/onboarding"));
}
