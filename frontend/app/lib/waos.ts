import "server-only";
import { ApiRequestError, apiFetch, apiFetchOrDefault, apiFetchResult } from "./api";
import {
  type AgendaOverviewContract,
  type AppointmentContract,
  type AnalyticsDailyContract,
  type ActivationSummaryContract,
  type InboxSavedViewContract,
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
  type IntegrationCenterContract,
  type MediaAssetContract,
  type ObservabilityContract,
  type PaymentContract,
  type PortalRequestContract,
  type PromotionContract,
  type QueueOverviewContract,
  type InboxQueuesContract,
  type ConversationDecisionSupportContract,
  type CRMPipelineSummaryContract,
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
  type TalentOverviewContract,
  type TraceabilityContract,
  type VerticalProfileContract,
  normalizeAgendaOverview,
  normalizeAnalyticsDaily,
  normalizeActivationSummary,
  normalizeInboxSavedView,
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
  normalizeIntegrationCenter,
  normalizeMediaAsset,
  normalizeObservability,
  normalizePayment,
  normalizePortalRequest,
  normalizePromotion,
  normalizeQueueOverview,
  normalizeInboxQueues,
  normalizeConversationDecisionSupport,
  normalizeCRMPipelineSummary,
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
  normalizeTalentOverview,
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

export type PortalModuleState<T> = {
  ok: boolean;
  data: T;
  error: ApiRequestError | null;
  endpoint: string;
};

export type ClientPortalSection = "resumen" | "conversaciones" | "agenda" | "promociones" | "solicitudes" | "bot" | "operaciones";

export type ClientPortalData = {
  context: { organizationId: string | null; botId: string | null; vertical: string | null };
  conversations: PortalModuleState<ConversationItem[]>;
  appointments: PortalModuleState<AppointmentContract[]>;
  agendaOverview: PortalModuleState<AgendaOverviewContract>;
  feedback: PortalModuleState<FeedbackItemContract[]>;
  requests: PortalModuleState<PortalRequestContract[]>;
  promotions: PortalModuleState<PromotionContract[]>;
  behavior: PortalModuleState<Record<string, unknown>>;
  verticalProfile: PortalModuleState<VerticalProfileContract>;
};

function normalizeLooseRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function portalDisabledState<T>(data: T, endpoint: string): PortalModuleState<T> {
  return { ok: true, data, error: null, endpoint };
}

async function fetchArrayState<T>(endpoint: string, fallback: unknown[], normalizeItem: (value: unknown) => T): Promise<PortalModuleState<T[]>> {
  const result = await apiFetchResult<unknown>(endpoint);
  if (!result.ok) return { ok: false, data: normalizeCollection(fallback, normalizeItem), error: result.error, endpoint };
  return { ok: true, data: normalizeCollection(result.data, normalizeItem), error: null, endpoint };
}

async function fetchRecordState<T>(endpoint: string, fallback: unknown, normalizeItem: (value: unknown) => T): Promise<PortalModuleState<T>> {
  const result = await apiFetchResult<unknown>(endpoint);
  if (!result.ok) return { ok: false, data: normalizeItem(fallback), error: result.error, endpoint };
  return { ok: true, data: normalizeItem(result.data), error: null, endpoint };
}

export async function getClientPortalData(section: ClientPortalSection, vertical?: string, botId?: string): Promise<ClientPortalData> {
  const wantsSummary = section === "resumen";
  const wantsConversations = wantsSummary || section === "conversaciones";
  const wantsAppointments = wantsSummary || section === "agenda";
  const wantsRequests = wantsSummary || section === "solicitudes";
  const wantsPromotions = wantsSummary || section === "promociones";
  const wantsBot = wantsSummary || section === "bot";

  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const currentOrganizationId = await getCurrentOrganizationId();
  const verticalValue = vertical || null;
  const emptyVerticalProfile = normalizeVerticalProfile({
    id: "",
    name: "",
    short_name: "",
    description: "",
    problem: "",
    portfolio_tier: "",
    master_thesis: "",
    subverticals: [],
    objects: [],
    flows: [],
    kpis: [],
    recommended_integrations: [],
    buyer: {},
    one_pager: {},
    demo_flow: [],
    native_objects: {},
    pipeline: {},
    bot_playbook: {},
    automation_sequences: [],
    runtime_connection: {},
  });

  const conversationEndpoint = `/api/v1/conversations?${query}`;
  const appointmentsEndpoint = `/api/v1/appointments?${query}`;
  const agendaEndpoint = `/api/v1/agenda/overview?${query}`;
  const feedbackEndpoint = `/api/v1/feedback?${query}`;
  const requestsEndpoint = `/api/v1/portal/requests?${query}`;
  const promotionsEndpoint = `/api/v1/promotions?${[query, currentBotId ? `bot_id=${encodeURIComponent(currentBotId)}` : ""].filter(Boolean).join("&")}`;
  const behaviorEndpoint = currentBotId ? `/api/v1/bot-studio/behavior?${query}&bot_id=${encodeURIComponent(currentBotId)}` : `/api/v1/bot-studio/behavior?${query}`;
  const verticalParams = [query, verticalValue ? `vertical=${encodeURIComponent(verticalValue)}` : "", currentBotId ? `bot_id=${encodeURIComponent(currentBotId)}` : ""].filter(Boolean).join("&");
  const verticalEndpoint = `/api/v1/verticals/profile?${verticalParams}`;

  const [conversations, appointments, agendaOverview, feedback, requests, promotions, behavior, verticalProfile] = await Promise.all([
    wantsConversations ? fetchArrayState(conversationEndpoint, [], normalizeConversation) : Promise.resolve(portalDisabledState([], conversationEndpoint)),
    wantsAppointments ? fetchArrayState(appointmentsEndpoint, [], normalizeAppointment) : Promise.resolve(portalDisabledState([], appointmentsEndpoint)),
    wantsAppointments ? fetchRecordState(agendaEndpoint, { summary: {}, upcoming: [] }, normalizeAgendaOverview) : Promise.resolve(portalDisabledState(normalizeAgendaOverview({ summary: {}, upcoming: [] }), agendaEndpoint)),
    wantsRequests ? fetchArrayState(feedbackEndpoint, [], normalizeFeedbackItem) : Promise.resolve(portalDisabledState([], feedbackEndpoint)),
    wantsRequests ? fetchArrayState(requestsEndpoint, [], normalizePortalRequest) : Promise.resolve(portalDisabledState([], requestsEndpoint)),
    wantsPromotions ? fetchArrayState(promotionsEndpoint, [], normalizePromotion) : Promise.resolve(portalDisabledState([], promotionsEndpoint)),
    wantsBot
      ? (currentBotId ? fetchRecordState(behaviorEndpoint, {}, normalizeLooseRecord) : Promise.resolve(portalDisabledState({}, behaviorEndpoint)))
      : Promise.resolve(portalDisabledState({}, behaviorEndpoint)),
    wantsBot || wantsSummary
      ? fetchRecordState(verticalEndpoint, emptyVerticalProfile, normalizeVerticalProfile)
      : Promise.resolve(portalDisabledState(emptyVerticalProfile, verticalEndpoint)),
  ]);

  return {
    context: { organizationId: currentOrganizationId, botId: currentBotId, vertical: verticalValue },
    conversations,
    appointments,
    agendaOverview,
    feedback,
    requests,
    promotions,
    behavior,
    verticalProfile,
  };
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

export async function getConversations(sort?: string): Promise<ConversationItem[]> {
  const query = await orgQuery();
  const sortSuffix = sort ? `&sort=${encodeURIComponent(sort)}` : "";
  return fetchArray(`/api/v1/conversations?${query}${sortSuffix}`, [], normalizeConversation);
}

export async function getActivationSummary(botId?: string): Promise<ActivationSummaryContract> {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const botSuffix = currentBotId ? `&bot_id=${encodeURIComponent(currentBotId)}` : "";
  return fetchRecord(`/api/v1/onboarding/summary?${query}${botSuffix}`, { counts: {}, progress: {}, blockers: [], checklist: [], next_step: {}, feature_flags: {} }, normalizeActivationSummary);
}

export async function getInboxSavedViews(): Promise<InboxSavedViewContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/inbox/saved-views?${query}`, [], normalizeInboxSavedView);
}

export async function getConversation(conversationId: string): Promise<ConversationDetailContract> {
  return fetchRecord(`/api/v1/conversations/${conversationId}`, { conversation: {}, contact: {}, memory: {}, bot: {}, messages: [] }, normalizeConversationDetail);
}


export async function getInboxQueues(): Promise<InboxQueuesContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/inbox/queues?${query}`, { queues: [] }, normalizeInboxQueues);
}

