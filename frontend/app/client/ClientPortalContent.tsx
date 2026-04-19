import Link from "next/link";
import { Badge, KeyValueList, ModuleCard, Shell, StoryBeat, TimelineList } from "../components";
import {
  ClientAppointmentCard,
  ClientEmptyBlock,
  ClientExecutiveSummary,
  ClientMetricCard,
  ClientNotice,
  ClientSectionBlock,
  ClientConversationCard,
  ClientBotAttribute,
  ClientPromotionCard,
  ClientRequestCard,
} from "../components/client/ClientPortalPrimitives";
import { formatDate, formatDateTime, formatNumber, humanizeToken, safeText, summarizeCount, yesNo } from "../lib/ui";
import { getSession } from "../lib/session";
import { apiFetchOrDefault } from "../lib/api";
import { approveOperationalCommandAction, cancelOperationalCommandAction, confirmOperationalCommandAction, createAuthorizedOperationalNumberAction, executeRescheduleBatchAction, previewRescheduleBatchAction, submitOperationalCommandAction, undoOperationalCommandAction } from "../actions/operational_control";
import { getClientPortalData, type ClientPortalData, type PortalModuleState } from "../lib/waos";

export type ClientSection = "resumen" | "conversaciones" | "agenda" | "promociones" | "solicitudes" | "bot" | "operaciones";

type TimelineEntry = {
  id: string;
  title: string;
  detail: string;
  kind: string;
  status?: string;
  createdAt: string;
};

const sectionMeta: Record<ClientSection, { title: string; subtitle: string; actionHref: string; actionLabel: string }> = {
  resumen: {
    title: "Portal cliente",
    subtitle: "Una portada ejecutiva, clara y compartible para entender avance, pendientes y siguientes decisiones sin entrar al modo operativo.",
    actionHref: "/client/solicitudes",
    actionLabel: "Ver pendientes",
  },
  conversaciones: {
    title: "Conversaciones visibles",
    subtitle: "Actividad resumida para cliente final: qué conversaciones están activas, cuáles requieren atención humana y dónde hay contexto suficiente para decidir.",
    actionHref: "/client/agenda",
    actionLabel: "Ver agenda",
  },
  agenda: {
    title: "Agenda del cliente",
    subtitle: "Próximas citas y seguimiento en un formato cómodo de escanear desde móvil o escritorio, con fecha, estado y contexto listos para compartir.",
    actionHref: "/client/resumen",
    actionLabel: "Volver al resumen",
  },
  promociones: {
    title: "Promociones activas",
    subtitle: "Campañas visibles con mensaje, vigencia, CTA y estado, presentadas como piezas comerciales y no como tarjetas genéricas.",
    actionHref: "/client/resumen",
    actionLabel: "Volver al resumen",
  },
  solicitudes: {
    title: "Solicitudes y feedback",
    subtitle: "Centro de seguimiento entre cliente y equipo para entender qué se pidió, qué quedó resuelto y qué sigue esperando respuesta.",
    actionHref: "/client/resumen",
    actionLabel: "Volver al resumen",
  },
  bot: {
    title: "Salud del bot",
    subtitle: "Una lectura humana del comportamiento del bot: tono, modo, longitud, intensidad comercial y señales de configuración útiles para cliente no técnico.",
    actionHref: "/client/resumen",
    actionLabel: "Volver al resumen",
  },
  operaciones: {
    title: "Control operativo por WhatsApp y agenda",
    subtitle: "Un centro para bloquear horarios, cambiar el estado del bot y operar emergencias desde portal o WhatsApp con trazabilidad y confirmación.",
    actionHref: "/client/agenda",
    actionLabel: "Ver agenda",
  },
};

function loadedModuleNotices(modules: Array<{ label: string; state: PortalModuleState<unknown> }>) {
  return modules.filter((item) => !item.state.ok && item.state.error);
}

function buildTimeline(data: ClientPortalData): TimelineEntry[] {
  const requests = data.requests.data.map((item) => ({
    id: item.id,
    title: safeText(item.detail || item.message, "Solicitud del cliente"),
    detail: safeText(item.message || item.detail, "Sin detalle adicional"),
    kind: humanizeToken(item.kind, "Solicitud"),
    status: item.status || undefined,
    createdAt: formatDateTime(item.created_at),
    sortAt: item.created_at || "",
  }));
  const feedback = data.feedback.data.map((item) => ({
    id: item.id,
    title: safeText(item.detail || item.comment || item.message, "Feedback del cliente"),
    detail: safeText(item.comment || item.message || item.detail, "Sin detalle adicional"),
    kind: humanizeToken(item.kind, "Feedback"),
    status: undefined,
    createdAt: formatDateTime(item.created_at),
    sortAt: item.created_at || "",
  }));
  return [...requests, ...feedback]
    .sort((a, b) => String(b.sortAt).localeCompare(String(a.sortAt)))
    .map(({ sortAt, ...item }) => item);
}

