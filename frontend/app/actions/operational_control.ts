"use server";

import { postJson, readString, runAndRefresh } from "./shared";

export async function createAuthorizedOperationalNumberAction(formData: FormData) {
  const organizationId = readString(formData, "organization_id");
  const botId = readString(formData, "bot_id");
  const redirectTo = readString(formData, "redirect_to") || "/client/operaciones";
  const allowedIntentsRaw = readString(formData, "allowed_intents");
  await runAndRefresh(redirectTo, () =>
    postJson(`/api/v1/client/operations/authorized-numbers`, {
      organization_id: organizationId,
      bot_id: botId,
      phone_e164: readString(formData, "phone_e164"),
      role: readString(formData, "role") || "owner",
      allowed_intents: allowedIntentsRaw ? allowedIntentsRaw.split(",").map((item) => item.trim()).filter(Boolean) : [],
      scope: {
        branches: readString(formData, "scope_branches") ? readString(formData, "scope_branches").split(",").map((item) => item.trim()).filter(Boolean) : [],
        resource_names: readString(formData, "scope_resource_names") ? readString(formData, "scope_resource_names").split(",").map((item) => item.trim()).filter(Boolean) : [],
        service_names: readString(formData, "scope_service_names") ? readString(formData, "scope_service_names").split(",").map((item) => item.trim()).filter(Boolean) : [],
      },
      status: "verified",
    }),
  );
}

export async function submitOperationalCommandAction(formData: FormData) {
  const organizationId = readString(formData, "organization_id");
  const botId = readString(formData, "bot_id");
  const redirectTo = readString(formData, "redirect_to") || "/client/operaciones";
  const mode = readString(formData, "mode") || "preview";
  await runAndRefresh(redirectTo, () =>
    postJson(`/api/v1/client/operations/commands`, {
      organization_id: organizationId,
      bot_id: botId,
      text: readString(formData, "text"),
      source_channel: "portal",
      dry_run: mode !== "execute",
    }),
  );
}

export async function confirmOperationalCommandAction(formData: FormData) {
  const commandId = readString(formData, "command_id");
  const redirectTo = readString(formData, "redirect_to") || "/client/operaciones";
  await runAndRefresh(redirectTo, () =>
    postJson(`/api/v1/client/operations/commands/${commandId}/confirm`, {
      confirmation_code: readString(formData, "confirmation_code") || null,
    }),
  );
}

export async function approveOperationalCommandAction(formData: FormData) {
  const commandId = readString(formData, "command_id");
  const redirectTo = readString(formData, "redirect_to") || "/client/operaciones";
  await runAndRefresh(redirectTo, () =>
    postJson(`/api/v1/client/operations/commands/${commandId}/approve`, {
      note: readString(formData, "note") || "approved_from_portal",
    }),
  );
}

export async function cancelOperationalCommandAction(formData: FormData) {
  const commandId = readString(formData, "command_id");
  const redirectTo = readString(formData, "redirect_to") || "/client/operaciones";
  await runAndRefresh(redirectTo, () =>
    postJson(`/api/v1/client/operations/commands/${commandId}/cancel`, {
      reason: readString(formData, "reason") || "cancelled_from_portal",
    }),
  );
}

export async function previewRescheduleBatchAction(formData: FormData) {
  const redirectTo = readString(formData, "redirect_to") || "/client/operaciones";
  await runAndRefresh(redirectTo, () =>
    postJson(`/api/v1/client/operations/reschedule-batches/preview`, {
      organization_id: readString(formData, "organization_id"),
      bot_id: readString(formData, "bot_id"),
      scope_day: readString(formData, "scope_day") || "tomorrow",
      target_date: readString(formData, "target_date") || null,
      target_start_time: readString(formData, "target_start_time") || "09:00",
      target_end_time: readString(formData, "target_end_time") || "18:00",
      strategy: readString(formData, "strategy") || "next_available_window",
      delay_minutes: Number(readString(formData, "delay_minutes") || "30"),
      notify_clients: readString(formData, "notify_clients") === "on",
    }),
  );
}

export async function executeRescheduleBatchAction(formData: FormData) {
  const redirectTo = readString(formData, "redirect_to") || "/client/operaciones";
  await runAndRefresh(redirectTo, () =>
    postJson(`/api/v1/client/operations/reschedule-batches/execute`, {
      organization_id: readString(formData, "organization_id"),
      bot_id: readString(formData, "bot_id"),
      scope_day: readString(formData, "scope_day") || "tomorrow",
      target_date: readString(formData, "target_date") || null,
      target_start_time: readString(formData, "target_start_time") || "09:00",
      target_end_time: readString(formData, "target_end_time") || "18:00",
      strategy: readString(formData, "strategy") || "next_available_window",
      delay_minutes: Number(readString(formData, "delay_minutes") || "30"),
      notify_clients: readString(formData, "notify_clients") === "on",
      confirm_large_impact: true,
    }),
  );
}


export async function undoOperationalCommandAction(formData: FormData) {
  const commandId = readString(formData, "command_id");
  const redirectTo = readString(formData, "redirect_to") || "/client/operaciones";
  await runAndRefresh(redirectTo, () =>
    postJson(`/api/v1/client/operations/commands/${commandId}/undo`, {
      reason: readString(formData, "reason") || "undo_requested",
    }),
  );
}
