import "server-only";

export type { Summary } from "./contracts/bots";
export type { PortalModuleState } from "./data/shared";
export type { ClientPortalData, ClientPortalSection } from "./data/client-portal";

// Deprecated compatibility barrel for legacy screens only.
// Prefer importing from app/lib/data/<domain> directly in new code.

export { getClientPortalData } from "./data/client-portal";

export {
  getBot,
  getBots,
  getBuilds,
  getReleaseReadiness,
  getReleases,
  getTalentOverview,
  getTraceability,
  getBotTemplates,
  getBotBehavior,
  getBotSimulationCases,
  getBotSimulationRuns,
  getBotValidation,
} from "./data/bots";

export { getActivationSummary } from "./data/onboarding";

export {
  getVerticalCatalog,
  getStrongestVerticals,
  getVerticalProfile,
} from "./data/verticals";

export {
  getConversations,
  getInboxSavedViews,
  getConversation,
  getInboxQueues,
  getConversationDecisionSupport,
  getConversationReviews,
  getVoiceNotes,
  getFeedback,
  getPortalRequests,
  getAppointments,
  getAgendaOverview,
  getInboxOwnership,
  getAgendaResources,
  getAgendaCapacityRules,
  getAgendaCapacityOverview,
  getWhatsappFlows,
} from "./data/inbox";

export {
  getDashboard,
  getRuns,
  getLogs,
  getObservability,
  getQueue,
  getWhatsappDeliveryTruth,
  getDailyAnalytics,
  getReactivationRecommendations,
  getExecutiveReports,
  getDirectorMode,
  getI18nConfig,
  getI18nAnalytics,
  getOmnichannelOverview,
  getBusinessHubOverview,
  getV14PublishSchedules,
  getV15PublishRuns,
} from "./data/analytics";

export {
  getPayments,
  getCRMLeads,
  getPlaybooks,
  getCRMPipelineSummary,
  getCatalogProducts,
  getCatalogServices,
  getMediaAssets,
  getPromotions,
  getPromotionRules,
  getCommerceInsights,
} from "./data/commerce";

export {
  getIntegrations,
  getSecrets,
  getIntegrationCenter,
  getScheduler,
  getRateLimits,
  getAccessMatrix,
  getSecurityPolicy,
  getSSOProviders,
  getRuntimeCallbacks,
  getDeadLetters,
  getIntegrationSyncRuns,
  getIntegrationEvents,
  getIntegrationObservability,
  getGoogleCalendars,
  getSystemStatus,
  getHealth,
} from "./data/integrations";
