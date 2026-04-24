import Link from "next/link";
import { setTenantModeAction } from "@/app/actions/onboarding";
import { ContextTip } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import { TimelineList } from "@/app/components/primitives/data-display";
import { getSession } from "../lib/session";
import { formatNumber, safeText } from "../lib/ui";
import { getBusinessHubOverview } from "@/app/lib/data/analytics";
import { getBots } from "@/app/lib/data/bots";
import { getIntegrations } from "@/app/lib/data/integrations";
import { getActivationSummary } from "@/app/lib/data/onboarding";
import { getVerticalProfile } from "@/app/lib/data/verticals";

export default async function OnboardingPage() {
  const session = await getSession();
  const currentOrg = session?.user.organizations.find((item) => item.id === session?.organizationId) || null;
  const [bots, integrations, hub, activation] = await Promise.all([
    getBots(),
    getIntegrations(),
    getBusinessHubOverview(),
    getActivationSummary(),
  ]);

  const activationBot = activation.bot_id ? bots.find((item) => item.id === activation.bot_id) || null : null;
  const verticalProfile = await getVerticalProfile(
    activationBot?.vertical || currentOrg?.vertical || activation.vertical || undefined,
    activationBot?.id || undefined,
    currentOrg?.subvertical || undefined,
    currentOrg?.id || undefined,
  );

  const connectedIntegrations = integrations.filter((item) => ["active", "configured", "connected"].includes(String(item.status || "").toLowerCase()));
  const summary = hub.summary || {};
  const totalOffer = Number(summary.products || 0) + Number(summary.services || 0) + Number(summary.promotions || 0);
  const readiness = Number(activation.readiness_score || 0);
  const guidedWizard = activation.guided_wizard || null;

  const executionLinks = [
    {
      title: "Definir industria de la organización",
      description: currentOrg?.vertical ? `Hoy la organización está en ${currentOrg.vertical}. Si quieres cambiar la industria y el tipo de operación, hazlo aquí.` : "Todavía no hay industria definida en la organización activa.",
      href: "/organizations",
      cta: "Ir a organizaciones",
    },
    {
      title: activationBot ? "Reconfigurar asistente operativo existente" : "Crear asistente operativo",
      description: activationBot
        ? `${safeText(activationBot.name)} ya existe. El setup real, diff y apply viven en Bot Studio con wizard_id persistido.`
        : "Si todavía no hay bot, Bot Studio ahora es el único lugar que crea y aplica el setup real del asistente operativo.",
      href: activationBot ? `/bot-studio?mode=reconfigure&bot=${encodeURIComponent(activationBot.id)}` : "/bot-studio?mode=create",
      cta: activationBot ? "Abrir Bot Studio en reconfiguración" : "Abrir Bot Studio en creación",
    },
    {
      title: "Conectar canal principal",
      description: connectedIntegrations.length ? `${formatNumber(connectedIntegrations.length)} canal(es) ya están conectados.` : "Sin canal principal, el onboarding sigue siendo teórico.",
      href: "/integrations",
      cta: "Ir a integraciones",
    },
    {
      title: "Validar y publicar",
      description: guidedWizard?.id
        ? `El último wizard guardado es ${safeText(guidedWizard.id)}. Cuando termines el setup real, la validación y publish siguen desde releases.`
        : "Después del setup real, releases queda como la estación final de validación y publicación.",
      href: "/releases",
      cta: "Ir a releases",
    },
  ];

  const readinessItems = [
    {
      title: "Organización activa",
      detail: currentOrg ? `${currentOrg.name} · ${safeText(currentOrg.vertical, "sin industria")}` : "No hay organización activa visible.",
      tone: currentOrg ? "green" as const : "red" as const,
    },
    {
      title: "Oferta visible",
      detail: totalOffer ? `${formatNumber(totalOffer)} elementos visibles entre catálogo, servicios y promociones.` : "Todavía no hay oferta mínima visible.",
      tone: totalOffer ? "green" as const : "gold" as const,
    },
    {
      title: "Canales conectados",
      detail: connectedIntegrations.length ? `${formatNumber(connectedIntegrations.length)} canal(es) conectados.` : "Todavía no hay canal principal conectado.",
      tone: connectedIntegrations.length ? "green" as const : "red" as const,
    },
    {
      title: "Asistente operativo explícito",
      detail: activationBot ? `${safeText(activationBot.name)} es el asistente operativo actualmente detectado por el readiness.` : "No se forzó ningún asistente operativo por cookie ni se cayó al primero de la lista.",
      tone: activationBot ? "green" as const : "gold" as const,
    },
  ];

  const demoFlow = verticalProfile.demo_flow?.length
    ? verticalProfile.demo_flow.map((item, index) => ({ title: `Paso ${index + 1}`, detail: safeText(item), tone: index === 0 ? "green" as const : "slate" as const }))
    : [
        { title: "Cliente escribe", detail: "Pregunta por producto, cita o disponibilidad.", tone: "green" as const },
        { title: "Asistente operativo responde", detail: "Califica intención y propone el siguiente paso.", tone: "slate" as const },
        { title: "Operación interviene", detail: "Si sube urgencia o relación, el inbox prioriza takeover humano.", tone: "slate" as const },
        { title: "Se publica", detail: "Solo después de probar de punta a punta.", tone: "slate" as const },
      ];

  return (
    <Shell
      title="Onboarding"
      subtitle="Onboarding ya no crea asistentes operativos ni compite con setup. Aquí solo ves readiness, checklist, bloqueadores y el siguiente paso real dentro del producto."
      action={<Link href={safeText(String(activation.next_step?.href || "/bot-studio?mode=create"), "/bot-studio?mode=create")} className="primary-btn">{safeText(String(activation.next_step?.label || "Ir al siguiente paso"))}</Link>}
    >
      <ContextTip title="Qué hace cada módulo">
        Onboarding = readiness, checklist y estado. Bot Studio = crear o reconfigurar. Integraciones = conectar o probar. Releases = publicar. Inbox = operar. Esta vista solo orquesta bloqueadores y te empuja al módulo correcto.
      </ContextTip>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Readiness" value={`${formatNumber(readiness)}%`} hint={`Modo ${safeText(activation.tenant_mode || "sandbox")}`} icon="target" tone={String(activation.tenant_mode || "sandbox") === "go_live" ? "green" : "gold"} />
        <StatCard label="Oferta visible" value={formatNumber(totalOffer)} hint="Productos, servicios y promociones" icon="catalog" tone="green" />
        <StatCard label="Canales conectados" value={formatNumber(connectedIntegrations.length)} hint="Dónde te pueden escribir ya" icon="plug" tone="blue" />
        <StatCard label="Asistentes operativos visibles" value={formatNumber(bots.length)} hint="Sin asumir uno por default" icon="bot" tone="gold" />
        <StatCard label="Último wizard" value={safeText(guidedWizard?.status, "sin wizard")} hint={safeText(guidedWizard?.id, "todavía no hay wizard persistido")} icon="wand" tone="slate" />
      </div>

      <Section title="Control tower de activación" subtitle="Qué está listo, qué bloquea y cuál es el siguiente módulo dueño del siguiente paso real dentro del producto." icon="target">
        <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
            <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Siguiente paso recomendado</div>
            <div className="mt-2 text-2xl font-semibold text-white">{safeText(String(activation.next_step?.label || "Continuar setup"))}</div>
            <p className="mt-3 text-sm leading-7 text-slate-300">{safeText(String(activation.next_step?.reason || "Cierra los bloqueadores principales antes de publicar."))}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link href={safeText(String(activation.next_step?.href || "/bot-studio?mode=create"), "/bot-studio?mode=create")} className="primary-btn">Ejecutar siguiente paso</Link>
              <Link href="/bot-studio?mode=create" className="secondary-btn">Abrir Bot Studio</Link>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {Object.entries(activation.progress || {}).map(([key, value]) => (
                <div key={key} className="surface-row">
                  <div className="text-xs uppercase tracking-[0.16em] text-slate-500">{safeText(key)}</div>
                  <div className="mt-1 text-lg font-semibold text-white">{formatNumber(Number(value || 0))}%</div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
            <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Modo actual</div>
            <div className="mt-2 text-2xl font-semibold text-white">{String(activation.tenant_mode || "sandbox") === "go_live" ? "Go live" : "Sandbox"}</div>
            <p className="mt-3 text-sm leading-7 text-slate-300">{String(activation.tenant_mode || "sandbox") === "go_live" ? "La cuenta ya está marcada para operar en vivo." : "La cuenta sigue en modo controlado para prueba y validación."}</p>
            {currentOrg ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <form action={setTenantModeAction}>
                  <input type="hidden" name="organization_id" value={currentOrg.id} />
                  <input type="hidden" name="tenant_mode" value="sandbox" />
                  <input type="hidden" name="redirect_to" value="/onboarding" />
                  <button className="secondary-btn w-full" type="submit">Poner en sandbox</button>
                </form>
                <form action={setTenantModeAction}>
                  <input type="hidden" name="organization_id" value={currentOrg.id} />
                  <input type="hidden" name="tenant_mode" value="go_live" />
                  <input type="hidden" name="redirect_to" value="/onboarding" />
                  <button className="primary-btn w-full" type="submit">Marcar go live</button>
                </form>
              </div>
            ) : null}
            <div className="mt-5">
              <TimelineList items={(activation.blockers || []).length
                ? (activation.blockers || []).map((item) => ({
                    title: safeText(String(item.message || item.key || "Bloqueador")),
                    detail: safeText(String(item.severity || "info")),
                    tone: String(item.severity || "medium") === "high" ? "red" as const : "gold" as const,
                  }))
                : [{ title: "Sin bloqueadores mayores", detail: "La cuenta ya tiene base para seguir avanzando.", tone: "green" as const }]} />
            </div>
          </div>
        </div>
      </Section>

      <Section title="Estado actual sin selección silenciosa" subtitle="Readiness visible sin caer por default al primer bot de la lista." icon="route">
        <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
          <div>
            <TimelineList items={readinessItems} />
            <div className="mt-5 grid gap-3 xl:grid-cols-2">
              {(activation.checklist || []).map((item, index) => (
                <ModuleCard
                  key={`${String(item.key || index)}`}
                  title={safeText(String(item.label || item.key || "Checklist"))}
                  description={Boolean(item.completed) ? "Listo para salir." : "Todavía pendiente antes de publicar."}
                  icon={Boolean(item.completed) ? "check" : "alert"}
                  tone={Boolean(item.completed) ? "green" : "gold"}
                />
              ))}
            </div>
          </div>
          <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Bot y wizard activos</div>
            <div className="mt-4 grid gap-3 text-sm leading-6 text-[color:var(--text-secondary)]">
              <div className="surface-row"><span>Asistente operativo explícito</span><strong>{safeText(activationBot?.name, "ninguno")}</strong></div>
              <div className="surface-row"><span>Vertical actual</span><strong>{safeText(activationBot?.vertical || currentOrg?.vertical, "sin definir")}</strong></div>
              <div className="surface-row"><span>Tipo de operación actual</span><strong>{safeText(currentOrg?.subvertical, verticalProfile.selected_subvertical?.name || "sin definir")}</strong></div>
              <div className="surface-row"><span>Wizard persistido</span><strong>{safeText(guidedWizard?.id, "sin wizard")}</strong></div>
              <div className="surface-row"><span>Status wizard</span><strong>{safeText(guidedWizard?.status, "draft")}</strong></div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link href={activationBot ? `/bot-studio?mode=reconfigure&bot=${encodeURIComponent(activationBot.id)}` : "/bot-studio?mode=create"} className="primary-btn">Ir a Bot Studio</Link>
              {guidedWizard?.id ? <Link href={`/bot-studio?mode=${activationBot ? "reconfigure" : "create"}&wizard_id=${encodeURIComponent(String(guidedWizard.id))}${activationBot ? `&bot=${encodeURIComponent(activationBot.id)}` : ""}`} className="secondary-btn">Retomar wizard</Link> : null}
            </div>
          </div>
        </div>
      </Section>

      <Section title="Dónde ejecutar cada cosa" subtitle="Un patrón único para producto, frontend y backend." icon="wand">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {executionLinks.map((item) => (
            <ModuleCard
              key={item.title}
              title={item.title}
              description={item.description}
              icon="play"
              tone="blue"
              footer={<Link href={item.href} className="secondary-btn">{item.cta}</Link>}
            />
          ))}
        </div>
      </Section>

      <Section title="Prueba mental del flujo" subtitle="La vista de readiness explica el recorrido, pero no ejecuta setup." icon="play">
        <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
          <TimelineList items={demoFlow} />
          <ModuleCard
            title="Regla nueva"
            description="Onboarding no vuelve a pedir vertical ni vuelve a crear bot. Solo muestra readiness, checklist, bloqueadores y el CTA correcto hacia Bot Studio u otras estaciones operativas."
            icon="check"
            tone="green"
            footer={<Link href="/bot-studio?mode=create" className="primary-btn">Abrir setup real</Link>}
          />
        </div>
      </Section>
    </Shell>
  );
}
