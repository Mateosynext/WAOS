import Link from "next/link";
import { ContextTip, EmptyActionState, ModuleCard, Section, Shell, StatCard, SuccessState, TimelineList } from "./components";
import { formatMoney, formatNumber } from "./lib/ui";
import { getSession } from "./lib/session";
import { getAgendaOverview, getBots, getBusinessHubOverview, getDashboard, getIntegrations, getQueue } from "./lib/waos";

function countConnectedIntegrations(integrations: Array<{ status?: string; credential_status?: string }>) {
  return integrations.filter((item) => {
    const status = String(item.status || "").toLowerCase();
    const credential = String(item.credential_status || "").toLowerCase();
    return ["active", "configured", "connected"].includes(status) || credential === "connected";
  }).length;
}

export default async function HomePage() {
  const session = await getSession();
  const [dashboard, hub, queue, integrations, bots, agenda] = await Promise.all([
    getDashboard(),
    getBusinessHubOverview(),
    getQueue(),
    getIntegrations(),
    getBots(),
    getAgendaOverview(),
  ]);

  const summary = dashboard.summary || {};
  const hubSummary = hub.summary || {};
  const connectedIntegrations = countConnectedIntegrations(integrations);
  const pendingJobs = (queue.automation_jobs || []).reduce((acc: number, item) => acc + Number(item.count || 0), 0);
  const pausedBots = (dashboard.bots || []).filter((bot) => Number(bot.ai_paused) === 1 || String(bot.status).toLowerCase() === "paused").length;
  const hotLeads = Number(summary.hot_leads || 0);
  const totalCatalog = Number(hubSummary.products || 0) + Number(hubSummary.services || 0) + Number(hubSummary.promotions || 0);
  const setupReady = bots.length > 0 && connectedIntegrations > 0 && totalCatalog > 0;
  const primaryHref = !bots.length ? "/bot-studio" : !connectedIntegrations ? "/integrations" : !totalCatalog ? "/business-hub?tab=catalogo" : "/inbox";
  const upcoming = agenda.upcoming || [];

  const launchChecklist = [
    { title: bots.length ? "Bot listo" : "Crear bot", detail: bots.length ? `${formatNumber(bots.length)} bot(s) visibles en este tenant.` : "Primero crea un bot con una vertical clara.", tone: bots.length ? "green" as const : "red" as const },
    { title: connectedIntegrations ? "Canales conectados" : "Conectar canal", detail: connectedIntegrations ? `${formatNumber(connectedIntegrations)} canales listos para operar.` : "Sin canal conectado, el sistema sigue en simulación.", tone: connectedIntegrations ? "green" as const : "gold" as const },
    { title: totalCatalog ? "Oferta visible" : "Cargar catálogo", detail: totalCatalog ? `${formatNumber(totalCatalog)} items visibles entre productos, servicios y promociones.` : "Sin contenido comercial el bot no puede vender ni orientar bien.", tone: totalCatalog ? "green" as const : "gold" as const },
  ];

  const attentionNow = [
    pendingJobs ? { title: "Tareas pendientes", detail: `${formatNumber(pendingJobs)} jobs aún consumen capacidad y conviene revisarlos hoy.`, tone: "gold" as const } : null,
    pausedBots ? { title: "Bots pausados", detail: `${formatNumber(pausedBots)} bots detenidos pueden congelar conversaciones.`, tone: "red" as const } : null,
    hotLeads ? { title: "Leads calientes", detail: `${formatNumber(hotLeads)} conversaciones comerciales requieren seguimiento oportuno.`, tone: "green" as const } : null,
    upcoming.length ? { title: "Citas próximas", detail: `${formatNumber(upcoming.length)} compromisos ya están en agenda.`, tone: "blue" as const } : null,
  ].filter(Boolean) as Array<{ title: string; detail: string; tone?: "slate" | "green" | "gold" | "red" | "blue" }>;

  return (
    <Shell
      title="Tu día en WAOS"
      subtitle="La portada ahora funciona como launcher de trabajo: qué falta para salir, qué requiere atención hoy y a qué módulo conviene entrar después."
      action={<Link href={primaryHref} className="primary-btn">Abrir siguiente módulo</Link>}
    >
      {session?.user.organizations && session.user.organizations.length > 1 && !session.organizationId ? (
        <EmptyActionState
          title="Antes de seguir, confirma una organización"
          description="Tu cuenta ve más de un tenant. La app ya bloquea pantallas críticas hasta fijar el contexto correcto para que no mezcles inbox, bots ni releases."
          primaryAction={<Link href="/organizations" className="primary-btn">Elegir organización</Link>}
        />
      ) : null}

      <ContextTip title="Cómo leer esta portada">Primero cierra la base operativa. Después atiende lo urgente. Al final abre el módulo exacto que necesitas. Ese orden reduce la sensación de caos y evita brincar entre pantallas.</ContextTip>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Conversaciones activas" value={formatNumber(summary.active_conversations)} hint="Trabajo vivo hoy" icon="chat" tone="blue" />
        <StatCard label="Canales conectados" value={formatNumber(connectedIntegrations)} hint="Capacidad real para operar" icon="plug" tone="green" />
        <StatCard label="Leads calientes" value={formatNumber(hotLeads)} hint="Seguimiento comercial" icon="target" tone="gold" />
        <StatCard label="Ingreso visible" value={formatMoney(Number(summary.revenue || 0), "MXN")} hint="Señal resumida del negocio" icon="money" tone="slate" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Section title="1. Lo mínimo para salir bien" subtitle="Una lectura corta del setup mínimo para que el producto deje de sentirse incompleto." icon="route">
          {!setupReady ? (
            <>
              <TimelineList items={launchChecklist} />
              <div className="mt-4 flex flex-wrap gap-2">
                <Link href="/onboarding" className="primary-btn">Continuar onboarding</Link>
                <Link href={primaryHref} className="secondary-btn">Ir al bloqueo principal</Link>
              </div>
            </>
          ) : (
            <SuccessState title="La base operativa ya está lista" description="Ya tienes bot, canal y contenido suficiente para trabajar conversaciones reales sin brincar entre pantallas de setup." actions={<Link href="/inbox" className="primary-btn">Ir al inbox</Link>} />
          )}
        </Section>

        <Section title="2. Lo que requiere atención hoy" subtitle="Solo lo que merece tiempo ahora mismo." icon="alert">
          {attentionNow.length ? <TimelineList items={attentionNow} /> : <SuccessState title="No se ven bloqueos inmediatos" description="Puedes dedicar el tiempo a operar el inbox, mejorar mensajes o preparar el siguiente release." actions={<Link href="/operations" className="primary-btn">Abrir operaciones</Link>} />}
        </Section>
      </div>

      <Section title="Elegir modo" subtitle="Super admin y portal cliente ya se sienten como experiencias distintas." icon="client">
        <div className="grid gap-4 md:grid-cols-2">
          <ModuleCard title="Modo interno" description="Entrar a inbox, operaciones, publicaciones y comercial para mover el negocio sin ruido técnico innecesario." icon="dashboard" tone="blue" footer={<Link href="/inbox" className="secondary-btn">Ir al modo interno</Link>} />
          <ModuleCard title="Portal cliente" description="Abrir una vista compartible con resumen, conversaciones, agenda, promociones y solicitudes sin exponer configuración interna." icon="client" tone="green" footer={<Link href="/client/resumen" className="secondary-btn">Abrir portal cliente</Link>} />
        </div>
      </Section>

      <Section title="3. A dónde entrar ahora" subtitle="Accesos por intención, no por jerga interna del sistema." icon="spark">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ModuleCard title="Crear o alinear bot" description="Abre un solo studio para crear bot, aplicar vertical y sembrar comportamiento base." icon="bot" tone="green" footer={<Link href="/bot-studio" className="secondary-btn">Abrir studio</Link>} />
          <ModuleCard title="Operar conversaciones" description="Lista, preview y acciones rápidas para decidir antes de entrar al hilo completo." icon="chat" tone="blue" footer={<Link href="/inbox" className="secondary-btn">Abrir inbox</Link>} />
          <ModuleCard title="Mover comercial" description="Catálogo, promociones, insights e ingresos ya viven bajo un mismo dominio comercial." icon="briefcase" tone="gold" footer={<Link href="/business-hub" className="secondary-btn">Abrir comercial</Link>} />
          <ModuleCard title="Publicar con control" description="Revisa readiness, riesgos y salida a producción en una sola capa de releases." icon="rocket" tone="slate" footer={<Link href="/releases" className="secondary-btn">Abrir releases</Link>} />
        </div>
      </Section>
    </Shell>
  );
}
