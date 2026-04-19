"use server";
import { redirect } from "next/navigation";
import { getCurrentOrganizationId } from "../lib/session";
import { postJson, runAndRefresh, withActionError } from "./shared";

export async function generateExecutiveReportAction(formData: FormData) {
  const organizationId = (await getCurrentOrganizationId()) || String(formData.get("organization_id") || "").trim();
  const periodStart = String(formData.get("period_start") || "").trim();
  const periodEnd = String(formData.get("period_end") || "").trim();
  const botId = String(formData.get("bot_id") || "").trim() || null;
  const redirectTo = String(formData.get("redirect_to") || "/insights").trim() || "/insights";
  const result = await runAndRefresh(redirectTo, () => postJson('/api/v1/reports/executive/generate', { organization_id: organizationId, period_start: periodStart, period_end: periodEnd, bot_id: botId, delivery_channels: ["ui"] }));
  if (!result.ok) redirect(withActionError(redirectTo, result.error, "No se pudo generar el reporte ejecutivo."));
}
