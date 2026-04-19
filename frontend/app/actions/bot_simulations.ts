"use server";
import { postJson, readString, runAndRefresh } from "./shared";

function readBooleanOptional(formData: FormData, key: string): boolean | null {
  if (!formData.has(key)) return null;
  const raw = String(formData.get(key) || "").toLowerCase();
  return ["on", "true", "1", "yes"].includes(raw);
}

export async function createBotSimulationCaseAction(formData: FormData) {
  const botId = readString(formData, "bot_id");
  const organizationId = readString(formData, "organization_id");
  const redirectTo = readString(formData, "redirect_to") || "/bot-studio";
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/bots/${botId}/simulation-cases`, {
    organization_id: organizationId,
    title: readString(formData, "title"),
    scenario_text: readString(formData, "scenario_text"),
    expected_action: readString(formData, "expected_action") || null,
    expected_queue: readString(formData, "expected_queue") || null,
    expected_must_escalate: readBooleanOptional(formData, "expected_must_escalate"),
    tags: [],
  }));
}

export async function runBotSimulationAction(formData: FormData) {
  const botId = readString(formData, "bot_id");
  const redirectTo = readString(formData, "redirect_to") || "/bot-studio";
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/bots/${botId}/simulate`, {
    compare_target: readString(formData, "compare_target") || "draft",
    case_ids: [],
    right_version_id: readString(formData, "right_version_id") || null,
  }));
}

export async function createBotDraftSnapshotAction(formData: FormData) {
  const botId = readString(formData, "bot_id");
  const redirectTo = readString(formData, "redirect_to") || "/bot-studio";
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/bots/${botId}/versions/draft-snapshot`, { notes: readString(formData, "notes") }));
}
