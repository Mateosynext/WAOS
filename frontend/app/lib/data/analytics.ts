import type { AnalyticsDailyContract, AuditLogContract, BusinessHubOverviewContract, DashboardContract, ObservabilityContract, QueueOverviewContract, RecommendationContract } from "../contracts/analytics";
import { normalizeAnalyticsDaily, normalizeAuditLog, normalizeBusinessHubOverview, normalizeDashboard, normalizeObservability, normalizeQueueOverview, normalizeRecommendation } from "../contracts/analytics";
import type { RunContract } from "../contracts/bots";
import { normalizeRun } from "../contracts/bots";
import { apiFetchOrDefault } from "../api";
import { fetchArray, fetchArrayState, fetchRecord, fetchRecordState, orgQuery, selectedBotId, type LooseRecord, type PortalModuleState } from "./shared";

export type DirectorModeResponse = {
  summary: LooseRecord;
  narrative: Array<LooseRecord>;
};

export type I18nAnalyticsResponse = {
  summary: LooseRecord;
  breakdown: LooseRecord;
};

export type OmnichannelOverviewResponse = {
  summary: LooseRecord;
  threads: Array<LooseRecord>;
};

export async function getDashboard(): Promise<DashboardContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/analytics/dashboard?${query}`, { summary: {}, bots: [] }, normalizeDashboard);
}

export async function getRuns(): Promise<RunContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/runs?${query}`, [], normalizeRun);
}

export async function getLogs(): Promise<AuditLogContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/logs/technical?${query}`, [], normalizeAuditLog);
}

export async function getObservabilityState(): Promise<PortalModuleState<ObservabilityContract>> {
  const query = await orgQuery();
  return fetchRecordState(`/api/v1/observability/overview?${query}`, { totals: {}, recent_failures: [], recent_logs: [] }, normalizeObservability);
}

export async function getObservability(): Promise<ObservabilityContract> {
  return (await getObservabilityState()).data;
}

export async function getQueueState(): Promise<PortalModuleState<QueueOverviewContract>> {
  const query = await orgQuery();
  return fetchRecordState(`/api/v1/runtime/queue?${query}`, { automation_jobs: [], outbox: [], callbacks: [], integration_sync: [] }, normalizeQueueOverview);
}

export async function getQueue(): Promise<QueueOverviewContract> {
  return (await getQueueState()).data;
}

export async function getWhatsappDeliveryTruthState(botId?: string, options?: { reconcile?: boolean; windowHours?: number; limit?: number }): Promise<PortalModuleState<Record<string, unknown>>> {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const params = new URLSearchParams(query);
  if (currentBotId) params.set("bot_id", currentBotId);
  if (options?.reconcile) params.set("reconcile", "true");
  if (options?.windowHours) params.set("window_hours", String(options.windowHours));
  if (options?.limit) params.set("limit", String(options.limit));
  return fetchRecordState(`/api/v1/analytics/whatsapp/delivery-truth?${params.toString()}`, { summary: {}, breakdowns: {}, recent_messages: [], alerts: [], reconciliation: {} }, (value) => (value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : { summary: {}, breakdowns: {}, recent_messages: [], alerts: [], reconciliation: {} }));
}

export async function getWhatsappDeliveryTruth(botId?: string, options?: { reconcile?: boolean; windowHours?: number; limit?: number }) {
  return (await getWhatsappDeliveryTruthState(botId, options)).data;
}

export async function getDailyAnalytics(botId?: string): Promise<AnalyticsDailyContract> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchRecord(`/api/v1/analytics/daily?${query}${botSuffix}`, { day: "-", metrics: {} }, normalizeAnalyticsDaily);
}

export async function getReactivationRecommendations(): Promise<RecommendationContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/reactivation/recommendations?${query}`, [], normalizeRecommendation);
}

