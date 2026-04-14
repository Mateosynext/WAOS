import Link from "next/link";
import { ContextTip, EmptyActionState, ModuleCard, Section, Shell, SecondaryNav, StatCard, SuccessState, TimelineList } from "./components";
import { formatMoney, formatNumber } from "./lib/ui";
import { getSession } from "./lib/session";
import { getAgendaOverview, getBots, getBusinessHubOverview, getDashboard, getDirectorMode, getIntegrations, getQueue, getObservability } from "./lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }
function countConnectedIntegrations(integrations: Array<{ status?: string; credential_status?: string }>) {
  return integrations.filter((item) => {
    const status = String(item.status || "").toLowerCase();
    const credential = String(item.credential_status || "").toLowerCase();
    return ["active", "configured", "connected"].includes(status) || credential === "connected";
  }).length;
}

export default async function HomePage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const view = first(params.view) || "operativa";
  const session = await getSession();
  const [dashboard, hub, queue, integrations, bots, agenda, observability, director] = await Promise.all([
    getDashboard(),
    getBusinessHubOverview(),
    getQueue(),
    getIntegrations(),
    getBots(),
    getAgendaOverview(),
    getObservability(),
    getDirectorMode(),
  ]);

  const summary = dashboard.summary || {};
  const hubSummary = hub.summary || {};
  const directorSummary = director.summary || {};
  const connectedIntegrations = countConnectedIntegrations(integrations);
  const pendingJobs = (queue.automation_jobs || []).reduce((acc: number, item) => acc + Number(item.count || 0), 0);
  const upcoming = agenda.upcoming || [];
  const pausedBots = (dashboard.bots || []).filter((bot) => Number(bot.ai_paused) === 1 || String(bot.status).toLowerCase() === "paused").length;
  const integrationIssues = integrations.filter((item) => !["active", "configured", "connected"].includes(String(item.status || "").toLowerCase()));
  const hasBots = bots.length > 0;
  const hasChannels = connectedIntegrations > 0;
  const hasContent = Number(hubSummary.products || 0) + Number(hubSummary.services || 0) + Number(hubSummary.promotions || 0) > 0;
  const setupReady = hasBots && hasChannels && hasContent;

  const primaryHref = !hasBots ? "/bot-studio" : !hasChannels ? "/integrations" : !hasContent ? "/catalog" : "/inbox?filter=human";
  const primaryLabel = !hasBots ? "Crear" : !hasChannels ? "Conectar" : !hasContent ? "Crear" : "Operar";

  const opsTimeline = [
    pendingJobs ? { title: "Revisar tareas pendientes", detail: `${formatNumber(pendingJobs)} tareas siguen acumuladas y pueden frenar la operación.`, tone: "gold" as const } : null,
    pausedBots ? { title: "Reactivar bots pausados", detail: `${formatNumber(pausedBots)} bots siguen detenidos y pueden cortar conversaciones.`, tone: "red" as const } : null,
    integrationIssues.length ? { title: "Probar integraciones con riesgo", detail: `${formatNumber(integrationIssues.length)} conexiones requieren prueba o ajuste.`, tone: "gold" as const } : null,
  ].filter(Boolean) as Array<{ title: string; detail: string; tone?: "slate" | "green" | "gold" | "red" | "blue" }>;

  return (
    <Shell
      title={view === "operativa" ? "Home super admin" : "Vista ejecutiva"}
      subtitle={view === "operativa"
        ? "Una entrada pensada para decidir qué hacer hoy sin ruido: operar, resolver bloqueos o terminar de preparar la salida."
        : "Una lectura corta para explicar estado, resultados y riesgo sin entrar a mantenimiento técnico."}
      action={<Link href={primaryHref} className="primary-btn">{primaryLabel}</Link>}
    >
      {session?.user.organizations && session.user.organizations.length > 1 && !session.organizationId ? <EmptyActionState title="Selecciona una organización para cargar contexto correcto" description="Tu cuenta opera varias organizaciones. Antes de seguir, fija una organización para que bots, inbox, integraciones y releases no mezclen datos." primaryAction={<Link href="/organizations" className="primary-btn">Seleccionar organización</Link>} /> : null}
      <SecondaryNav items={[
        { href: "/?view=operativa", label: "Trabajo diario", active: view === "operativa" },
        { href: "/?view=ejecutiva", label: "Resumen ejecutivo", active: view === "ejecutiva" },
      ]} />

      {view === "operativa" ? (
        <>
          <ContextTip>Empieza por una sola pregunta: ¿hoy te toca crear, conectar, probar o publicar? El resto se consulta después.</ContextTip>
          {!setupReady ? (
            <EmptyActionState
              title="Todavía no está lista la operación base"
              description="Antes de abrir muchas pantallas, cierra lo esencial en este orden: crear bot, conectar canal, cargar contenido y probar. Así el sistema deja de sentirse disperso."
              primaryAction={<Link href="/onboarding" className="primary-btn">Continuar onboarding</Link>}
              secondaryAction={<Link href={primaryHref} className="secondary-btn">{primaryLabel} ahora</Link>}
            />
          ) : (
            <SuccessState
              title="La base operativa ya está lista"
              description="Ya tienes bot, canal y contenido suficiente. Lo siguiente es operar la bandeja, monitorear riesgo y publicar cambios con control."
              actions={<Link href="/inbox?filter=human" className="primary-btn">Ir a trabajo diario</Link>}
            />
          )}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Conversaciones activas" value={formatNumber(summary.active_conversations)} hint="Lo que puede necesitar atención ahora" icon="chat" tone="green" />
            <StatCard label="Bots pausados" value={formatNumber(pausedBots)} hint="Casos que frenan la operación" icon="alert" tone={pausedBots ? "red" : "green"} />
            <StatCard label="Integraciones listas" value={formatNumber(connectedIntegrations)} hint="Canales ya conectados" icon="plug" tone="blue" />
            <StatCard label="Tareas pendientes" value={formatNumber(pendingJobs)} hint="Cola visible de trabajo" icon="clock" tone="gold" />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <Section title="Trabajo diario" subtitle="Solo lo necesario para operar hoy sin mezclarlo con mantenimiento." icon="chat">
              {opsTimeline.length ? (
                <TimelineList items={opsTimeline} />
              ) : (
                <SuccessState title="No se ven bloqueos inmediatos" description="Puedes dedicar el tiempo a revisar conversaciones, probar mejoras o preparar el siguiente release." actions={<Link href="/inbox" className="primary-btn">Operar</Link>} />
              )}
            </Section>
            <Section title="Configuración y salida" subtitle="Cuando ya cerraste lo diario, usa este bloque para preparar cambios o completar la base." icon="route">
              <div className="grid gap-4 md:grid-cols-2">
                <ModuleCard title="Crear bot" description="Define objetivo, tono y comportamiento antes de tocar otras capas." icon="wand" tone="green" footer={<Link href="/bot-studio" className="secondary-btn">Crear</Link>} />
                <ModuleCard title="Conectar canal" description="Activa el canal principal y deja credenciales sanas antes de publicar." icon="plug" tone="blue" footer={<Link href="/integrations" className="secondary-btn">Conectar</Link>} />
                <ModuleCard title="Probar experiencia" description="Valida flujos, inbox y portal cliente antes de soltar tráfico." icon="play" tone="gold" footer={<Link href="/onboarding?step=probar" className="secondary-btn">Probar</Link>} />
                <ModuleCard title="Publicar con control" description="Pasa por releases y estado interno para salir sin saltos de fe." icon="rocket" tone="slate" footer={<Link href="/releases" className="secondary-btn">Publicar</Link>} />
              </div>
            </Section>
          </div>
        </>
      ) : (
        <>
          <ContextTip title="Lectura ejecutiva">Esta vista sirve para explicar el estado a alguien que no necesita abrir módulos técnicos ni navegar veinte pantallas.</ContextTip>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Clientes nuevos" value={formatNumber(summary.new_leads)} hint="Movimiento comercial visible" icon="target" tone="green" />
            <StatCard label="Clientes calientes" value={formatNumber(summary.hot_leads)} hint="Casos con mayor intención" icon="sales" tone="gold" />
            <StatCard label="Citas próximas" value={formatNumber(upcoming.length)} hint="Compromisos ya generados" icon="calendar" tone="blue" />
            <StatCard label="Ingresos visibles" value={formatMoney(Number(directorSummary.revenue || 0))} hint="Señal resumida de negocio" icon="money" tone="slate" />
          </div>
          <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <Section title="Resumen ejecutivo" subtitle="Lo esencial del negocio y la operación en una sola tabla." icon="briefcase">
              <TimelineList items={[
                { title: "Actividad comercial", detail: `${formatNumber(summary.new_leads)} clientes nuevos y ${formatNumber(summary.hot_leads)} casos calientes.`, tone: "green" },
                { title: "Riesgo operativo", detail: integrationIssues.length ? `${formatNumber(integrationIssues.length)} integraciones requieren revisión.` : "No se ven riesgos relevantes en integraciones.", tone: integrationIssues.length ? "gold" : "green" },
                { title: "Capacidad de entrega", detail: pendingJobs ? `${formatNumber(pendingJobs)} tareas pendientes todavía consumen capacidad.` : "La cola visible no muestra presión importante.", tone: pendingJobs ? "gold" : "green" },
              ]} />
            </Section>
            <Section title="Qué conviene decidir hoy" subtitle="Una lectura corta para decidir sin perderse en mantenimiento." icon="alert">
              <div className="grid gap-4">
                <ModuleCard title="Revisar integración" description={integrationIssues.length ? "Hay conexiones que pueden afectar resultados o atención." : "No hay alertas visibles en conexiones."} icon="plug" tone={integrationIssues.length ? "gold" : "green"} footer={<Link href="/integrations?section=riesgo" className="secondary-btn">Ver riesgo</Link>} />
                <ModuleCard title="Revisar publicación" description={pausedBots ? "Hay bots pausados o cambios que conviene revisar antes de publicar." : "La operación visible no muestra pausas críticas."} icon="layers" tone={pausedBots ? "red" : "blue"} footer={<Link href="/releases" className="secondary-btn">Publicar</Link>} />
              </div>
            </Section>
          </div>
        </>
      )}
    </Shell>
  );
}
