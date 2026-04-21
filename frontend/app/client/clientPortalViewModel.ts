import type { ClientPortalData, PortalModuleState } from "../lib/waos";
import { formatDate, formatDateTime, formatNumber, humanizeToken, safeText, summarizeCount, yesNo } from "../lib/ui";

export type ClientSection = "resumen" | "conversaciones" | "agenda" | "promociones" | "solicitudes" | "bot" | "operaciones";
export type ClientTimelineEntry = { id: string; title: string; detail: string; kind: string; status?: string; createdAt: string };

export const clientSectionMeta: Record<ClientSection, { title: string; subtitle: string; actionHref: string; actionLabel: string }> = {
  resumen: { title: "Portal cliente", subtitle: "Una portada ejecutiva, clara y compartible para entender avance, pendientes y siguientes decisiones sin entrar al modo operativo.", actionHref: "/client/solicitudes", actionLabel: "Ver pendientes" },
  conversaciones: { title: "Conversaciones visibles", subtitle: "Actividad resumida para cliente final: qué conversaciones están activas, cuáles requieren atención humana y dónde hay contexto suficiente para decidir.", actionHref: "/client/agenda", actionLabel: "Ver agenda" },
  agenda: { title: "Agenda del cliente", subtitle: "Próximas citas y seguimiento en un formato cómodo de escanear desde móvil o escritorio, con fecha, estado y contexto listos para compartir.", actionHref: "/client/resumen", actionLabel: "Volver al resumen" },
  promociones: { title: "Promociones activas", subtitle: "Campañas visibles con mensaje, vigencia, CTA y estado, presentadas como piezas comerciales y no como tarjetas genéricas.", actionHref: "/client/resumen", actionLabel: "Volver al resumen" },
  solicitudes: { title: "Solicitudes y feedback", subtitle: "Centro de seguimiento entre cliente y equipo para entender qué se pidió, qué quedó resuelto y qué sigue esperando respuesta.", actionHref: "/client/resumen", actionLabel: "Volver al resumen" },
  bot: { title: "Salud del bot", subtitle: "Una lectura humana del comportamiento del bot: tono, modo, longitud, intensidad comercial y señales de configuración útiles para cliente no técnico.", actionHref: "/client/resumen", actionLabel: "Volver al resumen" },
  operaciones: { title: "Control operativo por WhatsApp y agenda", subtitle: "Un centro para bloquear horarios, cambiar el estado del bot y operar emergencias desde portal o WhatsApp con trazabilidad y confirmación.", actionHref: "/client/agenda", actionLabel: "Ver agenda" },
};

export function loadedModuleNotices(modules: Array<{ label: string; state: PortalModuleState<unknown> }>) {
  return modules.filter((item) => !item.state.ok && item.state.error);
}

export function buildClientPortalTimeline(data: ClientPortalData): ClientTimelineEntry[] {
  const requests = data.requests.data.map((item) => ({ id: item.id, title: safeText(item.detail || item.message, "Solicitud del cliente"), detail: safeText(item.message || item.detail, "Sin detalle adicional"), kind: humanizeToken(item.kind, "Solicitud"), status: item.status || undefined, createdAt: formatDateTime(item.created_at), sortAt: item.created_at || "" }));
  const feedback = data.feedback.data.map((item) => ({ id: item.id, title: safeText(item.detail || item.comment || item.message, "Feedback del cliente"), detail: safeText(item.comment || item.message || item.detail, "Sin detalle adicional"), kind: humanizeToken(item.kind, "Feedback"), status: undefined, createdAt: formatDateTime(item.created_at), sortAt: item.created_at || "" }));
  return [...requests, ...feedback].sort((a, b) => String(b.sortAt).localeCompare(String(a.sortAt))).map(({ sortAt, ...item }) => item);
}

export function hasPendingTimelineEntries(entries: ClientTimelineEntry[]) {
  return entries.some((item) => /pending|review|pendiente|open|abierto/i.test(String(item.status || "")) || /solicitud/i.test(item.kind.toLowerCase()));
}

export function buildConversationCardModels(conversations: ClientPortalData["conversations"]["data"]) {
  return conversations.map((item) => ({
    id: item.id,
    title: safeText(item.contact_name, "Contacto sin nombre"),
    summary: safeText(item.summary || item.latest_message_preview, "Sin resumen visible"),
    status: safeText(item.status, "sin dato"),
    preview: safeText(item.latest_message_preview, "Sin vista previa disponible"),
    meta: [
      { label: "Bot", value: safeText(item.bot_name, "Sin bot") },
      { label: "Etapa", value: humanizeToken(item.lead_stage, "Sin etapa") },
      { label: "Relación", value: humanizeToken(item.relationship_status || item.relationship_label, "Sin relación") },
      { label: "Actualización", value: formatDateTime(item.updated_at || item.last_inbound_at || item.last_outbound_at) },
    ],
  }));
}

