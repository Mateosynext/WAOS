import type { ConversationDecisionSupportContract, ConversationDetailContract, ConversationItem, InboxQueuesContract, InboxSavedViewContract } from "../contracts/inbox";
import { normalizeConversation, normalizeConversationDecisionSupport, normalizeConversationDetail, normalizeInboxQueues, normalizeInboxSavedView } from "../contracts/inbox";
import type { AgendaOverviewContract, AppointmentContract } from "../contracts/onboarding";
import { normalizeAgendaOverview, normalizeAppointment } from "../contracts/onboarding";
import type { FeedbackItemContract, PortalRequestContract } from "../contracts/portal";
import { normalizeFeedbackItem, normalizePortalRequest } from "../contracts/portal";
import { apiFetchOrDefault } from "../api";
import { fetchArray, fetchRecord, orgQuery, selectedBotId } from "./shared";

export async function getConversations(sort?: string): Promise<ConversationItem[]> {
  const query = await orgQuery();
  const sortSuffix = sort ? `&sort=${encodeURIComponent(sort)}` : "";
  return fetchArray(`/api/v1/conversations?${query}${sortSuffix}`, [], normalizeConversation);
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

export async function getAppointments(): Promise<AppointmentContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/appointments?${query}`, [], normalizeAppointment);
}

export async function getAgendaOverview(): Promise<AgendaOverviewContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/agenda/overview?${query}`, { summary: {}, upcoming: [] }, normalizeAgendaOverview);
}

export async function getInboxOwnership() {
  const query = await orgQuery();
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/inbox/ownership?${query}`, { organization_id: null, unassigned_open: 0, owners: [] });
}

export async function getAgendaResources(botId?: string) {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const suffix = currentBotId ? `&bot_id=${encodeURIComponent(currentBotId)}` : "";
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/agenda/resources?${query}${suffix}`, []);
}

export async function getAgendaCapacityRules(botId?: string) {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const suffix = currentBotId ? `&bot_id=${encodeURIComponent(currentBotId)}` : "";
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/agenda/capacity-rules?${query}${suffix}`, []);
}

export async function getAgendaCapacityOverview(botId?: string) {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const suffix = currentBotId ? `&bot_id=${encodeURIComponent(currentBotId)}` : "";
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/agenda/capacity/overview?${query}${suffix}`, { summary: {}, resources: [], rules: [], upcoming: [] });
}

export async function getWhatsappFlows() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/whatsapp/flows?${query}`, []);
}
