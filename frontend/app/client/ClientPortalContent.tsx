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
import { formatDate, formatDateTime, formatNumber, humanizeToken, safeText } from "../lib/ui";
import { getSession } from "../lib/session";
import { approveOperationalCommandAction, cancelOperationalCommandAction, confirmOperationalCommandAction, createAuthorizedOperationalNumberAction, executeRescheduleBatchAction, previewRescheduleBatchAction, submitOperationalCommandAction, undoOperationalCommandAction } from "../actions/operational_control";
import { type ClientPortalData, type PortalModuleState } from "../lib/waos";
import { getClientPortalData } from "../lib/data/client-portal";
import { getClientOperationsData } from "../lib/data/client-operations";
import { buildAgendaViewModel, buildBotAttributeModels, buildClientPortalSummaryViewModel, buildClientPortalTimeline, buildConversationCardModels, buildPromotionCardModels, buildRequestCardModels, clientSectionMeta, hasPendingTimelineEntries, loadedModuleNotices, type ClientSection, type ClientTimelineEntry } from "./clientPortalViewModel";

export type { ClientSection } from "./clientPortalViewModel";

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

function renderSummary(data: ClientPortalData, timeline: ClientTimelineEntry[]) {
  const summary = buildClientPortalSummaryViewModel(data, timeline);

  return (
    <div className="space-y-6">
      <ClientExecutiveSummary
        title="Una portada pensada para entender qué pasó, qué sigue y qué puedes decidir en menos de un minuto"
        description="El portal cliente ya no depende de tablas frías ni de componentes genéricos. Esta vista prioriza progreso visible, actividad reciente, próximos pasos y señales del negocio para que cualquier persona no técnica pueda orientarse rápido."
        insights={summary.executiveHighlights}
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
          value={summary.metrics.conversations.value}
          description={summary.metrics.conversations.description}
          icon="chat"
          tone="blue"
        />
        <ClientMetricCard
          label="Agenda"
          value={summary.metrics.agenda.value}
          description={summary.metrics.agenda.description}
          icon="calendar"
          tone="green"
        />
        <ClientMetricCard
          label="Pendientes"
          value={summary.metrics.pending.value}
          description={summary.metrics.pending.description}
          icon="folder"
          tone="gold"
        />
        <ClientMetricCard
          label="Promociones"
          value={summary.metrics.promotions.value}
          description={summary.metrics.promotions.description}
          icon="promo"
          tone="slate"
        />
      </div>

      <ClientSectionBlock title="Panorama actual" subtitle="Tres bloques para leer el estado del portal sin ruido técnico.">
        <div className="grid gap-4 xl:grid-cols-3">
          <StoryBeat
            step="Qué pasó"
            title="Actividad reciente"
            description={summary.storyBeats.activity.description}
            outcome={summary.storyBeats.activity.outcome}
            tone="blue"
          />
          <StoryBeat
            step="Qué sigue"
            title="Agenda y seguimiento"
            description={summary.storyBeats.agenda.description}
            outcome={summary.storyBeats.agenda.outcome}
            tone="green"
          />
          <StoryBeat
            step="Qué decidir"
            title="Solicitudes y feedback"
            description={summary.storyBeats.decisions.description}
            outcome={summary.storyBeats.decisions.outcome}
            tone="gold"
          />
        </div>
      </ClientSectionBlock>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <ClientSectionBlock title="Actividad reciente" subtitle="La mezcla justa entre conversaciones y seguimiento, presentada de forma humana.">
          <div className="grid gap-4 lg:grid-cols-2">
            {summary.topConversations.map((item) => (
              <ClientConversationCard key={item.id} title={item.title} summary={item.summary} status={item.status} meta={item.meta} preview={item.preview} />
            ))}
            {!summary.topConversations.length ? <ClientEmptyBlock title="Aún no hay conversaciones visibles" description="Cuando exista actividad real, este bloque mostrará el resumen y el estado sin exponer bandejas internas." /> : null}
          </div>
        </ClientSectionBlock>

        <ClientSectionBlock title="Contexto del negocio" subtitle="Lo que WAOS ya entendió de la operación activa para darle sentido al portal.">
          <div className="grid gap-4">
            <ModuleCard
              title={summary.businessContext.verticalTitle}
              description={summary.businessContext.verticalProblem}
              tone="green"
              icon="layers"
            />
            <KeyValueList
              items={[
                { label: "Subvertical activa", value: summary.businessContext.selectedSubvertical },
                { label: "Pack aplicado", value: summary.businessContext.packCoverage },
                { label: "Objetos operativos", value: summary.businessContext.objectsCount },
                { label: "Flujos esperados", value: summary.businessContext.flowsCount },
                { label: "KPI sugeridos", value: summary.businessContext.kpiCount },
              ]}
            />
            <ModuleCard
              title="Promesa activa"
              description={summary.businessContext.promise}
              tone="blue"
              icon="spark"
              footer={<div className="text-xs text-slate-400">Foco portal: {summary.businessContext.focus}</div>}
            />
          </div>
        </ClientSectionBlock>
      </div>
    </div>
  );
}

