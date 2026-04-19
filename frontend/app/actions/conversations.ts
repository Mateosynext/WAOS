"use server";

import { postJson, readString, runAndRefresh } from "./shared";

function parseOptionalJson(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  try {
    return JSON.parse(trimmed);
  } catch {
    throw new Error("whatsapp_payload_invalid_json");
  }
}

export async function sendConversationMessageAction(formData: FormData) {
  const conversationId = readString(formData, "conversation_id");
  const body = readString(formData, "body");
  const kind = readString(formData, "kind") || "text";
  const whatsappPayloadRaw = readString(formData, "whatsapp_payload");
  const redirectTo = readString(formData, "redirect_to") || `/inbox/${conversationId}`;
  await runAndRefresh(redirectTo, () =>
    postJson(`/api/v1/conversations/${conversationId}/messages`, {
      body,
      kind,
      whatsapp_payload: parseOptionalJson(whatsappPayloadRaw),
    }),
  );
}

export async function takeoverConversationAction(formData: FormData) {
  const conversationId = readString(formData, "conversation_id");
  const freezeMinutes = Number(readString(formData, "freeze_minutes") || 30);
  const redirectTo = readString(formData, "redirect_to") || `/inbox/${conversationId}`;
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/conversations/${conversationId}/takeover`, { freeze_minutes: freezeMinutes }));
}

export async function reactivateConversationAction(formData: FormData) {
  const conversationId = readString(formData, "conversation_id");
  const redirectTo = readString(formData, "redirect_to") || `/inbox/${conversationId}`;
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/conversations/${conversationId}/reactivate-ai`, {}));
}
