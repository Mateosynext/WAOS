import test from "node:test";
import assert from "node:assert/strict";
import { buildAgendaViewModel, buildBotAttributeModels, buildClientPortalSummaryViewModel, buildClientPortalTimeline, buildConversationCardModels, buildPromotionCardModels, hasPendingTimelineEntries } from "../app/client/clientPortalViewModel";
import type { ClientPortalData } from "../app/lib/data/client-portal";
import { normalizeAppointment, normalizeAgendaOverview } from "../app/lib/contracts/onboarding";
import { normalizeConversation } from "../app/lib/contracts/inbox";
import { normalizeFeedbackItem, normalizePortalRequest } from "../app/lib/contracts/portal";
import { normalizePromotion } from "../app/lib/contracts/commerce";
import { normalizeVerticalProfile } from "../app/lib/contracts/verticals";

const data: ClientPortalData = {
  context: { organizationId: "org_1", botId: "bot_1", vertical: "dental" },
  conversations: { ok: true, error: null, endpoint: "/api/v1/conversations", data: [normalizeConversation({ id: "c1", contact_name: "Ana", bot_name: "WAOS", status: "open", summary: "Paciente lista para reservar", latest_message_preview: "Quiero cita mañana", urgency_level: "high", attention_tier: "priority", recommended_mode: "human", updated_at: "2026-04-20T10:00:00Z" })] },
  appointments: { ok: true, error: null, endpoint: "/api/v1/appointments", data: [normalizeAppointment({ id: "a2", service_name: "Limpieza", customer_name: "Luis", scheduled_for: "2026-04-22T12:00:00Z", status: "confirmed", payment_status: "paid" }), normalizeAppointment({ id: "a1", service_name: "Valoración", customer_name: "Ana", scheduled_for: "2026-04-21T09:00:00Z", status: "pending", payment_status: "pending" })] },
  agendaOverview: { ok: true, error: null, endpoint: "/api/v1/agenda/overview", data: normalizeAgendaOverview({ summary: { pending: 1, confirmed: 1 }, upcoming: [] }) },
  feedback: { ok: true, error: null, endpoint: "/api/v1/feedback", data: [normalizeFeedbackItem({ id: "f1", comment: "Todo bien", created_at: "2026-04-19T08:00:00Z" })] },
  requests: { ok: true, error: null, endpoint: "/api/v1/portal/requests", data: [normalizePortalRequest({ id: "r1", kind: "pricing_change", detail: "Cambiar precio de blanqueamiento", status: "pending_review", created_at: "2026-04-20T11:00:00Z" })] },
  promotions: { ok: true, error: null, endpoint: "/api/v1/promotions", data: [normalizePromotion({ id: "p1", name: "Promo mayo", message_long: "2x1 en limpieza", status: "active", cta_label: "Reservar", starts_at: "2026-05-01T00:00:00Z", ends_at: "2026-05-31T23:59:59Z" })] },
  behavior: { ok: true, error: null, endpoint: "/api/v1/bot-studio/behavior", data: { bot_mode: "hybrid", tone: "warm", response_length: "medium", sales_intensity: "moderate", can_mention_stock: true } },
  verticalProfile: { ok: true, error: null, endpoint: "/api/v1/verticals/profile", data: normalizeVerticalProfile({ id: "vertical_dental", name: "Dental", short_name: "Dental", problem: "Falta seguimiento post consulta", objects: ["patients", "appointments"], flows: ["follow_up", "booking"], kpis: ["bookings"], selected_subvertical: { name: "Ortodoncia", promise: "Convertir valoraciones a tratamientos" }, runtime_connection: { active_subvertical: "Ortodoncia", pack_status: { coverage_score: 82 }, surface_focus: { portal: "seguimiento y agenda" } } }) },
} as const;

test("client portal timeline sorts newest first and flags pending work", () => {
  const timeline = buildClientPortalTimeline(data);
  assert.equal(timeline[0]?.id, "r1");
  assert.equal(timeline[1]?.id, "f1");
  assert.equal(hasPendingTimelineEntries(timeline), true);
});

test("client portal summary view model derives highlights and business context", () => {
  const timeline = buildClientPortalTimeline(data);
  const summary = buildClientPortalSummaryViewModel(data, timeline);
  assert.equal(summary.pendingCount, 2);
  assert.match(summary.executiveHighlights[0] || "", /conversacion/i);
  assert.match(summary.storyBeats.agenda.outcome, /(Limpieza|Valoración)/i);
  assert.equal(summary.businessContext.selectedSubvertical, "Ortodoncia");
  assert.equal(summary.businessContext.packCoverage, "82%");
});

test("client portal card view models keep UI mapping outside the component", () => {
  const conversationCards = buildConversationCardModels(data.conversations.data);
  const agenda = buildAgendaViewModel(data);
  const promotions = buildPromotionCardModels(data.promotions.data);
  const botAttributes = buildBotAttributeModels(data);
  assert.equal(conversationCards[0]?.title, "Ana");
  assert.equal(agenda.cards[0]?.title.includes("Valoración"), true);
  assert.equal(promotions[0]?.ctaLabel, "Reservar");
  assert.equal(botAttributes.some((item) => item.label === "Puede mencionar stock" && item.value === "Sí"), true);
});
