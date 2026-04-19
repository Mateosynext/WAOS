"use server";
import { redirect } from "next/navigation";
import { patchJson, readString, runAndRefresh, withActionError } from "./shared";

export async function updateOrganizationVerticalAction(formData: FormData) {
  const organizationId = readString(formData, "organization_id");
  const vertical = readString(formData, "vertical");
  const subvertical = readString(formData, "subvertical");
  const redirectTo = readString(formData, "redirect_to") || "/organizations";
  const result = await runAndRefresh(redirectTo, () => patchJson(`/api/v1/organizations/${organizationId}`, { vertical, subvertical: subvertical || null }));
  redirect(result.ok ? redirectTo : withActionError(redirectTo, result.error, "No se pudo actualizar la organización."));
}
