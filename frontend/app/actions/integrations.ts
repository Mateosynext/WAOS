"use server";

import { redirect } from "next/navigation";
import { postJson, readString, runAndRefresh } from "./shared";

function readOptionalString(formData: FormData, key: string): string | null {
  const value = readString(formData, key);
  return value ? value : null;
}

function readBoolean(formData: FormData, key: string): boolean {
  return String(formData.get(key) || "").toLowerCase() === "on" || String(formData.get(key) || "").toLowerCase() === "true" || String(formData.get(key) || "") === "1";
}

function readNumber(formData: FormData, key: string, fallback: number): number {
  const raw = Number(readString(formData, key));
  return Number.isFinite(raw) && raw > 0 ? raw : fallback;
}

export async function testIntegrationAction(formData: FormData) {
  const integrationId = readString(formData, "integration_id");
  const redirectTo = readString(formData, "redirect_to") || "/integrations";
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/integrations/${integrationId}/test`, {}));
}

export async function syncIntegrationAction(formData: FormData) {
  const integrationId = readString(formData, "integration_id");
  const redirectTo = readString(formData, "redirect_to") || "/integrations";
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/integrations/${integrationId}/sync`, {}));
}

export async function saveWhatsAppIntegrationAction(formData: FormData) {
  const redirectTo = readString(formData, "redirect_to") || "/integrations?section=configuracion";
  const payload = {
    organization_id: readString(formData, "organization_id"),
    bot_id: readOptionalString(formData, "bot_id"),
    name: readString(formData, "name") || "WhatsApp Cloud API",
    phone_number: readString(formData, "phone_number"),
    phone_number_id: readString(formData, "phone_number_id"),
    waba_id: readOptionalString(formData, "waba_id"),
    access_token: readOptionalString(formData, "access_token"),
    app_secret: readOptionalString(formData, "app_secret"),
    webhook_verify_token: readOptionalString(formData, "webhook_verify_token"),
    status: readString(formData, "status") || "configured",
  };
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/integrations/whatsapp/configure`, payload));
}

export async function saveGoogleCalendarIntegrationAction(formData: FormData) {
  const redirectTo = readString(formData, "redirect_to") || "/integrations?section=configuracion";
  const payload = {
    organization_id: readString(formData, "organization_id"),
    bot_id: readOptionalString(formData, "bot_id"),
    name: readString(formData, "name") || "Google Calendar",
    client_id: readString(formData, "client_id"),
    client_secret: readOptionalString(formData, "client_secret"),
    redirect_uri: readString(formData, "redirect_uri"),
    frontend_redirect_uri: readOptionalString(formData, "frontend_redirect_uri") || redirectTo,
    calendar_id: readOptionalString(formData, "calendar_id"),
    timezone: readOptionalString(formData, "timezone"),
    auto_sync_enabled: readBoolean(formData, "auto_sync_enabled"),
    sync_frequency_minutes: readNumber(formData, "sync_frequency_minutes", 30),
    status: readString(formData, "status") || "configured",
    scopes: ["openid", "email", "profile", "https://www.googleapis.com/auth/calendar"],
  };
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/integrations/google-calendar/configure`, payload));
}

export async function startGoogleOAuthAction(formData: FormData) {
  const integrationId = readString(formData, "integration_id");
  const result = await postJson(`/api/v1/integrations/${integrationId}/oauth/google/start`, {}) as { authorization_url?: string };
  redirect(String(result.authorization_url || '/integrations?section=configuracion'));
}

export async function saveStripeIntegrationAction(formData: FormData) {
  const redirectTo = readString(formData, "redirect_to") || "/integrations?section=configuracion";
  const payload = {
    organization_id: readString(formData, "organization_id"),
    bot_id: readOptionalString(formData, "bot_id"),
    name: readString(formData, "name") || "Stripe Payments",
    success_url: readString(formData, "success_url"),
    cancel_url: readString(formData, "cancel_url"),
    webhook_url: readOptionalString(formData, "webhook_url"),
    publishable_key: readOptionalString(formData, "publishable_key"),
    secret_key: readOptionalString(formData, "secret_key"),
    webhook_secret: readOptionalString(formData, "webhook_secret"),
    auto_sync_enabled: readBoolean(formData, "auto_sync_enabled"),
    sync_frequency_minutes: readNumber(formData, "sync_frequency_minutes", 10),
    status: readString(formData, "status") || "configured",
  };
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/integrations/stripe/configure`, payload));
}

export async function refreshPaymentStatusAction(formData: FormData) {
  const paymentId = readString(formData, "payment_id");
  const redirectTo = readString(formData, "redirect_to") || "/revenue";
  await runAndRefresh("/revenue", () => postJson(`/api/v1/sales/payments/${paymentId}/refresh`, {}));
  await runAndRefresh("/agenda", async () => null);
  if (redirectTo !== "/revenue") {
    await runAndRefresh(redirectTo, async () => null);
  }
}
