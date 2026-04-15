import Link from "next/link";
import { ContextTip, DataTable, EmptyActionState, ModuleCard, PortalTabs, Section, Shell, StatCard, StoryBeat, SuccessState, TimelineList } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getAppointments, getBotBehavior, getConversations, getFeedback, getPortalRequests, getPromotions, getVerticalProfile } from "../lib/waos";
import { getSession } from "../lib/session";

export type ClientSection = "resumen" | "conversaciones" | "agenda" | "promociones" | "solicitudes" | "bot";

export async function ClientPortalContent({ section }: { section: ClientSection }) {
  const session = await getSession();
  const currentOrg = session?.user.organizations?.find((item) => item.id === session?.organizationId) || null;

  const wantsSummary = section === "resumen";
  const wantsConversations = wantsSummary || section === "conversaciones";
  const wantsAppointments = wantsSummary || section === "agenda";
  const wantsRequests = wantsSummary || section === "solicitudes";
  const wantsPromotions = wantsSummary || section === "promociones";
  const wantsBot = wantsSummary || section === "bot";

  const [appointments, conversations, feedback, requests, promotions, behavior, verticalProfile] = await Promise.all([
    wantsAppointments ? getAppointments() : Promise.resolve([]),
    wantsConversations ? getConversations() : Promise.resolve([]),
    wantsRequests ? getFeedback() : Promise.resolve([]),
    wantsRequests ? getPortalRequests() : Promise.resolve([]),
    wantsPromotions ? getPromotions() : Promise.resolve([]),
    wantsBot ? getBotBehavior() : Promise.resolve<Record<string, unknown>>({}),
    wantsBot || wantsSummary ? getVerticalProfile(currentOrg?.vertical) : Promise.resolve({ id: "", name: "", short_name: "", description: "", problem: "", portfolio_tier: "", master_thesis: "", subverticals: [], objects: [], flows: [], kpis: [], recommended_integrations: [], buyer: {}, one_pager: {}, demo_flow: [], native_objects: {}, pipeline: {}, bot_playbook: {}, automation_sequences: [] }),
  ]);

  const totalRequests = requests.length + feedback.length;
  const primaryHref = section === "resumen" ? "/client/solicitudes" : section === "conversaciones" ? "/client/agenda" : "/client/resumen";
  const primaryLabel = section === "resumen" ? "Ver solicitudes" : section === "conversaciones" ? "Ver agenda" : "Volver al resumen";

  const weekStory = [
    { step: "Esta semana", title: "Conversaciones visibles", description: `Tienes ${formatNumber(conversations.length)} conversaciones abiertas para revisión y seguimiento.`, outcome: conversations.length ? "Puedes abrirlas y revisar contexto sin entrar a pantallas técnicas." : "Todavía no hay actividad visible esta semana.", tone: "blue" as const },
    { step: "Agenda", title: "Citas y seguimiento", description: `Hay ${formatNumber(appointments.length)} citas o espacios registrados.`, outcome: appointments.length ? "Puedes confirmar fechas y estado desde Agenda." : "Todavía no hay citas visibles esta semana.", tone: "green" as const },
    { step: "Solicitudes", title: "Cambios pedidos", description: `Tienes ${formatNumber(totalRequests)} solicitudes o comentarios acumulados.`, outcome: totalRequests ? "Puedes revisar qué está pendiente, qué fue aprobado y qué sigue." : "No hay solicitudes abiertas por ahora.", tone: "gold" as const },
  ];
  const requestTimeline = [...requests, ...feedback].slice(0, 6).map((item, index: number) => ({
    title: safeText(item.kind || ("comment" in item && item.comment ? "feedback" : "solicitud"), `item-${index}`),
    detail: safeText(item.detail || ("comment" in item && item.comment ? item.comment : null) || item.message, "Sin detalle"),
    tone: "slate" as const,
  }));

  return (
    <Shell
      mode="client"
      title={section === "resumen" ? "Portal cliente" : section === "solicitudes" ? "Solicitudes del cliente" : section === "conversaciones" ? "Conversaciones visibles" : section === "agenda" ? "Agenda del cliente" : section === "promociones" ? "Promociones activas" : "Estado del bot"}
      subtitle={section === "resumen"
        ? "Una portada simple para entender avances, pendientes y lo que sigue sin pedir ayuda técnica."
        : "Cada vista del portal cliente está separada por tarea para no mezclar conversaciones, agenda, solicitudes y estado del bot."}
      action={<Link href={primaryHref} className="primary-btn">{primaryLabel}</Link>}
    >
      <Section title="Moverse dentro del portal" subtitle="Solo lo necesario: resumen, conversaciones, agenda, promociones, solicitudes y estado del bot." icon="client">
        <PortalTabs />
      </Section>

      {section === "resumen" ? (
        <>
          <ContextTip title="Regla de oro del portal">Si el cliente puede usar esta portada sin capacitación, la experiencia va en la dirección correcta.</ContextTip>
          <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-3">
            <StatCard label="Conversaciones" value={formatNumber(conversations.length)} hint="Actividad visible" icon="chat" tone="blue" />
            <StatCard label="Citas" value={formatNumber(appointments.length)} hint="Seguimiento programado" icon="calendar" tone="green" />
            <StatCard label="Solicitudes" value={formatNumber(totalRequests)} hint="Lo que sigue o espera aprobación" icon="folder" tone="gold" />
          </div>

          <Section title="Vertical activa" subtitle="Lo que WAOS ya entiende de tu negocio y del tipo de bot que debe operar para ti." icon="layers">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <StatCard label="Vertical" value={safeText(verticalProfile.short_name || verticalProfile.name, "sin definir")} hint="Lenguaje operativo del negocio" icon="stack" tone="green" />
              <StatCard label="Subverticales" value={formatNumber(verticalProfile.subverticals.length)} hint="Casos cubiertos en la familia" icon="layers" tone="blue" />
              <StatCard label="Objetos operativos" value={formatNumber(verticalProfile.objects.length)} hint="Lo que el bot ya sabe seguir" icon="folder" tone="gold" />
              <StatCard label="KPI sugeridos" value={formatNumber(verticalProfile.kpis.length)} hint="Qué vale la pena medir" icon="stats" tone="slate" />
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <ModuleCard title="Problema que resuelve" description={safeText(verticalProfile.problem, "Todavía no hay una vertical definida para esta organización.")} icon="target" tone="green" />
              <ModuleCard title="Flujos que debería cubrir" description={safeText(verticalProfile.flows.join(" • "), "Aún no hay flujos visibles.")} icon="flow" tone="blue" />
              <ModuleCard title="Integraciones recomendadas" description={safeText(verticalProfile.recommended_integrations.join(" • "), "Base operativa pendiente.")} icon="plug" tone="gold" />
            </div>
          </Section>

          {totalRequests ? (
            <SuccessState title="Ya hay una historia clara para el cliente" description="Esta portada permite entender qué pasó, qué se movió y qué decisiones siguen sin abrir módulos técnicos." actions={<Link href="/client/solicitudes" className="primary-btn">Ver solicitudes</Link>} />
          ) : (
            <EmptyActionState title="Todavía no hay cambios pendientes" description="Cuando existan solicitudes, aprobaciones o comentarios, esta portada lo mostrará de forma simple y compartible." primaryAction={<Link href="/client/promociones" className="primary-btn">Ver promociones</Link>} />
          )}

          <Section title="Historia de la semana" subtitle="Una secuencia corta para contar qué se movió sin abrir más módulos." icon="route">
            <div className="grid gap-4 xl:grid-cols-3">
              {weekStory.map((item) => <StoryBeat key={item.title} {...item} />)}
            </div>
          </Section>
        </>
      ) : null}

      {section === "conversaciones" ? (
        <Section title="Conversaciones visibles" subtitle="Una vista compartible para revisar actividad sin entrar a la bandeja operativa." icon="chat">
          {conversations.length ? (
            <DataTable columns={["Contacto", "Estado", "Bot", "Resumen"]} rows={conversations.slice(0, 12).map((item) => [
              safeText(item.contact_name),
              safeText(item.status),
              safeText(item.bot_name),
              safeText(item.summary),
            ])} />
          ) : (
            <EmptyActionState title="Todavía no hay conversaciones visibles" description="Cuando exista actividad real, esta vista mostrará el resumen sin exponer configuración interna." primaryAction={<Link href="/client/resumen" className="primary-btn">Volver al resumen</Link>} />
          )}
        </Section>
      ) : null}

      {section === "agenda" ? (
        <Section title="Agenda del cliente" subtitle="Fechas y estado en una sola tabla legible." icon="calendar">
          {appointments.length ? (
            <DataTable columns={["Contacto", "Servicio", "Fecha", "Estado"]} rows={appointments.slice(0, 12).map((item) => [
              safeText(item.contact_name),
              safeText(item.service_name),
              safeText(item.starts_at || item.start_at || item.scheduled_for),
              safeText(item.status),
            ])} />
          ) : (
            <EmptyActionState title="No hay citas visibles" description="Cuando exista seguimiento programado, esta vista lo resumirá sin exigir navegación técnica." primaryAction={<Link href="/client/resumen" className="primary-btn">Volver al resumen</Link>} />
          )}
        </Section>
      ) : null}

      {section === "promociones" ? (
        <Section title="Promociones activas" subtitle="Ofertas y mensajes listos para compartir con el cliente." icon="promo">
          {promotions.length ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {promotions.map((item) => (
                <ModuleCard
                  key={item.id}
                  title={safeText(item.name)}
                  description={safeText(item.message_short || item.message_long, "Promoción sin copy visible.")}
                  tone="gold"
                  icon="promo"
                  footer={<><span className="mono-pill">{safeText(item.status || "activa")}</span><span className="mono-pill">{safeText(item.cta_label || "sin CTA")}</span></>}
                />
              ))}
            </div>
          ) : (
            <EmptyActionState title="No hay promociones activas" description="Cuando se publique una promoción visible para el cliente, aparecerá aquí." primaryAction={<Link href="/client/resumen" className="primary-btn">Volver al resumen</Link>} />
          )}
        </Section>
      ) : null}

      {section === "solicitudes" ? (
        <Section title="Solicitudes y feedback" subtitle="Todo lo que el cliente pidió o comentó, sin mezclarlo con la operación interna." icon="folder">
          {totalRequests ? <TimelineList items={requestTimeline} /> : null}
          {totalRequests ? <DataTable columns={["Tipo", "Detalle"]} rows={[
            ...requests.map((item) => [safeText(item.kind || "solicitud"), safeText(item.detail || item.message)]),
            ...feedback.map((item) => [safeText(item.kind || "feedback"), safeText(item.comment || item.message)]),
          ]} /> : <EmptyActionState title="No hay solicitudes abiertas" description="Cuando el cliente pida cambios o deje comentarios, esta pantalla mostrará el historial compartible." primaryAction={<Link href="/client/resumen" className="primary-btn">Volver al resumen</Link>} />}
        </Section>
      ) : null}

      {section === "bot" ? (
        <Section title="Estado del bot" subtitle="Una lectura simple del bot sin exponer pantallas técnicas." icon="bot">
          <DataTable columns={["Tema", "Valor"]} rows={[["Modo", safeText(behavior.bot_mode)], ["Tono", safeText(behavior.tone)], ["Longitud de respuesta", safeText(behavior.response_length)], ["Intensidad comercial", safeText(behavior.sales_intensity)], ["Puede mencionar stock", safeText(behavior.can_mention_stock ? "Sí" : "No")]]} />
        </Section>
      ) : null}
    </Shell>
  );
}
