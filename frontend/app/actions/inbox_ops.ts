"use server";

import { getCurrentOrganizationId } from "../lib/session";
import { postJson, readString, runAndRefresh } from "./shared";

export async function autoAssignInboxAction(formData: FormData) {
  const organizationId = readString(formData, "organization_id") || String(await getCurrentOrganizationId() || "").trim();
  const queueRole = readString(formData, "queue_role") || null;
  const redirectTo = readString(formData, "redirect_to") || "/inbox";
  if (!organizationId) return;
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/inbox/auto-assign`, { organization_id: organizationId, limit: 25, queue_role: queueRole }));
}

export async function assignConversationOwnerAction(formData: FormData) {
  const conversationId = readString(formData, "conversation_id");
  const assignedUserId = readString(formData, "assigned_user_id") || null;
  const mode = readString(formData, "mode") || (assignedUserId ? "manual" : "auto");
  const note = readString(formData, "note");
  const redirectTo = readString(formData, "redirect_to") || `/inbox/${conversationId}`;
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/conversations/${conversationId}/assign`, { assigned_user_id: assignedUserId, mode, note }));
}