function hasPendingRequests(entries: TimelineEntry[]) {
  return entries.some((item) => /pending|review|pendiente|open|abierto/i.test(String(item.status || "")) || /solicitud/i.test(item.kind.toLowerCase()));
}

function renderModuleErrors(modules: Array<{ label: string; state: PortalModuleState<unknown> }>) {
  const errors = loadedModuleNotices(modules);
  if (!errors.length) return null;
  return (
    <div className="space-y-3">
      {errors.map(({ label, state }) => (
        <ClientNotice
          key={label}
          title={`No pudimos refrescar ${label.toLowerCase()}`}
          description={state.error?.message || "La sección usó el último fallback disponible para no dejar la vista en blanco."}
          tone="warning"
          detail={`Endpoint verificado: ${state.endpoint}`}
          action={<Link href="/client/resumen" className="secondary-btn">Actualizar vista</Link>}
        />
      ))}
    </div>
  );
}

function renderSummary(data: ClientPortalData, timeline: TimelineEntry[]) {
  const conversations = data.conversations.data;
  const appointments = data.appointments.data;
  const promotions = data.promotions.data;
  const profile = data.verticalProfile.data;
  const pending = timeline.filter((item) => /pendiente|solicitud|review|feedback/i.test(`${item.kind} ${item.status || ""}`)).length;
  const nextAppointment = appointments[0];
  const executiveHighlights = [
    conversations.length
      ? `${summarizeCount("Conversaciones", conversations.length)}. Ya puedes revisar actividad sin abrir bandejas internas.`
      : "Hoy no hay conversaciones visibles para revisar.",
    nextAppointment
      ? `La próxima cita visible es ${safeText(nextAppointment.service_name, "una cita")} para ${safeText(nextAppointment.contact_name, "tu cliente")} el ${formatDateTime(nextAppointment.starts_at || nextAppointment.start_at || nextAppointment.scheduled_for)}.`
      : "No hay citas próximas visibles todavía.",
    pending
      ? `Hay ${formatNumber(pending)} puntos que merecen decisión o respuesta antes del siguiente corte.`
      : "No se ven decisiones abiertas en este momento.",
  ];

  return (
    <div className="space-y-6">
      <ClientExecutiveSummary
        title="Una portada pensada para entender qué pasó, qué sigue y qué puedes decidir en menos de un minuto"
        description="El portal cliente ya no depende de tablas frías ni de componentes genéricos. Esta vista prioriza progreso visible, actividad reciente, próximos pasos y señales del negocio para que cualquier persona no técnica pueda orientarse rápido."
        insights={executiveHighlights}
        cta={
          <>
            <Link href="/client/solicitudes" className="primary-btn">Revisar pendientes</Link>
            <Link href="/client/conversaciones" className="secondary-btn">Abrir conversaciones</Link>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <ClientMetricCard
          label="Conversaciones"
          value={formatNumber(conversations.length)}
          description={conversations.length ? "Actividad visible para seguimiento y toma de decisiones." : "Sin actividad visible por ahora."}
          icon="chat"
          tone="blue"
        />
        <ClientMetricCard
          label="Agenda"
          value={formatNumber(appointments.length)}
          description={nextAppointment ? `Próxima cita: ${formatDateTime(nextAppointment.starts_at || nextAppointment.start_at || nextAppointment.scheduled_for)}` : "Todavía no hay citas programadas visibles."}
          icon="calendar"
          tone="green"
        />
        <ClientMetricCard
          label="Pendientes"
          value={formatNumber(pending)}
          description={pending ? "Cambios, comentarios o aprobaciones que necesitan seguimiento." : "No hay decisiones abiertas registradas."}
          icon="folder"
          tone="gold"
        />
        <ClientMetricCard
          label="Promociones"
          value={formatNumber(promotions.length)}
          description={promotions.length ? "Campañas listas para revisar o compartir." : "No hay campañas activas visibles hoy."}
          icon="promo"
          tone="slate"
        />
      </div>

      <ClientSectionBlock title="Panorama actual" subtitle="Tres bloques para leer el estado del portal sin ruido técnico.">
        <div className="grid gap-4 xl:grid-cols-3">
          <StoryBeat
            step="Qué pasó"
            title="Actividad reciente"
            description={conversations.length ? `Se detectan ${formatNumber(conversations.length)} conversaciones con contexto suficiente para revisión.` : "Aún no hay conversaciones recientes visibles."}
            outcome={conversations[0] ? `Último resumen: ${safeText(conversations[0].summary, "Sin resumen")}` : "En cuanto exista actividad, aquí aparecerá la lectura ejecutiva."}
            tone="blue"
          />
          <StoryBeat
            step="Qué sigue"
            title="Agenda y seguimiento"
            description={appointments.length ? `Hay ${formatNumber(appointments.length)} citas registradas con estado visible para cliente.` : "No hay agenda visible por ahora."}
            outcome={nextAppointment ? `Siguiente cita: ${safeText(nextAppointment.service_name, "Cita")} · ${formatDateTime(nextAppointment.starts_at || nextAppointment.start_at || nextAppointment.scheduled_for)}` : "Cuando se programe seguimiento, aparecerá aquí."}
            tone="green"
          />
          <StoryBeat
            step="Qué decidir"
            title="Solicitudes y feedback"
            description={timeline.length ? `Se acumulan ${formatNumber(timeline.length)} interacciones entre solicitudes y comentarios.` : "No hay solicitudes ni comentarios abiertos."}
            outcome={timeline[0] ? `Más reciente: ${timeline[0].title}` : "Sin decisiones pendientes en este momento."}
            tone="gold"
          />
        </div>
      </ClientSectionBlock>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <ClientSectionBlock title="Actividad reciente" subtitle="La mezcla justa entre conversaciones y seguimiento, presentada de forma humana.">
          <div className="grid gap-4 lg:grid-cols-2">
            {conversations.slice(0, 2).map((item) => (
              <ClientConversationCard
                key={item.id}
                title={safeText(item.contact_name, "Contacto sin nombre")}
                summary={safeText(item.summary || item.latest_message_preview, "Sin resumen visible")}
                status={safeText(item.status, "sin dato")}
                meta={[
                  { label: "Bot", value: safeText(item.bot_name, "Sin bot") },
                  { label: "Prioridad", value: humanizeToken(item.urgency_level || item.attention_tier, "Normal") },
                  { label: "Actualización", value: formatDateTime(item.updated_at || item.last_inbound_at || item.last_outbound_at) },
                  { label: "Modo sugerido", value: humanizeToken(item.recommended_mode, "Automático") },
                ]}
                preview={safeText(item.latest_message_preview, "Sin vista previa disponible")}
              />
            ))}
            {!conversations.length ? <ClientEmptyBlock title="Aún no hay conversaciones visibles" description="Cuando exista actividad real, este bloque mostrará el resumen y el estado sin exponer bandejas internas." /> : null}
          </div>
        </ClientSectionBlock>

        <ClientSectionBlock title="Contexto del negocio" subtitle="Lo que WAOS ya entendió de la operación activa para darle sentido al portal.">
          <div className="grid gap-4">
            <ModuleCard
              title={safeText(profile.short_name || profile.name, "Vertical pendiente")}
              description={safeText(profile.problem, "Todavía no hay un perfil vertical visible para esta organización.")}
              tone="green"
              icon="layers"
            />
            <KeyValueList
              items={[
                { label: "Subvertical activa", value: safeText(profile.selected_subvertical?.name, (profile.runtime_connection?.active_subvertical as string) || "sin definir") },
                { label: "Pack aplicado", value: `${formatNumber(Number((profile.runtime_connection?.pack_status?.coverage_score as number) || 0))}%` },
                { label: "Objetos operativos", value: formatNumber(profile.objects.length) },
                { label: "Flujos esperados", value: formatNumber(profile.flows.length) },
                { label: "KPI sugeridos", value: formatNumber(profile.kpis.length) },
              ]}
            />
            <ModuleCard
              title="Promesa activa"
              description={safeText(profile.selected_subvertical?.promise, profile.ten_x_narrative || profile.problem || "Todavía no hay una promesa operativa visible para esta cuenta.")}
              tone="blue"
              icon="spark"
              footer={<div className="text-xs text-slate-400">Foco portal: {safeText(String(profile.runtime_connection?.surface_focus?.portal || 'resumen vertical'))}</div>}
            />
          </div>
        </ClientSectionBlock>
      </div>
    </div>
  );
}

function renderConversations(data: ClientPortalData) {
  const conversations = data.conversations.data;
  if (!conversations.length) {
    return <ClientEmptyBlock title="Todavía no hay conversaciones visibles" description="Cuando exista actividad real, esta sección mostrará estado, prioridad y resumen en un formato cómodo para cliente final." />;
  }
  return (
    <ClientSectionBlock
      title="Conversaciones activas y visibles"
      subtitle="Cada tarjeta resume contacto, estado, prioridad y contexto. La intención es poder compartir esta vista sin explicar terminología interna."
      aside={<Badge tone="sky">{formatNumber(conversations.length)} visibles</Badge>}
    >
      <div className="grid gap-4 lg:grid-cols-2">
        {conversations.map((item) => (
          <ClientConversationCard
            key={item.id}
            title={safeText(item.contact_name, "Contacto sin nombre")}
            summary={safeText(item.summary || item.latest_message_preview, "Sin resumen visible")}
            status={safeText(item.status, "sin dato")}
            meta={[
              { label: "Bot", value: safeText(item.bot_name, "Sin bot") },
              { label: "Etapa", value: humanizeToken(item.lead_stage, "Sin etapa") },
              { label: "Relación", value: humanizeToken(item.relationship_status || item.relationship_label, "Sin relación") },
              { label: "Actualización", value: formatDateTime(item.updated_at || item.last_inbound_at || item.last_outbound_at) },
            ]}
            preview={safeText(item.latest_message_preview, "Sin vista previa disponible")}
          />
        ))}
      </div>
    </ClientSectionBlock>
  );
}

function renderAgenda(data: ClientPortalData) {
  const appointments = [...data.appointments.data].sort((a, b) => String(a.starts_at || a.start_at || a.scheduled_for || "").localeCompare(String(b.starts_at || b.start_at || b.scheduled_for || "")));
  const summary = data.agendaOverview.data.summary || {};
  if (!appointments.length) {
    return <ClientEmptyBlock title="No hay citas visibles" description="En cuanto exista seguimiento programado, aquí verás cada cita con fecha, estado y contexto sin depender de tablas incómodas." />;
  }
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <ClientMetricCard label="Citas visibles" value={formatNumber(appointments.length)} description="Total recuperado desde backend para esta organización." icon="calendar" tone="green" />
        <ClientMetricCard label="Pendientes" value={formatNumber(Number(summary.pending || 0))} description="Espacios que aún esperan confirmación o seguimiento." icon="folder" tone="gold" />
        <ClientMetricCard label="Confirmadas" value={formatNumber(Number(summary.confirmed || 0))} description="Citas listas para ejecutarse o ya confirmadas." icon="stats" tone="blue" />
        <ClientMetricCard label="Próxima fecha" value={appointments[0] ? formatDate(appointments[0].starts_at || appointments[0].start_at || appointments[0].scheduled_for) : "Sin fecha"} description="Primer hito temporal visible en agenda." icon="calendar" tone="slate" />
      </div>
      <ClientSectionBlock title="Próximas citas" subtitle="Presentadas como tarjetas legibles en móvil y escritorio, con prioridad en fecha, estado y servicio.">
        <div className="grid gap-4 lg:grid-cols-2">
          {appointments.map((item) => (
            <ClientAppointmentCard
              key={item.id}
              title={`${safeText(item.service_name, "Cita")}${item.contact_name ? ` · ${item.contact_name}` : ""}`}
              when={formatDateTime(item.starts_at || item.start_at || item.scheduled_for)}
              status={safeText(item.status, "sin dato")}
              detail={item.payment_status ? `Estado de pago: ${humanizeToken(item.payment_status)}.` : "Seguimiento visible para esta cita."}
              chips={[
                safeText(item.contact_name, "Contacto sin nombre"),
                item.payment_status ? `Pago: ${humanizeToken(item.payment_status)}` : "Sin dato de pago",
                item.reconciliation_status ? `Conciliación: ${humanizeToken(item.reconciliation_status)}` : "Sin conciliación",
              ]}
            />
          ))}
        </div>
      </ClientSectionBlock>
    </div>
  );
}