export async function getConversationDecisionSupport(conversationId: string): Promise<ConversationDecisionSupportContract> {
  return fetchRecord(`/api/v1/conversations/${conversationId}/decision-support`, { conversation_id: conversationId, queue: {}, sla: {}, explanation: {}, risk_flags: [] }, normalizeConversationDecisionSupport);
}

export async function getCRMPipelineSummary(botId?: string): Promise<CRMPipelineSummaryContract> {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const suffix = currentBotId ? `&bot_id=${encodeURIComponent(currentBotId)}` : '';
  return fetchRecord(`/api/v1/crm/pipeline-summary?${query}${suffix}`, { total_leads: 0, weighted_amount: 0, stages: [], lost_reasons: [], recent_stage_changes: [] }, normalizeCRMPipelineSummary);
}

export async function getIntegrationCenter(): Promise<IntegrationCenterContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/integrations/center?${query}`, { summary: {}, integrations: [], observability: {}, recent_sync_runs: [], failed_receipts: [], retry_hotspots: [], dependency_map: [] }, normalizeIntegrationCenter);
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

export async function getWhatsappDeliveryTruth(botId?: string, options?: { reconcile?: boolean; windowHours?: number; limit?: number }) {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const params = new URLSearchParams(query);
  if (currentBotId) params.set("bot_id", currentBotId);
  if (options?.reconcile) params.set("reconcile", "true");
  if (options?.windowHours) params.set("window_hours", String(options.windowHours));
  if (options?.limit) params.set("limit", String(options.limit));
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/analytics/whatsapp/delivery-truth?${params.toString()}`, { summary: {}, breakdowns: {}, recent_messages: [], alerts: [], reconciliation: {} });
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

