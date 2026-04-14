import { apiFetchOrDefault } from "./api";
import {
  type AgendaOverviewContract,
  type AnalyticsDailyContract,
  type AuditLogContract,
  type BotContract,
  type BotTemplateContract,
  type BuildContract,
  type BusinessHubOverviewContract,
  type CRMLeadContract,
  type CatalogProductContract,
  type CatalogServiceContract,
  type CommerceInsightsContract,
  type ConversationDetailContract,
  type ConversationItem,
  type DashboardContract,
  type DeadLettersContract,
  type FeedbackItemContract,
  type IntegrationContract,
  type IntegrationEventContract,
  type IntegrationObservabilityContract,
  type MediaAssetContract,
  type ObservabilityContract,
  type PaymentContract,
  type PortalRequestContract,
  type PromotionContract,
  type QueueOverviewContract,
  type RateLimitPolicyContract,
  type RecommendationContract,
  type ReleaseReadinessContract,
  type ReleaseRequestContract,
  type RunContract,
  type RuntimeCallbackContract,
  type SchedulerOverviewContract,
  type SecretContract,
  type SecurityPolicyContract,
  type SSOProviderContract,
  type Summary,
  type SyncRunContract,
  type TraceabilityContract,
  type VerticalProfileContract,
  normalizeAgendaOverview,
  normalizeAnalyticsDaily,
  normalizeAppointment,
  normalizeAuditLog,
  normalizeBot,
  normalizeBotTemplate,
  normalizeBuild,
  normalizeBusinessHubOverview,
  normalizeCRMLead,
  normalizeCatalogProduct,
  normalizeCatalogService,
  normalizeCollection,
  normalizeCommerceInsights,
  normalizeConversation,
  normalizeConversationDetail,
  normalizeDashboard,
  normalizeDeadLetters,
  normalizeFeedbackItem,
  normalizeIntegration,
  normalizeIntegrationEvent,
  normalizeIntegrationObservability,
  normalizeMediaAsset,
  normalizeObservability,
  normalizePayment,
  normalizePortalRequest,
  normalizePromotion,
  normalizeQueueOverview,
  normalizeRateLimitPolicy,
  normalizeRecommendation,
  normalizeReleaseReadiness,
  normalizeReleaseRequest,
  normalizeRun,
  normalizeRuntimeCallback,
  normalizeSchedulerOverview,
  normalizeSecret,
  normalizeSecurityPolicy,
  normalizeSSOProvider,
  normalizeSyncRun,
  normalizeTraceability,
  normalizeVerticalProfile,
} from "./contracts";
import { getCurrentBotId, getCurrentOrganizationId } from "./session";

export type { Summary } from "./contracts";


type LooseRecord = Record<string, unknown>;

export type BotValidationResponse = {
  bot_id: string;
  validation: { ok: boolean; score: number; errors: string[]; warnings: string[] };
  against_published: { total_changes: number; changes: Array<LooseRecord> };
};

export type TraceabilityResponse = TraceabilityContract;
export type ReleaseReadinessResponse = ReleaseReadinessContract;

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

export type CommerceInsightsResponse = CommerceInsightsContract;

async function orgQuery(): Promise<string> {
  const organizationId = await getCurrentOrganizationId();
  return organizationId ? `organization_id=${encodeURIComponent(organizationId)}` : "";
}

async function selectedBotId(botId?: string): Promise<string | null> {
  if (botId) return botId;
  return await getCurrentBotId();
}

async function fetchArray<T>(path: string, fallback: unknown[], normalizeItem: (value: unknown) => T): Promise<T[]> {
  const raw = await apiFetchOrDefault<unknown>(path, fallback);
  return normalizeCollection(raw, normalizeItem);
}

async function fetchRecord<T>(path: string, fallback: unknown, normalizeItem: (value: unknown) => T): Promise<T> {
  const raw = await apiFetchOrDefault<unknown>(path, fallback);
  return normalizeItem(raw);
}

export async function getDashboard(): Promise<DashboardContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/analytics/dashboard?${query}`, { summary: {}, bots: [] }, normalizeDashboard);
}

export async function getBots(): Promise<BotContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/bots?${query}`, [], normalizeBot);
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