function renderRequests(data: ClientPortalData, timeline: TimelineEntry[]) {
  if (!timeline.length) {
    return <ClientEmptyBlock title="No hay solicitudes abiertas" description="Cuando el cliente pida cambios o deje comentarios, esta sección mostrará el historial con mejor contexto y jerarquía visual." />;
  }
  return (
    <ClientSectionBlock
      title="Seguimiento de solicitudes y feedback"
      subtitle="Cada elemento diferencia tipo, estado y detalle para que se entienda el avance sin tener que interpretar una tabla técnica."
      aside={<Badge tone={hasPendingRequests(timeline) ? "gold" : "green"}>{hasPendingRequests(timeline) ? "Hay pendientes" : "Todo al día"}</Badge>}
    >
      <div className="grid gap-4 lg:grid-cols-2">
        {timeline.map((item) => (
          <ClientRequestCard
            key={item.id}
            title={item.title}
            detail={item.detail}
            kind={item.kind}
            status={item.status}
            createdAt={item.createdAt}
          />
        ))}
      </div>
    </ClientSectionBlock>
  );
}

function renderPromotions(data: ClientPortalData) {
  const promotions = data.promotions.data;
  if (!promotions.length) {
    return <ClientEmptyBlock title="No hay promociones activas" description="Cuando exista una campaña visible para cliente, la verás aquí con vigencia, CTA y mensaje en formato comercial." />;
  }
  return (
    <ClientSectionBlock title="Campañas y promociones" subtitle="Presentadas como piezas compartibles con CTA visible, vigencia y estado para dar más valor percibido.">
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {promotions.map((item) => (
          <ClientPromotionCard
            key={item.id}
            title={safeText(item.name, "Promoción")}
            message={safeText(item.message_long || item.message_short, "Promoción sin copy visible")}
            validity={item.starts_at || item.ends_at ? `${formatDate(item.starts_at)} — ${formatDate(item.ends_at)}` : "Vigencia sin fecha visible"}
            status={safeText(item.status, "activa")}
            ctaLabel={safeText(item.cta_label, "Sin CTA visible")}
          />
        ))}
      </div>
    </ClientSectionBlock>
  );
}