export async function getExecutiveReportsState(): Promise<PortalModuleState<Array<Record<string, unknown>>>> {
  const query = await orgQuery();
  return fetchArrayState(`/api/v1/reports/executive?${query}`, [], (value) => (value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}));
}

export async function getExecutiveReports() {
  return (await getExecutiveReportsState()).data;
}

export async function getDirectorModeState(): Promise<PortalModuleState<DirectorModeResponse>> {
  const query = await orgQuery();
  return fetchRecordState(`/api/v1/analytics/director-mode?${query}`, { summary: {}, narrative: [] }, (value) => {
    const record = value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
    return { summary: (record.summary && typeof record.summary === "object" ? record.summary as LooseRecord : {}), narrative: Array.isArray(record.narrative) ? record.narrative.filter((item): item is LooseRecord => Boolean(item) && typeof item === "object") : [] };
  });
}

export async function getDirectorMode(): Promise<DirectorModeResponse> {
  return (await getDirectorModeState()).data;
}

export async function getI18nConfig(botId?: string) {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  if (!currentBotId) return {};
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/i18n/config?${query}&bot_id=${encodeURIComponent(currentBotId)}`, {});
}

export async function getI18nAnalytics(botId?: string): Promise<I18nAnalyticsResponse> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return apiFetchOrDefault<I18nAnalyticsResponse>(`/api/v1/i18n/analytics?${query}${botSuffix}`, { summary: {}, breakdown: {} });
}

export async function getOmnichannelOverview(botId?: string): Promise<OmnichannelOverviewResponse> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return apiFetchOrDefault<OmnichannelOverviewResponse>(`/api/v1/omnichannel/overview?${query}${botSuffix}`, { summary: {}, threads: [] });
}

export async function getBusinessHubOverview(botId?: string): Promise<BusinessHubOverviewContract> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchRecord(`/api/v1/business-hub/overview?${query}${botSuffix}`, { summary: {}, top_products: [], attention: [] }, normalizeBusinessHubOverview);
}

export async function getV14Funnel() {
  const query = await orgQuery();
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/analytics/funnel?${query}`, { funnel: [] });
}

export async function getV14Risk() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/inbox/risk?${query}`, []);
}

export async function getV14OperatorPerformance() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/analytics/operator-performance?${query}`, []);
}

export async function getV14Objections() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/analytics/objections?${query}`, []);
}

export async function getV14Heatmap() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/analytics/heatmap?${query}`, []);
}

export async function getV14Alerts() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/alerts/rules?${query}`, []);
}

export async function getV14ReportSchedules() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/reports/schedules?${query}`, []);
}

export async function getV14RoutingRules() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/routing/rules?${query}`, []);
}

export async function getV14FollowupExperiments() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/followups/experiments?${query}`, []);
}

export async function getV14BotTemplates() {
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/bot-library/templates`, []);
}

export async function getV14WhatsAppStatus() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/whatsapp/numbers/status?${query}`, []);
}

export async function getV14PublishSchedules() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/publish-schedules?${query}`, []);
}

export async function getV15Notifications() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/notifications?${query}`, []);
}

export async function getV15AlertEvents() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/alerts/events?${query}`, []);
}

export async function getV15RoutingAssignments() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/routing/assignments?${query}`, []);
}

export async function getV15ReportRuns() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/reports/schedule-runs?${query}`, []);
}

export async function getV15PublishRuns() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/publish-schedule-runs?${query}`, []);
}

export async function getV16Deliveries() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/deliveries?${query}`, []);
}

export async function getV16FollowupAssignments() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/followups/assignments?${query}`, []);
}

export async function getV16FollowupPerformance(experimentId?: string) {
  const selectedExperimentId = experimentId || ((await getV14FollowupExperiments())[0]?.id as string | undefined);
  if (!selectedExperimentId) return { experiment: {}, variants: [], assignments: [] };
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/followups/experiments/${selectedExperimentId}/performance`, { experiment: {}, variants: [], assignments: [] });
}