export async function getRuns(): Promise<RunContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/runs?${query}`, [], normalizeRun);
}

export async function getLogs(): Promise<AuditLogContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/logs/technical?${query}`, [], normalizeAuditLog);
}

export async function getObservability(): Promise<ObservabilityContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/observability/overview?${query}`, { totals: {}, recent_failures: [], recent_logs: [] }, normalizeObservability);
}

export async function getQueue(): Promise<QueueOverviewContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/runtime/queue?${query}`, { automation_jobs: [], outbox: [], callbacks: [], integration_sync: [] }, normalizeQueueOverview);
}

export async function getIntegrations(): Promise<IntegrationContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/integrations?${query}`, [], normalizeIntegration);
}

export async function getSecrets(): Promise<SecretContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/secrets?${query}`, [], normalizeSecret);
}

export async function getConversations(): Promise<ConversationItem[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/conversations?${query}`, [], normalizeConversation);
}

export async function getConversation(conversationId: string): Promise<ConversationDetailContract> {
  return fetchRecord(`/api/v1/conversations/${conversationId}`, { conversation: {}, contact: {}, memory: {}, bot: {}, messages: [] }, normalizeConversationDetail);
}

export async function getReleaseReadiness(botId?: string): Promise<ReleaseReadinessResponse> {
  const currentBotId = await selectedBotId(botId);
  if (!currentBotId) return { bot_id: '', organization_id: '', vertical: {}, summary: {}, checklist: {}, checklist_items: [], blockers: [], warnings: [], integrations: [], validation: {}, diff_summary: {} };
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

export async function getScheduler(): Promise<SchedulerOverviewContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/runtime/scheduler?${query}`, { due_now: 0, next_job: null, counts: [], stale_locks: 0, integration_due_now: 0, next_integration: null, integration_retries: 0 }, normalizeSchedulerOverview);
}

export async function getRateLimits(): Promise<RateLimitPolicyContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/rate-limits?${query}`, [], normalizeRateLimitPolicy);
}

export async function getAccessMatrix() {
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/access/matrix`, { current_user_role: "unknown", roles: {} });
}

export async function getDailyAnalytics(botId?: string): Promise<AnalyticsDailyContract> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchRecord(`/api/v1/analytics/daily?${query}${botSuffix}`, { day: "-", metrics: {} }, normalizeAnalyticsDaily);
}

export async function getSecurityPolicy(): Promise<SecurityPolicyContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/security/policies?${query}`, { organization_id: null, require_mfa: false, require_sso: false, session_ttl_minutes: 0, webhook_signature_required: false, strict_idempotency: false, ip_allowlist: [], allowed_origins: [] }, normalizeSecurityPolicy);
}

export async function getSSOProviders(): Promise<SSOProviderContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/security/sso?${query}`, [], normalizeSSOProvider);
}

export async function getRuntimeCallbacks(): Promise<RuntimeCallbackContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/runtime/callbacks?${query}`, [], normalizeRuntimeCallback);
}

export async function getDeadLetters(): Promise<DeadLettersContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/operations/dead-letters?${query}`, { jobs: [], outbox: [] }, normalizeDeadLetters);
}

export async function getIntegrationSyncRuns(): Promise<SyncRunContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/integrations/sync-runs?${query}`, [], normalizeSyncRun);
}


export async function getIntegrationEvents(): Promise<IntegrationEventContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/integrations/events?${query}`, [], normalizeIntegrationEvent);
}

export async function getIntegrationObservability(): Promise<IntegrationObservabilityContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/integrations/observability?${query}`, { totals: {}, latest_error: null, providers: [], recent: [] }, normalizeIntegrationObservability);
}

export async function getGoogleCalendars(integrationId: string | null | undefined): Promise<Array<Record<string, unknown>>> {
  if (!integrationId) return [];
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/integrations/${integrationId}/oauth/google/calendars`, []);
}

export async function getPayments(): Promise<PaymentContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/sales/payments?${query}`, [], normalizePayment);
}

export async function getCRMLeads(): Promise<CRMLeadContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/crm/leads?${query}`, [], normalizeCRMLead);
}

export async function getSellerMode(conversationId: string) {
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/sales/mode/${conversationId}`, {});
}

export async function getWhatsappFlows() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/whatsapp/flows?${query}`, []);
}