function renderBot(data: ClientPortalData) {
  const behavior = data.behavior.data;
  if (!data.context.botId) {
    return <ClientEmptyBlock title="Todavía no hay un bot seleccionado" description="El portal cliente respeta el contexto activo. Cuando exista un bot visible para esta organización, aquí mostraremos una lectura clara de su comportamiento." />;
  }
  return (
    <div className="space-y-6">
      <ClientSectionBlock title="Lectura resumida del bot" subtitle="Campos explicados en lenguaje claro para que el cliente entienda cómo está respondiendo el bot sin ver configuración interna.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <ClientBotAttribute label="Modo" value={humanizeToken(behavior.bot_mode, "Sin definir")} description="En qué tono de operación está enfocado el bot en este momento." />
          <ClientBotAttribute label="Tono" value={humanizeToken(behavior.tone, "Sin definir")} description="Cómo suena el bot frente al cliente final." />
          <ClientBotAttribute label="Longitud" value={humanizeToken(behavior.response_length, "Sin definir")} description="Qué tan extensas tienden a ser las respuestas." />
          <ClientBotAttribute label="Intensidad comercial" value={humanizeToken(behavior.sales_intensity, "Sin definir")} description="Qué tan directo es el bot al empujar una conversión." />
          <ClientBotAttribute label="Puede mencionar stock" value={yesNo(behavior.can_mention_stock)} description="Si está autorizado a responder sobre disponibilidad de inventario." />
          <ClientBotAttribute label="Bot activo" value={safeText(data.context.botId, "Sin bot")} description="Identificador visible del bot en el contexto actual para evitar mezclar tenants." />
        </div>
      </ClientSectionBlock>
    </div>
  );
}



