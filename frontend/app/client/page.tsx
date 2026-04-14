import Link from "next/link";
import { ContextTip, DataTable, EmptyActionState, ModuleCard, PortalTabs, Section, Shell, StatCard, StoryBeat, SuccessState, TimelineList } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getAppointments, getBotBehavior, getConversations, getFeedback, getPortalRequests, getPromotions, getVerticalProfile } from "../lib/waos";
import { getSession } from "../lib/session";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

export default async function ClientPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const section = first(params.section) || "resumen";
  const session = await getSession();
  const currentOrg = session?.user.organizations?.find((item) => item.id === session?.organizationId) || null;
  const [appointments, conversations, feedback, requests, promotions, behavior, verticalProfile] = await Promise.all([
    getAppointments(),
    getConversations(),
    getFeedback(),
    getPortalRequests(),
    getPromotions(),
    getBotBehavior(),
    getVerticalProfile(currentOrg?.vertical),
  ]);

  const totalRequests = requests.length + feedback.length;
  const primaryHref = section === "resumen" ? "/client?section=solicitudes" : section === "conversaciones" ? "/client?section=agenda" : "/client?section=resumen";
  const primaryLabel = section === "resumen" ? "Ver solicitudes" : section === "conversaciones" ? "Ver agenda" : "Volver al resumen";
  const weekStory = [
    { step: "Esta semana", title: "Conversaciones visibles", description: `Tienes ${formatNumber(conversations.length)} conversaciones abiertas para revisión y seguimiento.`, outcome: conversations.length ? "Puedes abrirlas y revisar contexto sin entrar a pantallas técnicas." : "Todavía no hay actividad visible esta semana.", tone: "blue" as const },
    { step: "Agenda", title: "Citas y seguimiento", description: `Hay ${formatNumber(appointments.length)} citas o espacios registrados.`, outcome: appointments.length ? "Puedes confirmar fechas y estado desde Agenda." : "Todavía no hay citas visibles esta semana.", tone: "green" as const },
    { step: "Solicitudes", title: "Cambios pedidos", description: `Tienes ${formatNumber(totalRequests)} solicitudes o comentarios acumulados.`, outcome: totalRequests ? "Puedes revisar qué está pendiente, qué fue aprobado y qué sigue." : "No hay solicitudes abiertas por ahora.", tone: "gold" as const },
  ];
  const requestTimeline = [...requests, ...feedback].slice(0, 6).map((item, index: number) => ({
    title: safeText(item.kind || (("comment" in item && item.comment) ? "feedback" : "solicitud"), `item-${index}`),
    detail: safeText(item.detail || (("comment" in item && item.comment) ? item.comment : null) || item.message, "Sin detalle"),
    tone: "slate" as const,
  }));

  return (
    <Shell
      mode="client"
      title={section === "resumen" ? "Qué pasó esta semana" : section === "solicitudes" ? "Solicitudes del cliente" : "Portal cliente"}
      subtitle={section === "resumen"
        ? "Una portada simple para entender avances, pendientes y lo que sigue sin pedir ayuda a alguien técnico."
        : "Todo lo que el cliente ve aquí está pensado para ser entendible, compartible y fácil de aprobar."}
      action={<Link href={primaryHref} className="primary-btn">{primaryLabel}</Link>}
    >
      <Section title="Navegación del portal" subtitle="Solo lo necesario: resumen, conversaciones, agenda, promociones y solicitudes." icon="client">
        <PortalTabs current={section} />
      </Section>

      {section === "resumen" ? (
        <>
          <ContextTip>Si el cliente puede usar esta portada sin capacitación, la experiencia va en la dirección correcta.</ContextTip>
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
              <StatCard label="KPI sugeridos" value={formatNumber(verticalProfile.kpis.length)} hint="Que vale la pena medir" icon="stats" tone="slate" />
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <ModuleCard title="Problema que resuelve" description={safeText(verticalProfile.problem, "Todavia no hay una vertical definida para esta organizacion.")} icon="target" tone="green" />
              <ModuleCard title="Flujos que deberia cubrir" description={safeText(verticalProfile.flows.join(" • "), "Aun no hay flujos visibles.")} icon="flow" tone="blue" />
              <ModuleCard title="Integraciones recomendadas" description={safeText(verticalProfile.recommended_integrations.join(" • "), "Base operativa pendiente.")} icon="plug" tone="gold" />
            </div>
          </Section>

          {totalRequests ? (
            <SuccessState title="Ya hay una historia clara para el cliente" description="Esta portada le permite entender qué pasó, qué se movió y qué decisiones siguen sin abrir módulos técnicos." actions={<Link href="/client?section=solicitudes" className="primary-btn">Ver solicitudes</Link>} />
          ) : (
            <EmptyActionState title="Todavía no hay cambios pendientes" description="Cuando existan solicitudes, aprobaciones o comentarios, esta portada lo mostrará de forma simple y compartible." primaryAction={<Link href="/client?section=promociones" className="primary-btn">Ver promociones</Link>} />
          )}

          <Section title="Qué pasó esta semana" subtitle="Una lectura simple para entender avances y pendientes." icon="stats">
            <div className="grid gap-4 xl:grid-cols-3">{weekStory.map((item) => <StoryBeat key={item.title} {...item} />)}</div>
          </Section>

          <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <Section title="Solicitudes recientes" subtitle="Todo lo pedido o comentado en una sola vista." icon="folder">
              <TimelineList items={requestTimeline.length ? requestTimeline : [{ title: "Sin solicitudes abiertas", detail: "Cuando pidas cambios, aprobaciones o seguimiento, aparecerán aquí.", tone: "slate" }]} />
            </Section>
            <Section title="Qué puedes hacer hoy" subtitle="Accesos directos pensados para alguien no técnico." icon="play">
              <div className="grid gap-4 md:grid-cols-2">
                <ModuleCard title="Ver conversaciones" description="Revisar hilos y contexto sin entrar a pantallas de operación." icon="chat" tone="blue" footer={<Link href="/client?section=conversaciones" className="secondary-btn">Abrir</Link>} />
                <ModuleCard title="Revisar agenda" description="Confirmar citas, horarios y seguimiento próximo." icon="calendar" tone="green" footer={<Link href="/client?section=agenda" className="secondary-btn">Abrir</Link>} />
                <ModuleCard title="Ver promociones" description="Consultar ofertas y mensajes activos en lenguaje simple." icon="promo" tone="gold" footer={<Link href="/client?section=promociones" className="secondary-btn">Abrir</Link>} />
                <ModuleCard title="Entender el bot" description="Ver su comportamiento actual sin lenguaje técnico." icon="bot" tone="slate" footer={<Link href="/client?section=bot" className="secondary-btn">Abrir</Link>} />
              </div>
            </Section>
          </div>
        </>
      ) : null}

      {section === "conversaciones" ? (
        <Section title="Conversaciones del cliente" subtitle="Hilos visibles para seguimiento y contexto, sin vista operativa pesada." icon="chat">
          {conversations.length ? <DataTable columns={["Contacto", "Estado", "Resumen"]} rows={conversations.map((item) => [safeText(item.contact_name), safeText(item.status), safeText(item.summary)])} /> : <EmptyActionState title="Todavía no hay conversaciones visibles" description="Cuando entren nuevos hilos o seguimientos, aparecerán aquí con contexto simple." primaryAction={<Link href="/client?section=resumen" className="primary-btn">Volver al resumen</Link>} />}
        </Section>
      ) : null}

      {section === "agenda" ? (
        <Section title="Agenda del cliente" subtitle="Próximas citas o espacios registrados en el sistema." icon="calendar">
          {appointments.length ? <DataTable columns={["Servicio", "Fecha", "Estado"]} rows={appointments.map((item) => [safeText(item.service_name), safeText(item.starts_at || item.start_at), safeText(item.status)])} /> : <EmptyActionState title="Todavía no hay agenda visible" description="Cuando existan citas o espacios agendados, aparecerán aquí para confirmación simple." primaryAction={<Link href="/client?section=resumen" className="primary-btn">Volver al resumen</Link>} />}
        </Section>
      ) : null}

      {section === "promociones" ? (
        <Section title="Promociones disponibles" subtitle="Ofertas visibles para el cliente en lenguaje simple." icon="promo">
          {promotions.length ? <DataTable columns={["Promoción", "Mensaje", "Vigencia"]} rows={promotions.map((item) => [safeText(item.name), safeText(item.message_short), `${safeText(item.starts_at)} → ${safeText(item.ends_at)}`])} /> : <EmptyActionState title="Todavía no hay promociones visibles" description="Cuando una promoción esté lista para revisar o aprobar, aparecerá aquí con su mensaje y vigencia." primaryAction={<Link href="/client?section=resumen" className="primary-btn">Volver al resumen</Link>} />}
        </Section>
      ) : null}

      {section === "solicitudes" ? (
        <Section title="Solicitudes y feedback" subtitle="Todo lo que el cliente ya pidió, aprobó o comentó." icon="folder">
          {totalRequests ? <DataTable columns={["Tipo", "Detalle"]} rows={[
            ...requests.map((item) => [safeText(item.kind || "solicitud"), safeText(item.detail || item.message)]),
            ...feedback.map((item) => [safeText(item.kind || "feedback"), safeText(item.comment || item.message)]),
          ]} /> : <EmptyActionState title="No hay solicitudes abiertas" description="Cuando el cliente pida cambios o deje comentarios, esta pantalla mostrará el historial compartible." primaryAction={<Link href="/client?section=resumen" className="primary-btn">Volver al resumen</Link>} />}
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