export function buildSummaryConversationCardModels(conversations: ClientPortalData["conversations"]["data"]) {
  return conversations.slice(0, 2).map((item) => ({
    id: item.id,
    title: safeText(item.contact_name, "Contacto sin nombre"),
    summary: safeText(item.summary || item.latest_message_preview, "Sin resumen visible"),
    status: safeText(item.status, "sin dato"),
    preview: safeText(item.latest_message_preview, "Sin vista previa disponible"),
    meta: [
      { label: "Bot", value: safeText(item.bot_name, "Sin bot") },
      { label: "Prioridad", value: humanizeToken(item.urgency_level || item.attention_tier, "Normal") },
      { label: "Actualización", value: formatDateTime(item.updated_at || item.last_inbound_at || item.last_outbound_at) },
      { label: "Modo sugerido", value: humanizeToken(item.recommended_mode, "Automático") },
    ],
  }));
}

export function buildAgendaViewModel(data: ClientPortalData) {
  const appointments = [...data.appointments.data].sort((a, b) => String(a.starts_at || a.start_at || a.scheduled_for || "").localeCompare(String(b.starts_at || b.start_at || b.scheduled_for || "")));
  const summary = data.agendaOverview.data.summary || {};
  return {
    appointments,
    metrics: {
      visibleCount: formatNumber(appointments.length),
      pendingCount: formatNumber(Number(summary.pending || 0)),
      confirmedCount: formatNumber(Number(summary.confirmed || 0)),
      nextDateLabel: appointments[0] ? formatDate(appointments[0].starts_at || appointments[0].start_at || appointments[0].scheduled_for) : "Sin fecha",
    },
    cards: appointments.map((item) => ({
      id: item.id,
      title: `${safeText(item.service_name, "Cita")}${item.contact_name ? ` · ${item.contact_name}` : ""}`,
      when: formatDateTime(item.starts_at || item.start_at || item.scheduled_for),
      status: safeText(item.status, "sin dato"),
      detail: item.payment_status ? `Estado de pago: ${humanizeToken(item.payment_status)}.` : "Seguimiento visible para esta cita.",
      chips: [safeText(item.contact_name, "Contacto sin nombre"), item.payment_status ? `Pago: ${humanizeToken(item.payment_status)}` : "Sin dato de pago", item.reconciliation_status ? `Conciliación: ${humanizeToken(item.reconciliation_status)}` : "Sin conciliación"],
    })),
  };
}

export function buildRequestCardModels(entries: ClientTimelineEntry[]) {
  return entries.map((item) => ({ id: item.id, title: item.title, detail: item.detail, kind: item.kind, status: item.status, createdAt: item.createdAt }));
}

export function buildPromotionCardModels(promotions: ClientPortalData["promotions"]["data"]) {
  return promotions.map((item) => ({ id: item.id, title: safeText(item.name, "Promoción"), message: safeText(item.message_long || item.message_short, "Promoción sin copy visible"), validity: item.starts_at || item.ends_at ? `${formatDate(item.starts_at)} — ${formatDate(item.ends_at)}` : "Vigencia sin fecha visible", status: safeText(item.status, "activa"), ctaLabel: safeText(item.cta_label, "Sin CTA visible") }));
}

export function buildBotAttributeModels(data: ClientPortalData) {
  const behavior = data.behavior.data;
  return [
    { label: "Modo", value: humanizeToken(behavior.bot_mode, "Sin definir"), description: "En qué tono de operación está enfocado el bot en este momento." },
    { label: "Tono", value: humanizeToken(behavior.tone, "Sin definir"), description: "Cómo suena el bot frente al cliente final." },
    { label: "Longitud", value: humanizeToken(behavior.response_length, "Sin definir"), description: "Qué tan extensas tienden a ser las respuestas." },
    { label: "Intensidad comercial", value: humanizeToken(behavior.sales_intensity, "Sin definir"), description: "Qué tan directo es el bot al empujar una conversión." },
    { label: "Puede mencionar stock", value: yesNo(behavior.can_mention_stock), description: "Si está autorizado a responder sobre disponibilidad de inventario." },
    { label: "Bot activo", value: safeText(data.context.botId, "Sin bot"), description: "Identificador visible del bot que alimenta este portal." },
  ];
}

