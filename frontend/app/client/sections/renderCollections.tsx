import { Badge } from "@/app/components/primitives/shared";
import {
  ClientAppointmentCard,
  ClientBotAttribute,
  ClientConversationCard,
  ClientEmptyBlock,
  ClientMetricCard,
  ClientPromotionCard,
  ClientRequestCard,
  ClientSectionBlock,
} from "../../components/client/ClientPortalPrimitives";
import { formatNumber } from "../../lib/ui";
import type { ClientPortalData } from "@/app/lib/data/client-portal";
import { buildAgendaViewModel, buildBotAttributeModels, buildConversationCardModels, buildPromotionCardModels, buildRequestCardModels, hasPendingTimelineEntries, type ClientTimelineEntry } from "../clientPortalViewModel";

export function renderConversations(data: ClientPortalData) {
  const conversations = buildConversationCardModels(data.conversations.data);
  if (!conversations.length) {
    return <ClientEmptyBlock title="Todavía no hay conversaciones visibles" description="Cuando exista actividad real, esta sección mostrará estado, prioridad y resumen en un formato cómodo para cliente final." />;
  }
  return (
    <ClientSectionBlock title="Conversaciones activas y visibles" subtitle="Cada tarjeta resume contacto, estado, prioridad y contexto. La intención es poder compartir esta vista sin explicar terminología interna." aside={<Badge tone="sky">{formatNumber(conversations.length)} visibles</Badge>}>
      <div className="grid gap-4 lg:grid-cols-2">
        {conversations.map((item) => (
          <ClientConversationCard key={item.id} title={item.title} summary={item.summary} status={item.status} meta={item.meta} preview={item.preview} />
        ))}
      </div>
    </ClientSectionBlock>
  );
}

export function renderAgenda(data: ClientPortalData) {
  const agenda = buildAgendaViewModel(data);
  if (!agenda.appointments.length) {
    return <ClientEmptyBlock title="No hay citas visibles" description="En cuanto exista seguimiento programado, aquí verás cada cita con fecha, estado y contexto sin depender de tablas incómodas." />;
  }
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <ClientMetricCard label="Citas visibles" value={agenda.metrics.visibleCount} description="Total recuperado desde backend para esta organización." icon="calendar" tone="green" />
        <ClientMetricCard label="Pendientes" value={agenda.metrics.pendingCount} description="Espacios que aún esperan confirmación o seguimiento." icon="folder" tone="gold" />
        <ClientMetricCard label="Confirmadas" value={agenda.metrics.confirmedCount} description="Citas listas para ejecutarse o ya confirmadas." icon="stats" tone="blue" />
        <ClientMetricCard label="Próxima fecha" value={agenda.metrics.nextDateLabel} description="Primer hito temporal visible en agenda." icon="calendar" tone="slate" />
      </div>
      <ClientSectionBlock title="Próximas citas" subtitle="Presentadas como tarjetas legibles en móvil y escritorio, con prioridad en fecha, estado y servicio.">
        <div className="grid gap-4 lg:grid-cols-2">
          {agenda.cards.map((item) => (
            <ClientAppointmentCard key={item.id} title={item.title} when={item.when} status={item.status} detail={item.detail} chips={item.chips} />
          ))}
        </div>
      </ClientSectionBlock>
    </div>
  );
}

export function renderRequests(_data: ClientPortalData, timeline: ClientTimelineEntry[]) {
  if (!timeline.length) {
    return <ClientEmptyBlock title="No hay solicitudes abiertas" description="Cuando el cliente pida cambios o deje comentarios, esta sección mostrará el historial con mejor contexto y jerarquía visual." />;
  }
  return (
    <ClientSectionBlock title="Seguimiento de solicitudes y feedback" subtitle="Cada elemento diferencia tipo, estado y detalle para que se entienda el avance sin tener que interpretar una tabla técnica." aside={<Badge tone={hasPendingTimelineEntries(timeline) ? "gold" : "green"}>{hasPendingTimelineEntries(timeline) ? "Hay pendientes" : "Todo al día"}</Badge>}>
      <div className="grid gap-4 lg:grid-cols-2">
        {buildRequestCardModels(timeline).map((item) => (
          <ClientRequestCard key={item.id} title={item.title} detail={item.detail} kind={item.kind} status={item.status} createdAt={item.createdAt} />
        ))}
      </div>
    </ClientSectionBlock>
  );
}

export function renderPromotions(data: ClientPortalData) {
  const promotions = buildPromotionCardModels(data.promotions.data);
  if (!promotions.length) {
    return <ClientEmptyBlock title="No hay promociones activas" description="Cuando exista una campaña visible para cliente, la verás aquí con vigencia, CTA y mensaje en formato comercial." />;
  }
  return (
    <ClientSectionBlock title="Campañas y promociones" subtitle="Presentadas como piezas compartibles con CTA visible, vigencia y estado para dar más valor percibido.">
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {promotions.map((item) => (
          <ClientPromotionCard key={item.id} title={item.title} message={item.message} validity={item.validity} status={item.status} ctaLabel={item.ctaLabel} />
        ))}
      </div>
    </ClientSectionBlock>
  );
}

export function renderBot(data: ClientPortalData) {
  if (!data.context.botId) {
    return <ClientEmptyBlock title="Todavía no hay un bot seleccionado" description="El portal cliente respeta el contexto activo. Cuando exista un bot visible para esta organización, aquí mostraremos una lectura clara de su comportamiento." />;
  }
  return (
    <div className="space-y-6">
      <ClientSectionBlock title="Lectura resumida del bot" subtitle="Campos explicados en lenguaje claro para que el cliente entienda cómo está respondiendo el bot sin ver configuración interna.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {buildBotAttributeModels(data).map((item) => (
            <ClientBotAttribute key={item.label} label={item.label} value={item.value} description={item.description} />
          ))}
        </div>
      </ClientSectionBlock>
    </div>
  );
}
