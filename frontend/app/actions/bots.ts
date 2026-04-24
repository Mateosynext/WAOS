"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { getBot } from "@/app/lib/data/bots";
import { BOT_COOKIE, ORG_COOKIE, cookies, normalizeActionError, patchJson, postJson, readString, runAndRefresh, sessionCookieOptions, withActionError } from "./shared";

export type BotStudioActionState = {
  ok: boolean;
  error?: string;
  warning?: string;
  success?: string;
  botId?: string;
  organizationId?: string;
  redirectTo?: string;
  snapshotCreated?: boolean;
};

function readBoolean(formData: FormData, key: string) {
  const value = String(formData.get(key) || "").toLowerCase();
  return ["on", "true", "1", "yes"].includes(value);
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? { ...(value as Record<string, unknown>) } : {};
}

async function setScopeCookies(organizationId?: string, botId?: string) {
  const store = await cookies();
  const options = sessionCookieOptions.scope();
  if (organizationId) store.set(ORG_COOKIE, organizationId, options);
  if (botId) store.set(BOT_COOKIE, botId, options);
}

async function syncOrganizationVertical(organizationId: string, vertical: string, subvertical: string) {
  if (!organizationId || !vertical) return;
  await patchJson(`/api/v1/organizations/${organizationId}`, {
    vertical,
    subvertical: subvertical || null,
  });
}

async function applySubverticalPack(organizationId: string, botId: string, vertical: string, subvertical: string) {
  if (!organizationId || !botId || !vertical || !subvertical) return;
  await postJson(`/api/v1/verticals/apply-subvertical-pack`, {
    organization_id: organizationId,
    bot_id: botId,
    vertical,
    subvertical,
  });
}

async function createDraftSnapshot(botId: string, notes: string) {
  if (!botId) return;
  await postJson(`/api/v1/bots/${botId}/versions/draft-snapshot`, { notes });
}

function buildRedirectTarget(redirectTo: string, botId?: string) {
  const base = redirectTo || "/bot-studio";
  const url = new URL(base, "http://localhost");
  if (url.pathname === "/bot-studio") {
    url.searchParams.set("mode", "reconfigure");
    if (botId) url.searchParams.set("bot", botId);
  }
  return `${url.pathname}${url.search}`;
}

function refreshWorkspace(paths: Array<string | null | undefined>) {
  for (const path of Array.from(new Set(paths.filter(Boolean) as string[]))) {
    revalidatePath(path.split("?")[0]);
  }
}

const initialBotStudioState: BotStudioActionState = { ok: false };

export async function createBotAction(formData: FormData): Promise<void>;
export async function createBotAction(previousState: BotStudioActionState | undefined, formData: FormData): Promise<BotStudioActionState>;
export async function createBotAction(
  previousStateOrFormData: BotStudioActionState | FormData | undefined = initialBotStudioState,
  maybeFormData?: FormData,
): Promise<BotStudioActionState | void> {
  const stateful = !(previousStateOrFormData instanceof FormData);
  const formData = previousStateOrFormData instanceof FormData ? previousStateOrFormData : maybeFormData;
  if (!formData) return initialBotStudioState;
  const organizationId = readString(formData, "organization_id");
  const businessName = readString(formData, "business_name");
  const botName = readString(formData, "bot_name");
  const vertical = readString(formData, "vertical");
  const subvertical = readString(formData, "subvertical");
  const primaryObjective = readString(formData, "primary_objective") || "agendar";
  const tone = readString(formData, "tone") || "amable";
  const language = readString(formData, "language") || "es";
  const timezone = readString(formData, "timezone") || "America/Mexico_City";
  const whatsappNumber = readString(formData, "whatsapp_number");
  const hours = readString(formData, "hours");
  const redirectTo = readString(formData, "redirect_to") || "/bot-studio";
  const publishNow = readBoolean(formData, "publish_now");
  let createdBotId = "";

  try {
    await setScopeCookies(organizationId);
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

    createdBotId = String(created.id || "");
    await setScopeCookies(organizationId, createdBotId);
    await syncOrganizationVertical(organizationId, vertical, subvertical);
    await applySubverticalPack(organizationId, createdBotId, vertical, subvertical);

    const successTarget = buildRedirectTarget(redirectTo, createdBotId);
    refreshWorkspace([
      "/bot-studio",
      "/bots",
      createdBotId ? `/bots/${createdBotId}` : null,
      "/organizations",
      "/onboarding",
      "/inbox",
      "/agenda",
      "/business-hub",
      successTarget,
    ]);

    const result: BotStudioActionState = {
      ok: true,
      success: publishNow
        ? "Bot creado y draft inicial publicado sin salir del wizard."
        : "Bot creado dentro del wizard. Ahora puedes conectar canal, revisar o publicar.",
      botId: createdBotId,
      organizationId,
      redirectTo: successTarget,
    };
    if (!stateful) redirect(successTarget);
    return result;
  } catch (error) {
    const failureTarget = buildRedirectTarget(redirectTo, createdBotId || undefined);
    const result: BotStudioActionState = {
      ok: false,
      error: normalizeActionError(
        error,
        createdBotId
          ? "Se creó el bot, pero no se pudo terminar de conectar la vertical."
          : "No se pudo crear el bot.",
      ),
      botId: createdBotId || undefined,
      organizationId,
      redirectTo: failureTarget,
    };
    if (!stateful) redirect(withActionError(failureTarget, result.error, result.error));
    return result;
  }
}

