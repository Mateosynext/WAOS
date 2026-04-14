"use server";
import { redirect } from "next/navigation";
import { BOT_COOKIE, cookies, patchJson, postJson, readString, runAndRefresh, secureCookies } from "./shared";

function readBoolean(formData: FormData, key: string) {
  const value = String(formData.get(key) || "").toLowerCase();
  return ["on", "true", "1", "yes"].includes(value);
}

export async function createBotAction(formData: FormData) {
  const organizationId = readString(formData, "organization_id");
  const businessName = readString(formData, "business_name");
  const botName = readString(formData, "bot_name");
  const vertical = readString(formData, "vertical");
  const primaryObjective = readString(formData, "primary_objective") || "agendar";
  const tone = readString(formData, "tone") || "amable";
  const language = readString(formData, "language") || "es";
  const timezone = readString(formData, "timezone") || "America/Mexico_City";
  const whatsappNumber = readString(formData, "whatsapp_number");
  const hours = readString(formData, "hours");
  const redirectTo = readString(formData, "redirect_to");
  const publishNow = readBoolean(formData, "publish_now");
  const created = await postJson(`/api/v1/bots`, {
    organization_id: organizationId,
    business_name: businessName,
    vertical,
    bot_name: botName,
    primary_objective: primaryObjective,
    tone,
    language,
    timezone,
    services: [],
    hours,
    faqs: [],
    whatsapp_number: whatsappNumber,
    publish_now: publishNow,
  }) as Record<string, unknown>;
  const botId = String(created.id || "");
  const store = await cookies();
  if (botId) store.set(BOT_COOKIE, botId, { httpOnly: true, sameSite: "lax", secure: secureCookies, path: "/" });
  await runAndRefresh("/bot-studio", async () => null);
  await runAndRefresh("/bots", async () => null);
  if (redirectTo) {
    await runAndRefresh(redirectTo, async () => null);
    redirect(redirectTo);
  }
  redirect(botId ? `/bots/${botId}` : "/bots");
}

export async function applyBotVerticalAction(formData: FormData) {
  const botId = readString(formData, "bot_id");
  const vertical = readString(formData, "vertical");
  const redirectTo = readString(formData, "redirect_to") || `/bots/${botId}`;
  await runAndRefresh(redirectTo, () => patchJson(`/api/v1/bots/${botId}`, { vertical, apply_vertical_defaults: true }));
  redirect(redirectTo);
}

export async function pauseBotAction(formData: FormData) { const botId = readString(formData, "bot_id"); const redirectTo = readString(formData, "redirect_to") || `/bots/${botId}`; await runAndRefresh(redirectTo, () => postJson(`/api/v1/bots/${botId}/pause`, {})); }
export async function resumeBotAction(formData: FormData) { const botId = readString(formData, "bot_id"); const redirectTo = readString(formData, "redirect_to") || `/bots/${botId}`; await runAndRefresh(redirectTo, () => postJson(`/api/v1/bots/${botId}/resume`, {})); }
export async function publishBotAction(formData: FormData) { const botId = readString(formData, "bot_id"); const notes = readString(formData, "notes"); const redirectTo = readString(formData, "redirect_to") || `/bots/${botId}`; await runAndRefresh(redirectTo, () => postJson(`/api/v1/bots/${botId}/publish`, { notes })); }