export async function getVerticalCatalog(topOnly = false): Promise<VerticalProfileContract[]> {
  const raw = await apiFetchOrDefault<unknown[]>(`/api/v1/verticals${topOnly ? "?top_only=1" : ""}`, []);
  return normalizeCollection(raw, normalizeVerticalProfile);
}

export async function getStrongestVerticals(): Promise<VerticalProfileContract[]> {
  return getVerticalCatalog(true);
}

export async function getVerticalProfile(vertical?: string, botId?: string, subvertical?: string, organizationId?: string): Promise<VerticalProfileContract> {
  const query = organizationId ? `organization_id=${encodeURIComponent(organizationId)}` : await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const params = [query];
  if (vertical) params.push(`vertical=${encodeURIComponent(vertical)}`);
  if (subvertical) params.push(`subvertical=${encodeURIComponent(subvertical)}`);
  if (currentBotId) params.push(`bot_id=${encodeURIComponent(currentBotId)}`);
  const qs = params.filter(Boolean).join("&");
  const raw = await apiFetchOrDefault<unknown>(`/api/v1/verticals/profile?${qs}`, {});
  return normalizeVerticalProfile(raw);
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

export async function getTalentOverview(botId?: string): Promise<TalentOverviewContract> {
  const currentBotId = await selectedBotId(botId);
  if (!currentBotId) return { bot_id: "", config: {}, vacancies: [], candidates: [], summary: {} };
  return fetchRecord(`/api/v1/bots/${currentBotId}/talent/overview`, { bot_id: currentBotId, config: {}, vacancies: [], candidates: [], summary: {} }, normalizeTalentOverview);
}



export async function getInboxOwnership() {
  const query = await orgQuery();
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/inbox/ownership?${query}`, { organization_id: null, unassigned_open: 0, owners: [] });
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

export async function getAgendaResources(botId?: string) {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const suffix = currentBotId ? `&bot_id=${encodeURIComponent(currentBotId)}` : '';
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/agenda/resources?${query}${suffix}`, []);
}

export async function getAgendaCapacityRules(botId?: string) {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const suffix = currentBotId ? `&bot_id=${encodeURIComponent(currentBotId)}` : '';
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/agenda/capacity-rules?${query}${suffix}`, []);
}

export async function getAgendaCapacityOverview(botId?: string) {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const suffix = currentBotId ? `&bot_id=${encodeURIComponent(currentBotId)}` : '';
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/agenda/capacity/overview?${query}${suffix}`, { summary: {}, resources: [], rules: [], upcoming: [] });
}