export async function applyBotVerticalAction(formData: FormData): Promise<void>;
export async function applyBotVerticalAction(previousState: BotStudioActionState | undefined, formData: FormData): Promise<BotStudioActionState>;
export async function applyBotVerticalAction(
  previousStateOrFormData: BotStudioActionState | FormData | undefined = initialBotStudioState,
  maybeFormData?: FormData,
): Promise<BotStudioActionState | void> {
  const stateful = !(previousStateOrFormData instanceof FormData);
  const formData = previousStateOrFormData instanceof FormData ? previousStateOrFormData : maybeFormData;
  if (!formData) return initialBotStudioState;
  const botId = readString(formData, "bot_id");
  const organizationId = readString(formData, "organization_id");
  const vertical = readString(formData, "vertical");
  const subvertical = readString(formData, "subvertical");
  const primaryObjective = readString(formData, "primary_objective") || "agendar";
  const redirectTo = readString(formData, "redirect_to") || "/bot-studio";
  const reviewRequired = readBoolean(formData, "review_required");
  const reviewConfirmed = readBoolean(formData, "review_confirmed");
  const successTarget = buildRedirectTarget(redirectTo, botId);

  try {
    if (reviewRequired && !reviewConfirmed) {
      return {
        ok: false,
        error: "Antes de aplicar esta reconfiguración debes revisar el impacto y confirmar la aplicación.",
        botId,
        organizationId,
        redirectTo: successTarget,
      };
    }

    await setScopeCookies(organizationId, botId);
    const bot = await getBot(botId);
    const configDraft = asRecord(bot.config_draft);
    const identity = asRecord(configDraft.identity);
    const objective = asRecord(configDraft.objective);

    identity.vertical = vertical;
    objective.primary = primaryObjective;
    if (subvertical) {
      configDraft.selected_subvertical = subvertical;
      configDraft.subvertical = subvertical;
    }

    configDraft.identity = identity;
    configDraft.objective = objective;

    await createDraftSnapshot(botId, `Snapshot preventivo antes de reconfigurar a ${vertical}${subvertical ? ` / ${subvertical}` : ""}`);

    await patchJson(`/api/v1/bots/${botId}`, {
      vertical,
      apply_vertical_defaults: true,
      config_draft: configDraft,
    });
    await syncOrganizationVertical(organizationId, vertical, subvertical);
    await applySubverticalPack(organizationId, botId, vertical, subvertical);

    const snapshotCreated = true;

    refreshWorkspace([
      "/bot-studio",
      "/bots",
      botId ? `/bots/${botId}` : null,
      "/organizations",
      "/onboarding",
      "/inbox",
      "/agenda",
      "/business-hub",
      successTarget,
    ]);

    const result: BotStudioActionState = {
      ok: true,
      success: "Snapshot preventivo creado y pack reaplicado sin salir del wizard.",
      botId,
      organizationId,
      redirectTo: successTarget,
      snapshotCreated,
    };
    if (!stateful) redirect(successTarget);
    return result;
  } catch (error) {
    const result: BotStudioActionState = {
      ok: false,
      error: normalizeActionError(error, "No se pudo reconfigurar el bot. No se aplicaron cambios si el snapshot preventivo no se pudo crear."),
      botId,
      organizationId,
      redirectTo: successTarget,
    };
    if (!stateful) redirect(withActionError(successTarget, result.error, result.error));
    return result;
  }
}

export async function pauseBotAction(formData: FormData) { const botId = readString(formData, "bot_id"); const redirectTo = readString(formData, "redirect_to") || `/bots/${botId}`; const result = await runAndRefresh(redirectTo, () => postJson(`/api/v1/bots/${botId}/pause`, {})); redirect(result.ok ? redirectTo : withActionError(redirectTo, result.error, "No se pudo pausar el bot.")); }
export async function resumeBotAction(formData: FormData) { const botId = readString(formData, "bot_id"); const redirectTo = readString(formData, "redirect_to") || `/bots/${botId}`; const result = await runAndRefresh(redirectTo, () => postJson(`/api/v1/bots/${botId}/resume`, {})); redirect(result.ok ? redirectTo : withActionError(redirectTo, result.error, "No se pudo reanudar el bot.")); }
export async function publishBotAction(formData: FormData) { const botId = readString(formData, "bot_id"); const notes = readString(formData, "notes"); const redirectTo = readString(formData, "redirect_to") || `/bots/${botId}`; const result = await runAndRefresh(redirectTo, () => postJson(`/api/v1/bots/${botId}/publish`, { notes })); redirect(result.ok ? redirectTo : withActionError(redirectTo, result.error, "No se pudo publicar el bot.")); }
