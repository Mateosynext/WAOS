import Link from "next/link";
import { createBotAction, setTenantModeAction, updateOrganizationVerticalAction } from "../actions";
import { ContextTip, EmptyActionState, ModuleCard, Section, Shell, StageRail, StatCard, SuccessState, TimelineList } from "../components";
import { getCurrentBotId, getSession } from "../lib/session";
import { formatNumber, safeText } from "../lib/ui";
import { getActivationSummary, getBotBehavior, getBotTemplates, getBots, getBusinessHubOverview, getIntegrations, getVerticalCatalog, getVerticalProfile } from "../lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

function normalizeStep(value?: string) {
  if (value === "probar") return "probar";
  if (value === "responder") return "responder";
  if (value === "canal") return "canal";
  return "oferta";
}

export default async function OnboardingPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const step = normalizeStep(first(params.step));
  const session = await getSession();
  const currentOrg = session?.user.organizations.find((item) => item.id === session?.organizationId) || null;
  const currentBotId = await getCurrentBotId();

  const [bots, integrations, hub, verticals, activation] = await Promise.all([
    getBots(),
    getIntegrations(),
    getBusinessHubOverview(),
    getVerticalCatalog(),
    getActivationSummary(),
  ]);

  const selectedBot = bots.find((item) => item.id === currentBotId) || bots[0] || null;
  const [behavior, templates, verticalProfile] = await Promise.all([
    selectedBot?.id ? getBotBehavior(selectedBot.id) : Promise.resolve<Record<string, unknown>>({}),
    selectedBot?.id ? getBotTemplates(selectedBot.id) : Promise.resolve([]),
    getVerticalProfile(selectedBot?.vertical || currentOrg?.vertical || verticals[0]?.id),
  ]);

  const connectedIntegrations = integrations.filter((item) => ["active", "configured", "connected"].includes(String(item.status || "").toLowerCase()));
  const summary = hub.summary || {};
  const totalOffer = Number(summary.products || 0) + Number(summary.services || 0) + Number(summary.promotions || 0);
  const hasBehavior = Boolean(behavior && (behavior.bot_mode || behavior.tone || behavior.response_length));
  const hasTemplates = templates.length > 0;

  const steps = [
    { id: "oferta", title: "Qué vendes", detail: "Define vertical y oferta base" },
    { id: "canal", title: "Por dónde te escriben", detail: "Conecta el canal principal" },
    { id: "responder", title: "Cómo debe responder", detail: "Bot, tono y templates" },
    { id: "probar", title: "Pruébalo", detail: "Valida antes de salir" },
  ];

  const readiness = [
    { title: "Vertical definida", detail: currentOrg?.vertical ? `La organización ya usa ${currentOrg.vertical}.` : "Todavía no hay vertical activa en este tenant.", tone: currentOrg?.vertical ? "green" as const : "gold" as const },
    { title: "Oferta visible", detail: totalOffer ? `${formatNumber(totalOffer)} elementos visibles entre catálogo y promociones.` : "Sin oferta visible el bot no puede orientar ni vender bien.", tone: totalOffer ? "green" as const : "gold" as const },
    { title: "Canal conectado", detail: connectedIntegrations.length ? `${formatNumber(connectedIntegrations.length)} canal(es) conectados.` : "Todavía no hay canal principal conectado.", tone: connectedIntegrations.length ? "green" as const : "red" as const },
    { title: "Bot con comportamiento", detail: selectedBot ? `${safeText(selectedBot.name)} ya existe.${hasBehavior ? " También hay comportamiento base." : " Pero todavía falta sembrar comportamiento."}` : "Todavía no existe un bot activo para este tenant.", tone: selectedBot && hasBehavior ? "green" as const : selectedBot ? "gold" as const : "red" as const },
  ];

  const demoFlow = verticalProfile.demo_flow?.length ? verticalProfile.demo_flow : [
    { title: "Cliente escribe", detail: "Pregunta por producto, cita o disponibilidad." },
    { title: "Bot responde", detail: "Califica intención y propone siguiente paso." },
    { title: "Inbox toma contexto", detail: "Si sube urgencia o relación, se prioriza en operación." },
    { title: "Se valida", detail: "Antes de salir, se prueba el flujo completo con casos reales." },
  ];

  return (
    <Shell
      title="Puesta en marcha sin ruido"
      subtitle="Esta puesta en marcha sigue el orden mental correcto: qué vendes, por dónde te escriben, cómo debe responder y cómo probarlo antes de publicar."
      action={<Link href={step === "probar" ? "/releases" : `/onboarding?step=${step === "oferta" ? "canal" : step === "canal" ? "responder" : step === "responder" ? "probar" : "probar"}`} className="primary-btn">Continuar</Link>}
    >
      <ContextTip title="Cómo avanzar aquí">No necesitas entender palabras internas antes de tiempo. Primero cierras la intención del negocio; después conectas el sistema técnico.</ContextTip>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Oferta visible" value={formatNumber(totalOffer)} hint="Productos, servicios y promociones" icon="catalog" tone="green" />
        <StatCard label="Canales conectados" value={formatNumber(connectedIntegrations.length)} hint="Dónde te pueden escribir ya" icon="plug" tone="blue" />
        <StatCard label="Bots" value={formatNumber(bots.length)} hint="Bots visibles en este tenant" icon="bot" tone="gold" />
        <StatCard label="Templates" value={formatNumber(templates.length)} hint="Mensajes listos para operar" icon="stack" tone="slate" />
        <StatCard label="Readiness" value={`${formatNumber(Number(activation.readiness_score || 0))}%`} hint={`Modo ${safeText(activation.tenant_mode || "sandbox")}`} icon="target" tone={String(activation.tenant_mode || "sandbox") === "go_live" ? "green" : "gold"} />
      </div>

      <Section title="Control tower de activación vertical" subtitle="Ahora el onboarding ya lee el estado real del tenant, recomienda el siguiente paso y separa sandbox de go live." icon="target">
        <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
            <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Siguiente paso recomendado</div>
            <div className="mt-2 text-2xl font-semibold text-white">{safeText(String(activation.next_step?.label || "Continuar setup"))}</div>
            <p className="mt-3 text-sm leading-7 text-slate-300">{safeText(String(activation.next_step?.reason || "Cierra los bloqueadores principales antes de publicar."))}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link href={safeText(String(activation.next_step?.href || "/onboarding"), "/onboarding")} className="primary-btn">Ir al siguiente paso</Link>
              <Link href="/releases" className="secondary-btn">Ver release</Link>
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
              <TimelineList items={(activation.blockers || []).length ? (activation.blockers || []).map((item) => ({ title: safeText(String(item.message || item.key || "Bloqueador")), detail: safeText(String(item.severity || "info")), tone: String(item.severity || "medium") === "high" ? "red" : "gold" })) : [{ title: "Sin bloqueadores mayores", detail: "La cuenta ya tiene base para seguir avanzando.", tone: "green" as const }]} />
            </div>
          </div>
        </div>
      </Section>

      <Section title="Progreso visible y siguiente paso" subtitle="Qué ya quedó, qué sigue y qué está bloqueando de verdad." icon="route">
        <StageRail steps={steps} activeStep={step} />
        <div className="mt-5">
          <TimelineList items={readiness} />
        </div>
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
        <div className="mt-5 flex flex-wrap gap-2">
          <Link href="/business-hub" className="secondary-btn">Ver oferta</Link>
          <Link href="/integrations" className="secondary-btn">Ver canales</Link>
          <Link href="/bot-studio" className="secondary-btn">Abrir bot</Link>
        </div>
      </Section>

      {step === "oferta" ? (
        <Section title="1. Qué vendes" subtitle="Primero fija la vertical del tenant y deja una oferta mínima visible para que el bot tenga qué explicar." icon="briefcase">
          {currentOrg ? (
            <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
              <form action={updateOrganizationVerticalAction} className="grid gap-4 md:grid-cols-2">
                <input type="hidden" name="organization_id" value={currentOrg.id} />
                <input type="hidden" name="redirect_to" value="/onboarding?step=canal" />
                <label className="field-label">Organización
                  <input className="field-input" value={currentOrg.name} readOnly />
                </label>
                <label className="field-label">Tipo de negocio
                  <select className="field-input" name="vertical" defaultValue={currentOrg.vertical || ""} required>
                    <option value="">Selecciona una vertical</option>
                    {verticals.map((vertical) => <option key={vertical.id} value={vertical.id}>{vertical.name}</option>)}
                  </select>
                </label>
                <div className="md:col-span-2">
                  <button className="primary-btn" type="submit">Guardar vertical y seguir</button>
                </div>
              </form>
              <ModuleCard title="Referencia útil para no sentir la app vacía" description="Aunque todavía no tengas todo listo, esta vista ya te explica qué debería existir para que el producto no se sienta vacío: catálogo mínimo, promociones y templates básicos." icon="play" tone="blue" footer={<Link href="/business-hub?tab=catalogo" className="secondary-btn">Abrir centro comercial</Link>} />
            </div>
          ) : (
            <EmptyActionState title="Selecciona una organización primero" description="Sin tenant activo este wizard no puede sembrar vertical ni preparar oferta." primaryAction={<Link href="/organizations" className="primary-btn">Elegir organización</Link>} />
          )}
        </Section>
      ) : null}

      {step === "canal" ? (
        <Section title="2. Por dónde te escriben" subtitle="Conecta al menos un canal real antes de probar cualquier otra cosa." icon="plug">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {connectedIntegrations.length ? connectedIntegrations.map((item) => (
              <ModuleCard key={item.id || item.name} title={safeText(item.name || item.provider || item.integration_type, "Canal")} description={safeText(item.status, "Conectado")} icon="plug" tone="green" footer={<span className="mono-pill">{safeText(item.provider || item.integration_type || "canal")}</span>} />
            )) : <ModuleCard title="Aún no hay canal conectado" description="Empieza por WhatsApp o el canal principal que realmente usa tu negocio. Sin esto, el onboarding sigue siendo teórico." icon="alert" tone="gold" footer={<Link href="/integrations" className="secondary-btn">Conectar canal</Link>} />}
          </div>
        </Section>
      ) : null}

      {step === "responder" ? (
        <Section title="3. Cómo debe responder" subtitle="El bot debe quedar alineado con tu negocio antes de salir: vertical, tono, objetivo y templates." icon="bot">
          <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
            {currentOrg ? (
              <form action={createBotAction} className="grid gap-4 md:grid-cols-2">
                <input type="hidden" name="organization_id" value={currentOrg.id} />
                <label className="field-label">Nombre del negocio
                  <input className="field-input" name="business_name" defaultValue={currentOrg.name} required />
                </label>
                <label className="field-label">Nombre del bot
                  <input className="field-input" name="bot_name" placeholder="Ej. Sofía" required />
                </label>
                <label className="field-label">Vertical
                  <select className="field-input" name="vertical" defaultValue={selectedBot?.vertical || currentOrg.vertical || ""} required>
                    {verticals.map((vertical) => <option key={vertical.id} value={vertical.id}>{vertical.name}</option>)}
                  </select>
                </label>
                <label className="field-label">Objetivo principal
                  <select className="field-input" name="primary_objective" defaultValue="agendar">
                    <option value="agendar">Agendar</option>
                    <option value="vender">Vender</option>
                    <option value="calificar">Calificar</option>
                    <option value="responder">Responder</option>
                  </select>
                </label>
                <label className="field-label">Tono base
                  <input className="field-input" name="tone" defaultValue="amable" />
                </label>
                <label className="field-label">Idioma
                  <select className="field-input" name="language" defaultValue="es"><option value="es">Español</option><option value="en">English</option></select>
                </label>
                <div className="md:col-span-2 flex flex-wrap gap-2">
                  <button className="primary-btn" type="submit">Crear bot base</button>
                  {selectedBot ? <Link href="/bot-studio" className="secondary-btn">Reaplicar vertical al bot actual</Link> : null}
                </div>
              </form>
            ) : null}
            <div className="grid gap-4">
              <ModuleCard title="Comportamiento detectado" description={hasBehavior ? `Modo ${safeText(behavior.bot_mode)} con tono ${safeText(behavior.tone)}.` : "Todavía no vemos comportamiento suficiente en el bot activo."} icon="spark" tone={hasBehavior ? "green" : "gold"} />
              <ModuleCard title="Templates listos" description={hasTemplates ? `${formatNumber(templates.length)} templates visibles para arrancar conversación y seguimiento.` : "Faltan templates base para que el bot no improvise todo."} icon="stack" tone={hasTemplates ? "blue" : "gold"} />
            </div>
          </div>
        </Section>
      ) : null}

      {step === "probar" ? (
        <Section title="4. Pruébalo antes de publicar" subtitle="No publiques a ciegas. Simula un flujo real desde el mensaje de entrada hasta la intervención humana si aplica." icon="play">
          <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
            <div>
              <TimelineList items={demoFlow.map((item: any, index: number) => ({ title: safeText(item.title, `Paso ${index + 1}`), detail: safeText(item.detail || item.description, "Ruta de lanzamiento"), tone: index === 0 ? "green" : "slate" }))} />
              <div className="mt-4 flex flex-wrap gap-2">
                <Link href="/inbox" className="primary-btn">Abrir inbox</Link>
                <Link href="/releases" className="secondary-btn">Revisar release</Link>
              </div>
            </div>
            <SuccessState title="Checklist final" description="Antes de publicar, confirma que el bot entiende la oferta, puede entrar por el canal principal y deja el inbox operativo cuando se necesita takeover humano." />
          </div>
        </Section>
      ) : null}
    </Shell>
  );
}
