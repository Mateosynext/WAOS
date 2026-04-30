import type { BotContract, BotTemplateContract, BuildContract, ReleaseReadinessContract, ReleaseRequestContract, TraceabilityContract } from "../contracts/bots";
import { normalizeBot, normalizeBotTemplate, normalizeBuild, normalizeReleaseReadiness, normalizeReleaseRequest, normalizeTraceability } from "../contracts/bots";
import type { TalentOverviewContract } from "../contracts/talent";
import { normalizeTalentOverview } from "../contracts/talent";
import { apiFetchOrDefault } from "../api";
import { fetchArray, fetchArrayState, fetchRecord, orgQuery, selectedBotId, type LooseRecord, type PortalModuleState } from "./shared";

export type BotValidationResponse = {
  bot_id: string;
  validation: { ok: boolean; score: number; errors: string[]; warnings: string[] };
  against_published: { total_changes: number; changes: Array<LooseRecord> };
};

export type TraceabilityResponse = TraceabilityContract;
export type ReleaseReadinessResponse = ReleaseReadinessContract;

export async function getBotsState(): Promise<PortalModuleState<BotContract[]>> {
  const query = await orgQuery();
  return fetchArrayState(`/api/v1/bots?${query}`, [], normalizeBot);
}

export async function getBots(): Promise<BotContract[]> {
  return (await getBotsState()).data;
}

export async function getBot(botId: string): Promise<BotContract> {
  return fetchRecord(`/api/v1/bots/${botId}`, {}, normalizeBot);
}

export async function getBotValidation(botId: string): Promise<BotValidationResponse> {
  return apiFetchOrDefault<BotValidationResponse>(`/api/v1/bots/${botId}/validate-draft`, { bot_id: botId, validation: { ok: false, score: 0, errors: [], warnings: [] }, against_published: { total_changes: 0, changes: [] } });
}

export async function getBuilds(botId: string): Promise<BuildContract[]> {
  return fetchArray(`/api/v1/bots/${botId}/builds`, [], normalizeBuild);
}

export async function getReleaseReadiness(botId?: string): Promise<ReleaseReadinessResponse> {
  const currentBotId = await selectedBotId(botId);
  if (!currentBotId) return { bot_id: "", organization_id: "", vertical: {}, summary: {}, checklist: {}, checklist_items: [], blockers: [], warnings: [], integrations: [], validation: {}, diff_summary: {} };
  return fetchRecord(`/api/v1/bots/${currentBotId}/release-readiness`, { bot_id: currentBotId, summary: {}, checklist: {}, checklist_items: [], blockers: [], warnings: [], integrations: [], validation: {}, diff_summary: {} }, normalizeReleaseReadiness);
}

export async function getReleases(botId?: string): Promise<ReleaseRequestContract[]> {
  const currentBotId = await selectedBotId(botId);
  if (!currentBotId) return [];
  return fetchArray(`/api/v1/bots/${currentBotId}/release-requests`, [], normalizeReleaseRequest);
}

export async function getTraceability(botId?: string): Promise<TraceabilityResponse> {
  const currentBotId = await selectedBotId(botId);
  if (!currentBotId) return { bot: {}, versions: [], builds: [], releases: [], runs: [] };
  return fetchRecord(`/api/v1/bots/${currentBotId}/traceability`, { bot: {}, versions: [], builds: [], releases: [], runs: [] }, normalizeTraceability);
}

export async function getBotTemplates(botId?: string): Promise<BotTemplateContract[]> {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const botSuffix = currentBotId ? `&bot_id=${encodeURIComponent(currentBotId)}` : "";
  return fetchArray(`/api/v1/bot-studio/templates?${query}${botSuffix}`, [], normalizeBotTemplate);
}

export async function getBotBehavior(botId?: string) {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  if (!currentBotId) return {};
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/bot-studio/behavior?${query}&bot_id=${encodeURIComponent(currentBotId)}`, {});
}

export async function getTalentOverview(botId?: string): Promise<TalentOverviewContract> {
  const currentBotId = await selectedBotId(botId);
  if (!currentBotId) return { bot_id: "", config: {}, vacancies: [], candidates: [], summary: {} };
  return fetchRecord(`/api/v1/bots/${currentBotId}/talent/overview`, { bot_id: currentBotId, config: {}, vacancies: [], candidates: [], summary: {} }, normalizeTalentOverview);
}

export async function getBotSimulationCases(botId?: string) {
  const currentBotId = await selectedBotId(botId);
  if (!currentBotId) return [];
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/bots/${currentBotId}/simulation-cases`, []);
}

export async function getBotSimulationRuns(botId?: string) {
  const currentBotId = await selectedBotId(botId);
  if (!currentBotId) return [];
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/bots/${currentBotId}/simulation-runs`, []);
}
