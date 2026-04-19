"use server";
import { postJson, readString, runAndRefresh } from "./shared";

export async function createAgendaResourceAction(formData: FormData) {
  const organizationId = readString(formData, "organization_id");
  const redirectTo = readString(formData, "redirect_to") || "/agenda";
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/agenda/resources`, {
    organization_id: organizationId,
    bot_id: readString(formData, "bot_id") || null,
    name: readString(formData, "name"),
    resource_type: readString(formData, "resource_type") || "professional",
    branch: readString(formData, "branch") || null,
  }));
}

export async function createAgendaCapacityRuleAction(formData: FormData) {
  const organizationId = readString(formData, "organization_id");
  const redirectTo = readString(formData, "redirect_to") || "/agenda";
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/agenda/capacity-rules`, {
    organization_id: organizationId,
    bot_id: readString(formData, "bot_id") || null,
    resource_id: readString(formData, "resource_id"),
    day_of_week: Number(readString(formData, "day_of_week") || 1),
    start_time: readString(formData, "start_time") || "09:00",
    end_time: readString(formData, "end_time") || "18:00",
    slot_capacity: Number(readString(formData, "slot_capacity") || 1),
  }));
}