export function buildClientPortalSummaryViewModel(data: ClientPortalData, timeline: ClientTimelineEntry[]) {
  const conversations = data.conversations.data;
  const appointments = data.appointments.data;
  const promotions = data.promotions.data;
  const profile = data.verticalProfile.data;
  const pendingCount = timeline.filter((item) => /pendiente|solicitud|review|feedback/i.test(`${item.kind} ${item.status || ""}`)).length;
  const nextAppointment = appointments[0];
  return {
    pendingCount,
    executiveHighlights: [
      conversations.length ? `${summarizeCount("Conversaciones", conversations.length)}. Ya puedes revisar actividad sin abrir bandejas internas.` : "Hoy no hay conversaciones visibles para revisar.",
      nextAppointment ? `La próxima cita visible es ${safeText(nextAppointment.service_name, "una cita")} para ${safeText(nextAppointment.contact_name, "tu cliente")} el ${formatDateTime(nextAppointment.starts_at || nextAppointment.start_at || nextAppointment.scheduled_for)}.` : "No hay citas próximas visibles todavía.",
      pendingCount ? `Hay ${formatNumber(pendingCount)} puntos que merecen decisión o respuesta antes del siguiente corte.` : "No se ven decisiones abiertas en este momento.",
    ],
    metrics: {
      conversations: { value: formatNumber(conversations.length), description: conversations.length ? "Actividad visible para seguimiento y toma de decisiones." : "Sin actividad visible por ahora." },
      agenda: { value: formatNumber(appointments.length), description: nextAppointment ? `Próxima cita: ${formatDateTime(nextAppointment.starts_at || nextAppointment.start_at || nextAppointment.scheduled_for)}` : "Todavía no hay citas programadas visibles." },
      pending: { value: formatNumber(pendingCount), description: pendingCount ? "Cambios, comentarios o aprobaciones que necesitan seguimiento." : "No hay decisiones abiertas registradas." },
      promotions: { value: formatNumber(promotions.length), description: promotions.length ? "Campañas listas para revisar o compartir." : "No hay campañas activas visibles hoy." },
    },
    storyBeats: {
      activity: { description: conversations.length ? `Se detectan ${formatNumber(conversations.length)} conversaciones con contexto suficiente para revisión.` : "Aún no hay conversaciones recientes visibles.", outcome: conversations[0] ? `Último resumen: ${safeText(conversations[0].summary, "Sin resumen")}` : "En cuanto exista actividad, aquí aparecerá la lectura ejecutiva." },
      agenda: { description: appointments.length ? `Hay ${formatNumber(appointments.length)} citas registradas con estado visible para cliente.` : "No hay agenda visible por ahora.", outcome: nextAppointment ? `Siguiente cita: ${safeText(nextAppointment.service_name, "Cita")} · ${formatDateTime(nextAppointment.starts_at || nextAppointment.start_at || nextAppointment.scheduled_for)}` : "Cuando se programe seguimiento, aparecerá aquí." },
      decisions: { description: timeline.length ? `Se acumulan ${formatNumber(timeline.length)} interacciones entre solicitudes y comentarios.` : "No hay solicitudes ni comentarios abiertos.", outcome: timeline[0] ? `Más reciente: ${timeline[0].title}` : "Sin decisiones pendientes en este momento." },
    },
    businessContext: {
      verticalTitle: safeText(profile.short_name || profile.name, "Vertical pendiente"),
      verticalProblem: safeText(profile.problem, "Todavía no hay un perfil vertical visible para esta organización."),
      selectedSubvertical: safeText(profile.selected_subvertical?.name, (profile.runtime_connection?.active_subvertical as string) || "sin definir"),
      packCoverage: `${formatNumber(Number((profile.runtime_connection?.pack_status?.coverage_score as number) || 0))}%`,
      objectsCount: formatNumber(profile.objects.length),
      flowsCount: formatNumber(profile.flows.length),
      kpiCount: formatNumber(profile.kpis.length),
      promise: safeText(profile.selected_subvertical?.promise, profile.ten_x_narrative || profile.problem || "Todavía no hay una promesa operativa visible para esta cuenta."),
      focus: safeText(String(profile.runtime_connection?.surface_focus?.portal || "resumen vertical")),
    },
    topConversations: buildSummaryConversationCardModels(conversations),
  };
}