function renderConversations(data: ClientPortalData) {
  const conversations = buildConversationCardModels(data.conversations.data);
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
          <ClientConversationCard key={item.id} title={item.title} summary={item.summary} status={item.status} meta={item.meta} preview={item.preview} />
        ))}
      </div>
    </ClientSectionBlock>
  );
}

function renderAgenda(data: ClientPortalData) {
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

function renderRequests(data: ClientPortalData, timeline: ClientTimelineEntry[]) {
  if (!timeline.length) {
    return <ClientEmptyBlock title="No hay solicitudes abiertas" description="Cuando el cliente pida cambios o deje comentarios, esta sección mostrará el historial con mejor contexto y jerarquía visual." />;
  }
  return (
    <ClientSectionBlock
      title="Seguimiento de solicitudes y feedback"
      subtitle="Cada elemento diferencia tipo, estado y detalle para que se entienda el avance sin tener que interpretar una tabla técnica."
      aside={<Badge tone={hasPendingTimelineEntries(timeline) ? "gold" : "green"}>{hasPendingTimelineEntries(timeline) ? "Hay pendientes" : "Todo al día"}</Badge>}
    >
      <div className="grid gap-4 lg:grid-cols-2">
        {buildRequestCardModels(timeline).map((item) => (
          <ClientRequestCard key={item.id} title={item.title} detail={item.detail} kind={item.kind} status={item.status} createdAt={item.createdAt} />
        ))}
      </div>
    </ClientSectionBlock>
  );
}

function renderPromotions(data: ClientPortalData) {
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

function renderBot(data: ClientPortalData) {
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



async function renderOperations(data: ClientPortalData) {
  if (!data.context.organizationId || !data.context.botId) {
    return <ClientEmptyBlock title="No hay contexto operativo activo" description="Selecciona una organización y un bot para habilitar el control operativo por portal o WhatsApp." />;
  }
  const organizationId = data.context.organizationId;
  const botId = data.context.botId;
  const { summary, availability, metrics, alerts } = await getClientOperationsData(organizationId, botId);
  const recentCommands = summary.recent_commands;
  const authorizedNumbers = summary.authorized_numbers;
  const bot = summary.bot;
  const counts = summary.counts;

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
        <ClientMetricCard label="Estado bot" value={safeText(bot.operational_state || bot.current_state || "active", "active")} description={safeText(bot.temp_unavailability_message || "Sin mensaje temporal", "Sin mensaje temporal")} icon="bot" tone="blue" />
        <ClientMetricCard label="Comandos 7d" value={formatNumber(metrics.summary.total || counts.recent_commands || 0)} description="Actividad operativa reciente registrada para este bot." icon="tool" tone="gold" />
        <ClientMetricCard label="Autorizados" value={formatNumber(Number(counts.authorized_numbers || 0))} description="Números que sí pueden operar por WhatsApp." icon="shield" tone="green" />
        <ClientMetricCard label="Alto impacto" value={formatNumber(metrics.summary.high_risk || 0)} description="Comandos de alto impacto creados en la última semana." icon="alert" tone="slate" />
        <ClientMetricCard label="Alertas abiertas" value={formatNumber(metrics.summary.alerts_open || counts.alerts_open || 0)} description="Eventos operativos que requieren seguimiento." icon="alert" tone="gold" />
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
            {authorizedNumbers.length ? authorizedNumbers.slice(0, 4).map((item) => (
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
            {alerts.length ? alerts.slice(0, 6).map((item) => (
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
            {recentCommands.length ? recentCommands.map((item) => (
              <div key={String(item.id)} className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={String(item.risk_level || 'low') === 'high' ? 'gold' : 'sky'}>{safeText(String(item.detected_intent || 'sin intención'), 'sin intención')}</Badge>
                  <Badge tone="slate">{safeText(String(item.status || 'queued'), 'queued')}</Badge>
                  {item.requires_confirmation ? <Badge tone="gold">Requiere confirmación</Badge> : null}
                </div>
                <div className="mt-3 text-sm text-[color:var(--text-secondary)]">{safeText(item.result_summary || item.created_at || '', 'Sin detalle')}</div>
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
              { label: 'Citas hoy', value: formatNumber(availability.summary.appointments || 0) },
              { label: 'Bloqueos', value: formatNumber(availability.summary.blocked_ranges || 0) },
              { label: 'Excepciones abiertas', value: formatNumber(availability.summary.open_exceptions || 0) },
            ]} />
            <TimelineList items={availability.appointments.slice(0, 6).map((item) => ({ title: `Cita ${safeText(item.id, '')}`, detail: `${safeText(item.status || 'scheduled', 'scheduled')} · ${formatDateTime(item.scheduled_for || '')}`, tone: 'slate' as const }))} />
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
  const timeline = buildClientPortalTimeline(data);
  const meta = clientSectionMeta[section];

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