export async function getReactivationRecommendations(): Promise<RecommendationContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/reactivation/recommendations?${query}`, [], normalizeRecommendation);
}

export async function getExecutiveReports() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/reports/executive?${query}`, []);
}

export async function getDirectorMode(): Promise<DirectorModeResponse> {
  const query = await orgQuery();
  return apiFetchOrDefault<DirectorModeResponse>(`/api/v1/analytics/director-mode?${query}`, { summary: {}, narrative: [] });
}

export async function getConversationReviews() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/conversations/reviews?${query}`, []);
}

export async function getVoiceNotes() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/voice/notes?${query}`, []);
}

export async function getFeedback(): Promise<FeedbackItemContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/feedback?${query}`, [], normalizeFeedbackItem);
}

export async function getPortalRequests(): Promise<PortalRequestContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/portal/requests?${query}`, [], normalizePortalRequest);
}

export async function getPlaybooks() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/playbooks?${query}`, []);
}

export async function getAppointments() {
  const query = await orgQuery();
  return fetchArray(`/api/v1/appointments?${query}`, [], normalizeAppointment);
}

export async function getAgendaOverview(): Promise<AgendaOverviewContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/agenda/overview?${query}`, { summary: {}, upcoming: [] }, normalizeAgendaOverview);
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

export async function getCatalogCategories() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/catalog/categories?${query}`, []);
}

export async function getCatalogProducts(botId?: string): Promise<CatalogProductContract[]> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchArray(`/api/v1/catalog/products?${query}${botSuffix}`, [], normalizeCatalogProduct);
}

export async function getCatalogServices(botId?: string): Promise<CatalogServiceContract[]> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchArray(`/api/v1/catalog/services?${query}${botSuffix}`, [], normalizeCatalogService);
}

export async function getMediaAssets(botId?: string): Promise<MediaAssetContract[]> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchArray(`/api/v1/media/assets?${query}${botSuffix}`, [], normalizeMediaAsset);
}

export async function getPromotions(botId?: string): Promise<PromotionContract[]> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchArray(`/api/v1/promotions?${query}${botSuffix}`, [], normalizePromotion);
}

export async function getPromotionRules(promotionId?: string) {
  const query = await orgQuery();
  const promoSuffix = promotionId ? `&promotion_id=${encodeURIComponent(promotionId)}` : "";
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/promotions/rules?${query}${promoSuffix}`, []);
}

export async function getBotTemplates(botId?: string): Promise<BotTemplateContract[]> {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const botSuffix = currentBotId ? `&bot_id=${encodeURIComponent(currentBotId)}` : "";
  return fetchArray(`/api/v1/bot-studio/templates?${query}${botSuffix}`, [], normalizeBotTemplate);
}

export async function getVerticalCatalog(): Promise<VerticalProfileContract[]> {
  return fetchArray(`/api/v1/verticals`, [], normalizeVerticalProfile);
}

export async function getVerticalProfile(vertical?: string, botId?: string): Promise<VerticalProfileContract> {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const params = [query];
  if (vertical) params.push(`vertical=${encodeURIComponent(vertical)}`);
  if (currentBotId) params.push(`bot_id=${encodeURIComponent(currentBotId)}`);
  const qs = params.filter(Boolean).join("&");
  return fetchRecord(`/api/v1/verticals/profile?${qs}`, {}, normalizeVerticalProfile);
}

export async function getBotBehavior(botId?: string) {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  if (!currentBotId) return {};
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/bot-studio/behavior?${query}&bot_id=${encodeURIComponent(currentBotId)}`, {});
}

export async function getCommerceInsights(botId?: string): Promise<CommerceInsightsResponse> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchRecord(`/api/v1/commerce/insights?${query}${botSuffix}`, { summary: {}, top_products: [], top_assets: [], top_promotions: [], recommendations: [], alerts: [] }, normalizeCommerceInsights);
}

export async function getSystemStatus() {
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/system/status`, {
    status: "unknown",
    environment: "development",
    version: "-",
    checks: [],
    launch_checks: [],
    config: {},
  });
}

export async function getHealth() {
  return apiFetchOrDefault<Record<string, unknown>>(`/healthz`, {
    status: "unknown",
    service: "WAOS",
    version: "-",
    environment: "development",
  });
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