async function renderOperations(data: ClientPortalData) {
  if (!data.context.organizationId || !data.context.botId) {
    return <ClientEmptyBlock title="No hay contexto operativo activo" description="Selecciona una organización y un bot para habilitar el control operativo por portal o WhatsApp." />;
  }
  const organizationId = data.context.organizationId;
  const botId = data.context.botId;
  const summary = await apiFetchOrDefault(`/api/v1/client/operations/summary?organization_id=${encodeURIComponent(organizationId)}&bot_id=${encodeURIComponent(botId)}`, { bot: {}, counts: {}, recent_commands: [], authorized_numbers: [], scheduled_actions: [], upcoming_appointments: [] });
  const availability = await apiFetchOrDefault(`/api/v1/client/operations/availability?organization_id=${encodeURIComponent(organizationId)}&bot_id=${encodeURIComponent(botId)}&day=today`, { summary: {}, appointments: [], overrides: [] });
  const metrics = await apiFetchOrDefault(`/api/v1/client/operations/metrics?organization_id=${encodeURIComponent(organizationId)}&bot_id=${encodeURIComponent(botId)}&window_days=7`, { summary: {}, intents: [], statuses: [] });
  const alerts = await apiFetchOrDefault(`/api/v1/client/operations/alerts?organization_id=${encodeURIComponent(organizationId)}&bot_id=${encodeURIComponent(botId)}`, []);
  const recentCommands = Array.isArray((summary as any).recent_commands) ? (summary as any).recent_commands : [];
  const authorizedNumbers = Array.isArray((summary as any).authorized_numbers) ? (summary as any).authorized_numbers : [];
  const bot = ((summary as any).bot || {}) as Record<string, unknown>;
  const counts = ((summary as any).counts || {}) as Record<string, unknown>;

  return (
    <div className="space-y-6">
      <ClientExecutiveSummary
        title="Opera la agenda y el estado del bot sin salir del portal"
        description="Esta vista unifica control operativo, números autorizados y comandos en lenguaje natural. Los cambios masivos exigen confirmación y quedan auditados."
        insights={[
          `Estado actual: ${safeText(String(bot.operational_state || bot.current_state || bot.status || 'sin estado'), 'sin estado')}.`,
          `Números autorizados: ${formatNumber(Number(counts.authorized_numbers || 0))}.`,
          `Comandos recientes: ${formatNumber(Number(counts.recent_commands || 0))}.`,
        ]}
        cta={<Link href="/client/agenda" className="primary-btn">Revisar citas afectadas</Link>}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <ClientMetricCard label="Estado bot" value={safeText(String(bot.operational_state || bot.current_state || 'active'), 'active')} description={safeText(String(bot.temp_unavailability_message || 'Sin mensaje temporal'), 'Sin mensaje temporal')} icon="bot" tone="blue" />
        <ClientMetricCard label="Comandos 7d" value={formatNumber(Number((metrics as any).summary?.total || counts.recent_commands || 0))} description="Actividad operativa reciente registrada para este bot." icon="tool" tone="gold" />
        <ClientMetricCard label="Autorizados" value={formatNumber(Number(counts.authorized_numbers || 0))} description="Números que sí pueden operar por WhatsApp." icon="shield" tone="green" />
        <ClientMetricCard label="Alto impacto" value={formatNumber(Number((metrics as any).summary?.high_risk || 0))} description="Comandos de alto impacto creados en la última semana." icon="alert" tone="slate" />
        <ClientMetricCard label="Alertas abiertas" value={formatNumber(Number((metrics as any).summary?.alerts_open || counts.alerts_open || 0))} description="Eventos operativos que requieren seguimiento." icon="alert" tone="gold" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <ClientSectionBlock title="Reprogramación masiva guiada" subtitle="Haz preview y ejecución con matching real de slots usando la capacidad declarada.">
          <div className="grid gap-3 lg:grid-cols-2">
            <form action={previewRescheduleBatchAction} className="grid gap-3 rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
              <input type="hidden" name="organization_id" value={organizationId} />
              <input type="hidden" name="bot_id" value={botId} />
              <input type="hidden" name="redirect_to" value="/client/operaciones" />
              <input name="scope_day" defaultValue="tomorrow" placeholder="today | tomorrow | custom" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
              <input name="target_date" placeholder="2026-04-20" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
              <input name="target_start_time" defaultValue="09:00" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
              <input name="target_end_time" defaultValue="18:00" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
              <input name="delay_minutes" defaultValue="30" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
              <button type="submit" className="secondary-btn">Simular reprogramación</button>
            </form>
            <form action={executeRescheduleBatchAction} className="grid gap-3 rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
              <input type="hidden" name="organization_id" value={organizationId} />
              <input type="hidden" name="bot_id" value={botId} />
              <input type="hidden" name="redirect_to" value="/client/operaciones" />
              <input name="scope_day" defaultValue="tomorrow" placeholder="today | tomorrow | custom" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
              <input name="target_date" placeholder="2026-04-20" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
              <input name="target_start_time" defaultValue="09:00" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
              <input name="target_end_time" defaultValue="18:00" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
              <input name="delay_minutes" defaultValue="30" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
              <label className="flex items-center gap-2 text-sm text-[color:var(--text-secondary)]"><input type="checkbox" name="notify_clients" /> Notificar clientes</label>
              <button type="submit" className="primary-btn">Ejecutar reprogramación</button>
            </form>
          </div>
        </ClientSectionBlock>


        <ClientSectionBlock title="Comando libre" subtitle="Escribe un comando natural como 'bloquéame mañana de 2 a 6' o 'apaga el bot'.">
          <form action={submitOperationalCommandAction} className="space-y-4">
            <input type="hidden" name="organization_id" value={organizationId} />
            <input type="hidden" name="bot_id" value={botId} />
            <input type="hidden" name="redirect_to" value="/client/operaciones" />
            <textarea name="text" rows={4} className="w-full rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm text-[color:var(--text-primary)]" placeholder="Ejemplo: avísale a mis citas de hoy que voy 30 minutos tarde" />
            <div className="flex flex-wrap gap-3">
              <button type="submit" name="mode" value="preview" className="secondary-btn">Simular impacto</button>
              <button type="submit" name="mode" value="execute" className="primary-btn">Ejecutar comando</button>
            </div>
          </form>
        </ClientSectionBlock>

        <ClientSectionBlock title="Autorizar número" subtitle="Da de alta números que sí pueden controlar el bot por WhatsApp.">
          <form action={createAuthorizedOperationalNumberAction} className="grid gap-3">
            <input type="hidden" name="organization_id" value={organizationId} />
            <input type="hidden" name="bot_id" value={botId} />
            <input type="hidden" name="redirect_to" value="/client/operaciones" />
            <input name="phone_e164" placeholder="+5215550001111" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
            <input name="role" placeholder="owner" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
            <input name="allowed_intents" placeholder="appointment.notify_affected,bot.pause" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
            <input name="scope_branches" placeholder="Centro,Norte" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
            <input name="scope_resource_names" placeholder="Dra. Ana,Dr. Luis" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
            <input name="scope_service_names" placeholder="Limpieza,Consulta" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
            <button type="submit" className="primary-btn">Autorizar número</button>
          </form>
          <div className="mt-4 space-y-3">
            {authorizedNumbers.length ? authorizedNumbers.slice(0, 4).map((item: any) => (
              <div key={String(item.id)} className="surface-row">
                <div className="font-medium text-[color:var(--text-primary)]">{safeText(String(item.phone_e164 || ''), 'Sin número')}</div>
                <div className="text-sm text-[color:var(--text-secondary)]">{safeText(String(item.role || 'owner'), 'owner')} · {safeText(String(item.status || 'verified'), 'verified')} · {safeText(String(item.scope_summary || 'Sin restricción'), 'Sin restricción')}</div>
              </div>
            )) : <ClientEmptyBlock title="Sin números autorizados" description="Hasta que autorices un número, los mensajes por chat no ejecutarán comandos operativos." />}
          </div>
        </ClientSectionBlock>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <ClientSectionBlock title="Alertas operativas" subtitle="Abuso, rate limits y ejecuciones parciales que requieren seguimiento.">
          <div className="space-y-3">
            {Array.isArray(alerts) && alerts.length ? (alerts as any[]).slice(0, 6).map((item) => (
              <div key={String(item.id)} className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={String(item.severity || 'warning') === 'critical' ? 'gold' : 'slate'}>{safeText(String(item.alert_type || 'alerta'), 'alerta')}</Badge>
                  <Badge tone="sky">{safeText(String(item.status || 'open'), 'open')}</Badge>
                </div>
                <div className="mt-3 font-medium text-[color:var(--text-primary)]">{safeText(String(item.title || 'Alerta operativa'), 'Alerta operativa')}</div>
                <div className="mt-2 text-sm text-[color:var(--text-secondary)]">{safeText(String(item.body || ''), '')}</div>
              </div>
            )) : <ClientEmptyBlock title="Sin alertas abiertas" description="Cuando haya abuso, rate limits o fallos parciales, aparecerán aquí." />}
          </div>
        </ClientSectionBlock>

        <ClientSectionBlock title="Comandos recientes" subtitle="Incluye previews, comandos confirmados y acciones cancelables.">
          <div className="space-y-3">
            {recentCommands.length ? recentCommands.map((item: any) => (
              <div key={String(item.id)} className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={String(item.risk_level || 'low') === 'high' ? 'gold' : 'sky'}>{safeText(String(item.detected_intent || 'sin intención'), 'sin intención')}</Badge>
                  <Badge tone="slate">{safeText(String(item.status || 'queued'), 'queued')}</Badge>
                  {item.requires_confirmation ? <Badge tone="gold">Requiere confirmación</Badge> : null}
                </div>
                <div className="mt-3 text-sm text-[color:var(--text-secondary)]">{safeText(String(item.result?.reply_text || item.result?.preview?.impact?.appointments_affected || item.created_at || ''), 'Sin detalle')}</div>
                <div className="mt-3 flex flex-wrap gap-3">
                  {String(item.status) === 'awaiting_confirmation' ? (
                    <>
                      <form action={confirmOperationalCommandAction}>
                        <input type="hidden" name="command_id" value={String(item.id)} />
                        <input type="hidden" name="confirmation_code" value={safeText(String(item.confirmation_code || ''), '')} />
                        <input type="hidden" name="redirect_to" value="/client/operaciones" />
                        <button type="submit" className="secondary-btn">Confirmar</button>
                      </form>
                      <form action={cancelOperationalCommandAction}>
                        <input type="hidden" name="command_id" value={String(item.id)} />
                        <input type="hidden" name="reason" value="cancelled_from_portal" />
                        <input type="hidden" name="redirect_to" value="/client/operaciones" />
                        <button type="submit" className="secondary-btn">Cancelar</button>
                      </form>
                    </>
                  ) : null}
                  {String(item.status) === 'awaiting_second_approval' ? (
                    <form action={approveOperationalCommandAction}>
                      <input type="hidden" name="command_id" value={String(item.id)} />
                      <input type="hidden" name="note" value="approved_from_portal" />
                      <input type="hidden" name="redirect_to" value="/client/operaciones" />
                      <button type="submit" className="secondary-btn">Aprobar segundo paso</button>
                    </form>
                  ) : null}
                  {['executed','partially_reverted'].includes(String(item.status)) && item.undoable_until ? (
                    <form action={undoOperationalCommandAction}>
                      <input type="hidden" name="command_id" value={String(item.id)} />
                      <input type="hidden" name="reason" value="undo_from_portal" />
                      <input type="hidden" name="redirect_to" value="/client/operaciones" />
                      <button type="submit" className="secondary-btn">Deshacer</button>
                    </form>
                  ) : null}
                </div>
              </div>
            )) : <ClientEmptyBlock title="Sin comandos recientes" description="Cuando operes disponibilidad o estado del bot, aquí quedará el historial." />}
          </div>
        </ClientSectionBlock>

        <ClientSectionBlock title="Disponibilidad y citas de hoy" subtitle="Lectura rápida del impacto operativo visible para hoy.">
          <div className="space-y-3">
            <KeyValueList items={[
              { label: 'Citas hoy', value: formatNumber(Number((availability as any).summary?.appointments || 0)) },
              { label: 'Bloqueos', value: formatNumber(Number((availability as any).summary?.blocked_ranges || 0)) },
              { label: 'Excepciones abiertas', value: formatNumber(Number((availability as any).summary?.open_exceptions || 0)) },
            ]} />
            <TimelineList items={(((availability as any).appointments || []) as any[]).slice(0, 6).map((item) => ({ title: `Cita ${safeText(String(item.id || ''), '')}`, detail: `${safeText(String(item.status || 'scheduled'), 'scheduled')} · ${formatDateTime(String(item.scheduled_for || ''))}`, tone: 'slate' as const }))} />
          </div>
        </ClientSectionBlock>
      </div>
    </div>
  );
}
export async function ClientPortalContent({ section }: { section: ClientSection }) {
  const session = await getSession();
  const currentOrg = session?.user.organizations?.find((item) => item.id === session?.organizationId) || null;
  const data = await getClientPortalData(section, currentOrg?.vertical);
  const timeline = buildTimeline(data);
  const meta = sectionMeta[section];

  const modulesForErrors: Array<{ label: string; state: PortalModuleState<unknown> }> = [
    { label: "Conversaciones", state: data.conversations },
    { label: "Agenda", state: data.appointments },
    { label: "Resumen de agenda", state: data.agendaOverview },
    { label: "Solicitudes", state: data.requests },
    { label: "Feedback", state: data.feedback },
    { label: "Promociones", state: data.promotions },
    { label: "Bot", state: data.behavior },
    { label: "Perfil vertical", state: data.verticalProfile },
  ];

  return (
    <Shell
      mode="client"
      title={meta.title}
      subtitle={meta.subtitle}
      action={<Link href={meta.actionHref} className="primary-btn">{meta.actionLabel}</Link>}
    >
      <div className="space-y-6">
        {renderModuleErrors(modulesForErrors)}
        {section === "resumen" ? renderSummary(data, timeline) : null}
        {section === "conversaciones" ? renderConversations(data) : null}
        {section === "agenda" ? renderAgenda(data) : null}
        {section === "solicitudes" ? renderRequests(data, timeline) : null}
        {section === "promociones" ? renderPromotions(data) : null}
        {section === "bot" ? renderBot(data) : null}
        {section === "operaciones" ? await renderOperations(data) : null}
      </div>
    </Shell>
  );
}
