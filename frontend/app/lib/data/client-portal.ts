import type { ConversationItem } from "../contracts/inbox";
import { normalizeConversation } from "../contracts/inbox";
import type { AgendaOverviewContract, AppointmentContract } from "../contracts/onboarding";
import { normalizeAgendaOverview, normalizeAppointment } from "../contracts/onboarding";
import type { FeedbackItemContract, PortalRequestContract } from "../contracts/portal";
import { normalizeFeedbackItem, normalizePortalRequest } from "../contracts/portal";
import type { PromotionContract } from "../contracts/commerce";
import { normalizePromotion } from "../contracts/commerce";
import type { VerticalProfileContract } from "../contracts/verticals";
import { normalizeVerticalProfile } from "../contracts/verticals";
import { getCurrentOrganizationId } from "../session";
import { fetchArrayState, fetchRecordState, normalizeLooseRecord, orgQuery, portalDisabledState, type PortalModuleState, selectedBotId } from "./shared";

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
