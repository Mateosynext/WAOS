import Link from "next/link";
import { applyBotVerticalAction, createBotAction, requestReleaseAction, switchBotAction, updateOrganizationVerticalAction } from "../actions";
import { ContextTip, EmptyActionState, ModuleCard, Section, Shell, StageRail, StatCard, SuccessState, SecondaryNav, TimelineList } from "../components";
import { getCurrentBotId, getSession } from "../lib/session";
import { formatNumber, safeText } from "../lib/ui";
import { getAgendaOverview, getBotBehavior, getBotTemplates, getBots, getBusinessHubOverview, getIntegrations, getReleaseReadiness, getVerticalCatalog, getVerticalProfile } from "../lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;

type ReadinessItem = {
  title: string;
  ok: boolean;
  detail: string;
  href?: string;
  action?: string;
  tone?: "slate" | "green" | "gold" | "red" | "blue";
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function normalizeStep(value: string | undefined) {
  if (!value) return "cuenta";
  if (value === "probar") return "validar";
  return value;
}

function normalizeTokens(value: unknown) {
  const input = String(value || "").toLowerCase();
  const compact = input.replace(/[^a-z0-9]+/g, " ").trim();
  const tokens = new Set(compact.split(/\s+/).filter(Boolean));
  if (compact.includes("whatsapp")) tokens.add("whatsapp");
  if (compact.includes("calendar") || compact.includes("google")) {
    tokens.add("calendar");
    tokens.add("google_calendar");
  }
  if (compact.includes("payment") || compact.includes("stripe") || compact.includes("cobro")) {
    tokens.add("payments");
    tokens.add("payment");
  }
  if (compact.includes("crm") || compact.includes("lead")) tokens.add("crm");
  if (compact.includes("commerce") || compact.includes("catalog")) tokens.add("commerce");
  if (compact.includes("webhook")) tokens.add("webhook");
  return tokens;
}

function integrationMatches(item: Record<string, unknown>, expected: string) {
  const expectedTokens = normalizeTokens(expected);
  const actualTokens = new Set<string>([
    ...normalizeTokens(item.integration_type),
    ...normalizeTokens(item.provider),
    ...normalizeTokens(item.name),
    ...normalizeTokens(item.status),
  ]);
  for (const token of expectedTokens) {
    if (actualTokens.has(token)) return true;
  }
  return false;
}

function readinessTone(ok: boolean, soft = false): "green" | "gold" | "red" {
  if (ok) return "green";
  return soft ? "gold" : "red";
}

export default async function OnboardingPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const step = normalizeStep(first(params.step));
  const session = await getSession();
  const currentOrg = session?.user.organizations.find((item) => item.id === session?.organizationId) || null;
  const currentBotId = await getCurrentBotId();

  const [bots, integrations, hub, agenda, verticals] = await Promise.all([
    getBots(),
    getIntegrations(),
    getBusinessHubOverview(),
    getAgendaOverview(),
    getVerticalCatalog(),
  ]);

  const selectedBot = bots.find((item) => item.id === currentBotId) || bots[0] || null;
  const selectedVerticalId = selectedBot?.vertical || currentOrg?.vertical || verticals[0]?.id || "";

  const [selectedVertical, rawBehavior, templates, releaseReadiness] = await Promise.all([
    getVerticalProfile(selectedVerticalId, selectedBot?.id),
    selectedBot?.id ? getBotBehavior(selectedBot.id) : Promise.resolve<Record<string, unknown>>({}),
    selectedBot?.id ? getBotTemplates(selectedBot.id) : Promise.resolve([]),
    selectedBot?.id ? getReleaseReadiness(selectedBot.id) : Promise.resolve({ bot_id: "", summary: {}, checklist: {}, checklist_items: [], blockers: [], warnings: [], integrations: [], validation: {}, diff_summary: {} }),
  ]);

  const behavior = rawBehavior as Record<string, unknown>;
  const releaseReadinessSummary = (releaseReadiness.summary || {}) as Record<string, unknown>;

  const summary = hub.summary || {};
  const connectedIntegrations = integrations.filter((item) => ["active", "configured", "connected"].includes(String(item.status || "").toLowerCase()));
  const matchedRecommendedIntegrations = connectedIntegrations.filter((item) => selectedVertical.recommended_integrations.some((expected) => integrationMatches(item as Record<string, unknown>, expected)));
  const hasBots = bots.length > 0;
  const hasTemplates = templates.length > 0;
  const hasBehavior = Boolean(behavior && (behavior.bot_mode || behavior.tone || behavior.response_length));
  const hasContent = Number(summary.products || 0) > 0 || Number(summary.services || 0) > 0 || Number(summary.promotions || 0) > 0;
  const hasConnectedChannel = Boolean(selectedBot?.connection_status === "connected" || matchedRecommendedIntegrations.length > 0);
  const hasOrgVertical = Boolean(currentOrg?.vertical);
  const hasBotVertical = Boolean(selectedBot?.vertical);
  const validationScore = typeof selectedBot?.validation_score === "number" ? selectedBot.validation_score : null;
  const validationReady = validationScore !== null ? validationScore >= 80 : hasBehavior && hasTemplates && hasContent;
  const appointmentsVisible = Number((agenda.upcoming || []).length || 0) > 0;
  const readyToPublish = Boolean(releaseReadinessSummary.can_publish_release) || (hasOrgVertical && hasBots && hasBotVertical && hasConnectedChannel && hasBehavior && hasTemplates && hasContent && validationReady);

  const readiness: ReadinessItem[] = [
    {
      title: "Vertical en la organizacion",
      ok: hasOrgVertical,
      detail: hasOrgVertical ? `La organizacion activa ya opera como ${safeText(currentOrg?.vertical, "vertical")}.` : "Falta definir la vertical del tenant para que WAOS cargue lenguaje, objetos y foco operativo.",
      href: "/onboarding?step=cuenta",
      action: "Definir vertical",
    },
    {
      title: "Canal principal conectado",
      ok: hasConnectedChannel,
      detail: hasConnectedChannel ? `Ya hay ${formatNumber(matchedRecommendedIntegrations.length || connectedIntegrations.length)} integracion(es) conectadas para mover conversaciones reales.` : "Conecta WhatsApp o la integracion principal antes de pedirle al bot que salga a produccion.",
      href: "/integrations",
      action: "Conectar canal",
    },
    {
      title: "Bot creado",
      ok: hasBots,
      detail: hasBots ? `${formatNumber(bots.length)} bot(s) creados para la organizacion activa.` : "Todavia no existe un bot sembrado con vertical y configuracion base.",
      href: "/onboarding?step=bot",
      action: "Crear bot",
    },
    {
      title: "Vertical aplicada al bot",
      ok: hasBotVertical,
      detail: hasBotVertical ? `El bot seleccionado ya usa ${safeText(selectedBot?.vertical, "vertical")}.` : "El bot existe, pero aun no esta verticalizado para una operacion real.",
      href: "/onboarding?step=bot",
      action: "Aplicar vertical",
    },
    {
      title: "Comportamiento sembrado",
      ok: hasBehavior,
      detail: hasBehavior ? `Modo ${safeText(behavior.bot_mode, "configurado")} con tono ${safeText(behavior.tone, "definido")}.` : "Aun no se ve comportamiento operativo sembrado para el bot seleccionado.",
      href: "/bot-studio",
      action: "Configurar comportamiento",
    },
    {
      title: "Plantillas listas",
      ok: hasTemplates,
      detail: hasTemplates ? `${formatNumber(templates.length)} plantillas visibles para arrancar conversaciones, seguimiento y reactivacion.` : "Faltan templates sembrados para arrancar mensajes clave y followups.",
      href: "/bot-studio",
      action: "Sembrar templates",
    },
    {
      title: "Contenido base cargado",
      ok: hasContent,
      detail: hasContent ? `Hay ${formatNumber(Number(summary.products || 0) + Number(summary.services || 0) + Number(summary.promotions || 0))} items visibles entre catalogo y promociones.` : "Sin productos, servicios o promociones la validacion se queda superficial.",
      href: "/catalog",
      action: "Cargar contenido",
    },
    {
      title: "Validacion operativa",
      ok: validationReady,
      detail: validationScore !== null ? `Score actual: ${formatNumber(validationScore)}.` : validationReady ? "El bot pasa la validacion funcional basica segun comportamiento, templates y contenido." : "Todavia no hay senal suficiente para considerar al bot listo.",
      href: selectedBot ? `/bots/${selectedBot.id}` : "/bots",
      action: "Revisar bot",
    },
  ];

  const blockers = readiness.filter((item) => !item.ok);
  const productionNarrative = readyToPublish
    ? "La vertical, el bot, el canal y el contenido ya estan alineados. Lo siguiente es publicar con disciplina de release y monitoreo."
    : blockers.length
      ? `Todavia no esta listo para salir. El bloqueo principal hoy es: ${blockers[0]?.title.toLowerCase()}.`
      : "Ya hay senal para seguir con release, pero conviene revisar el checklist final antes de publicar.";

  const stepConfig: Record<string, { title: string; subtitle: string; actionLabel: string; actionHref: string }> = {
    cuenta: { title: "Elegir vertical", subtitle: "Primero define la vertical del tenant. Todo el wizard se ordena desde ahi.", actionLabel: hasOrgVertical ? "Siguiente paso" : "Guardar vertical", actionHref: hasOrgVertical ? "/onboarding?step=canal" : "/organizations" },
    canal: { title: "Conectar canal", subtitle: "Conecta al menos el canal principal recomendado para tu vertical antes de validar experiencia.", actionLabel: hasConnectedChannel ? "Siguiente paso" : "Ir a integraciones", actionHref: hasConnectedChannel ? "/onboarding?step=bot" : "/integrations" },
    bot: { title: "Crear o alinear bot", subtitle: "Crea un bot nuevo con vertical o reaplica la vertical al bot actual para sembrar defaults productivos.", actionLabel: hasBots ? "Validar setup" : "Crear bot", actionHref: hasBots ? "/onboarding?step=validar" : "/bot-studio" },
    validar: { title: "Validar operacion", subtitle: "Revisa comportamiento, templates, contenido y score antes de pensar en release.", actionLabel: readyToPublish ? "Ir a publicar" : "Cerrar huecos", actionHref: readyToPublish ? "/onboarding?step=publicar" : "/catalog" },
    publicar: { title: "Listo para produccion", subtitle: "Pasa por release, seguridad y observabilidad con una senal clara de go/no-go.", actionLabel: readyToPublish ? "Abrir releases" : "Volver a checklist", actionHref: readyToPublish ? "/releases" : "/onboarding?step=validar" },
  };
  const current = stepConfig[step] || stepConfig.cuenta;

  return (
    <Shell title={`Onboarding por vertical · ${current.title}`} subtitle={current.subtitle} action={<Link href={current.actionHref} className="primary-btn">{current.actionLabel}</Link>}>
      <SecondaryNav items={[
        { href: "/onboarding?step=cuenta", label: "1. Vertical", active: step === "cuenta" },
        { href: "/onboarding?step=canal", label: "2. Canal", active: step === "canal" },
        { href: "/onboarding?step=bot", label: "3. Bot", active: step === "bot" },
        { href: "/onboarding?step=validar", label: "4. Validar", active: step === "validar" },
        { href: "/onboarding?step=publicar", label: "5. Publicar", active: step === "publicar" },
      ]} />

      <ContextTip>
        Este wizard ya no es solo navegacion. Usa la vertical activa para decirte que configurar, que validar y que te sigue faltando para estar listo de verdad.
      </ContextTip>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Vertical activa" value={safeText(selectedVertical.short_name || currentOrg?.vertical, "sin definir")} hint="Marco operativo actual" icon="layers" tone="green" />
        <StatCard label="Integraciones recomendadas conectadas" value={formatNumber(matchedRecommendedIntegrations.length)} hint="Coincidencia con la vertical" icon="plug" tone="blue" />
        <StatCard label="Templates sembrados" value={formatNumber(templates.length)} hint="Mensajes base visibles" icon="wand" tone="gold" />
        <StatCard label="Checklist listo" value={formatNumber(readiness.filter((item) => item.ok).length)} hint={`${formatNumber(readiness.length)} puntos revisados`} icon="check" tone="slate" />
      </div>

      <Section title="Ruta guiada" subtitle="Cada paso te muestra lo minimo necesario para avanzar sin perder el hilo operativo." icon="route">
        <StageRail activeStep={step} steps={[
          { id: "cuenta", label: "Elegir vertical", detail: "Definir lenguaje, objetos y problema estructural." },
          { id: "canal", label: "Conectar canal", detail: "Alinear integraciones recomendadas a la vertical." },
          { id: "bot", label: "Crear o alinear bot", detail: "Sembrar comportamiento y templates listos." },
          { id: "validar", label: "Validar", detail: "Cerrar huecos antes de release." },
          { id: "publicar", label: "Publicar", detail: "Salir con una senal clara de go/no-go." },
        ]} />
      </Section>

      <Section title="Checklist maestro" subtitle="Aqui ves la lectura real del sistema, no una lista estatica." icon="check">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {readiness.map((item) => (
            <ModuleCard
              key={item.title}
              title={item.title}
              description={item.detail}
              icon={item.ok ? "check" : "alert"}
              tone={readinessTone(item.ok, item.title === "Validacion operativa")}
              footer={item.href ? <Link href={item.href} className="secondary-btn">{item.action || "Abrir"}</Link> : undefined}
            />
          ))}
        </div>
      </Section>

      {step === "cuenta" ? (
        <Section title="Paso 1 · Definir vertical del tenant" subtitle="La vertical del tenant gobierna el lenguaje, objetos, followups y recomendaciones del resto del wizard." icon="layers">
          {currentOrg ? (
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
              <form action={updateOrganizationVerticalAction} className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <input type="hidden" name="organization_id" value={currentOrg.id} />
                <input type="hidden" name="redirect_to" value="/onboarding?step=canal" />
                <label className="field-label">Organizacion activa
                  <input className="field-input" value={currentOrg.name} readOnly />
                </label>
                <label className="field-label">Vertical madre
                  <select className="field-input" name="vertical" defaultValue={currentOrg.vertical || selectedVertical.id} required>
                    {verticals.map((vertical) => <option key={vertical.id} value={vertical.id}>{vertical.name}</option>)}
                  </select>
                </label>
                <div className="flex items-end">
                  <button className="primary-btn w-full" type="submit">Guardar vertical y seguir</button>
                </div>
              </form>
              <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-slate-500">Preview vertical</div>
                <h3 className="mt-2 text-xl font-semibold text-white">{safeText(selectedVertical.name, "Vertical")}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-300">{safeText(selectedVertical.problem, "Esta vertical ya viene lista para ordenar el problema principal del cliente.")}</p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <ModuleCard title="Subverticales" description={selectedVertical.subverticals.join(", ") || "Sin subverticales definidas"} icon="folder" tone="slate" />
                  <ModuleCard title="Objetos operativos" description={selectedVertical.objects.join(" · ") || "Sin objetos definidos"} icon="catalog" tone="blue" />
                </div>
              </div>
            </div>
          ) : (
            <EmptyActionState title="Primero fija una organizacion" description="El wizard necesita tenant activo para no meter ambiguedad en multi-tenant." primaryAction={<Link href="/organizations" className="primary-btn">Seleccionar organizacion</Link>} />
          )}
        </Section>
      ) : null}

      {step === "canal" ? (
        <Section title="Paso 2 · Conectar canal recomendado" subtitle="No todas las integraciones pesan igual. Aqui ves primero las que tu vertical necesita para operar bien." icon="plug">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {selectedVertical.recommended_integrations.map((integration) => {
              const ok = matchedRecommendedIntegrations.some((item) => integrationMatches(item as Record<string, unknown>, integration));
              return (
                <ModuleCard
                  key={integration}
                  title={integration.replace(/_/g, " ")}
                  description={ok ? "Ya existe una integracion conectada o configurada que cubre este frente." : "Todavia no aparece una integracion conectada para este frente operativo."}
                  icon={ok ? "check" : "plug"}
                  tone={readinessTone(ok, true)}
                  footer={<Link href="/integrations" className="secondary-btn">{ok ? "Revisar" : "Conectar"}</Link>}
                />
              );
            })}
          </div>
          <div className="mt-5">
            {hasConnectedChannel ? (
              <SuccessState title="La base de canales ya existe" description={`Detectamos ${formatNumber(matchedRecommendedIntegrations.length || connectedIntegrations.length)} integracion(es) conectadas. El siguiente paso es crear o alinear el bot con la vertical.`} actions={<Link href="/onboarding?step=bot" className="primary-btn">Ir a bot</Link>} />
            ) : (
              <EmptyActionState title="Todavia no hay canal principal conectado" description="Conecta primero WhatsApp o la integracion clave de esta vertical para que el bot no se quede en maqueta." primaryAction={<Link href="/integrations" className="primary-btn">Abrir integraciones</Link>} secondaryAction={<Link href="/status" className="secondary-btn">Ver estado</Link>} />
            )}
          </div>
        </Section>
      ) : null}

      {step === "bot" ? (
        <Section title="Paso 3 · Crear o alinear bot" subtitle="Este paso ya trae formularios reales para no salir del wizard." icon="wand">
          {currentOrg ? (
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
              <div className="space-y-5">
                <form action={createBotAction} className="grid gap-4 md:grid-cols-2">
                  <input type="hidden" name="organization_id" value={currentOrg.id} />
                  <input type="hidden" name="redirect_to" value="/onboarding?step=validar" />
                  <label className="field-label">Vertical
                    <select className="field-input" name="vertical" defaultValue={currentOrg.vertical || selectedVertical.id} required>
                      {verticals.map((vertical) => <option key={vertical.id} value={vertical.id}>{vertical.name}</option>)}
                    </select>
                  </label>
                  <label className="field-label">Objetivo primario
                    <select className="field-input" name="primary_objective" defaultValue="agendar">
                      <option value="agendar">Agendar</option>
                      <option value="vender">Vender</option>
                      <option value="calificar">Calificar</option>
                      <option value="responder">Responder</option>
                      <option value="reactivar">Reactivar</option>
                    </select>
                  </label>
                  <label className="field-label">Nombre del negocio
                    <input className="field-input" name="business_name" placeholder="Ej. WAOS Dental Polanco" required />
                  </label>
                  <label className="field-label">Nombre del bot
                    <input className="field-input" name="bot_name" placeholder="Ej. Sofia" required />
                  </label>
                  <label className="field-label">Tono base
                    <input className="field-input" name="tone" defaultValue="amable" />
                  </label>
                  <label className="field-label">Horario inicial
                    <input className="field-input" name="hours" placeholder="Lun-Vie 9:00-18:00" />
                  </label>
                  <label className="field-label">Idioma
                    <select className="field-input" name="language" defaultValue="es">
                      <option value="es">Espanol</option>
                      <option value="en">English</option>
                    </select>
                  </label>
                  <label className="field-label">WhatsApp (opcional)
                    <input className="field-input" name="whatsapp_number" placeholder="+525512345678" />
                  </label>
                  <input type="hidden" name="timezone" value={currentOrg.timezone || "America/Mexico_City"} />
                  <label className="field-label flex items-center gap-3 md:col-span-2">
                    <input type="checkbox" name="publish_now" defaultChecked />
                    <span>Publicar primer draft al crear</span>
                  </label>
                  <div className="md:col-span-2">
                    <button className="primary-btn" type="submit">Crear bot desde el wizard</button>
                  </div>
                </form>

                {selectedBot ? (
                  <form action={applyBotVerticalAction} className="grid gap-4 md:grid-cols-2 rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
                    <input type="hidden" name="bot_id" value={selectedBot.id} />
                    <input type="hidden" name="redirect_to" value="/onboarding?step=validar" />
                    <label className="field-label">Bot actual
                      <input className="field-input" value={selectedBot.name} readOnly />
                    </label>
                    <label className="field-label">Aplicar vertical
                      <select className="field-input" name="vertical" defaultValue={selectedBot.vertical || currentOrg.vertical || selectedVertical.id} required>
                        {verticals.map((vertical) => <option key={vertical.id} value={vertical.id}>{vertical.name}</option>)}
                      </select>
                    </label>
                    <div className="md:col-span-2">
                      <button className="primary-btn" type="submit">Reaplicar vertical y sembrar defaults</button>
                    </div>
                  </form>
                ) : null}
              </div>

              <div className="space-y-5">
                {bots.length > 1 ? (
                  <form action={switchBotAction} className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
                    <input type="hidden" name="redirect_to" value="/onboarding?step=bot" />
                    <label className="field-label">Bot enfocado en el wizard
                      <select className="field-input" name="bot_id" defaultValue={selectedBot?.id || ""}>
                        {bots.map((bot) => <option key={bot.id} value={bot.id}>{bot.name}</option>)}
                      </select>
                    </label>
                    <div className="mt-4"><button className="secondary-btn" type="submit">Cambiar bot</button></div>
                  </form>
                ) : null}

                <ModuleCard title="Vertical objetivo" description={safeText(selectedVertical.problem, "Vertical lista para operar.")} icon="layers" tone="green" footer={<span className="mono-pill">{safeText(selectedVertical.short_name, "perfil")}</span>} />
                <ModuleCard title="Flujos clave" description={selectedVertical.flows.join(" · ") || "Sin flujos definidos"} icon="route" tone="blue" />
                <ModuleCard title="KPIs esperados" description={selectedVertical.kpis.join(" · ") || "Sin KPIs definidos"} icon="stats" tone="gold" />
              </div>
            </div>
          ) : (
            <EmptyActionState title="Primero selecciona una organizacion" description="Sin tenant activo este paso no puede crear ni alinear un bot real." primaryAction={<Link href="/organizations" className="primary-btn">Seleccionar organizacion</Link>} />
          )}
        </Section>
      ) : null}

      {step === "validar" ? (
        <Section title="Paso 4 · Validar setup" subtitle="El wizard junta comportamiento, templates, contenido y score para que no publiques a ciegas." icon="check">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Bot enfocado" value={safeText(selectedBot?.name, "sin bot")} hint="Bot activo del wizard" icon="bot" tone="green" />
            <StatCard label="Modo del bot" value={safeText(behavior.bot_mode, "sin modo")} hint="Senal de comportamiento sembrado" icon="spark" tone="blue" />
            <StatCard label="Templates" value={formatNumber(templates.length)} hint="Plantillas visibles" icon="wand" tone="gold" />
            <StatCard label="Score" value={validationScore !== null ? formatNumber(validationScore) : "-"} hint="Senal operativa actual" icon="stats" tone="slate" />
          </div>
          {blockers.length ? (
            <TimelineList items={blockers.map((item) => ({ title: item.title, detail: item.detail, tone: item.title === "Validacion operativa" ? "gold" : "red" }))} />
          ) : (
            <SuccessState title="No hay huecos criticos visibles" description="La lectura actual del sistema ya te deja pasar al paso de publicacion con buena disciplina operativa." actions={<Link href="/onboarding?step=publicar" className="primary-btn">Ir a publicar</Link>} />
          )}
          <div className="mt-5 grid gap-4 md:grid-cols-3">
            <ModuleCard title="Comportamiento" description={hasBehavior ? `Tono ${safeText(behavior.tone, "definido")} y modo ${safeText(behavior.bot_mode, "activo")}.` : "Aun no se detecta comportamiento sembrado para el bot."} icon="bot" tone={readinessTone(hasBehavior, true)} footer={<Link href="/bot-studio" className="secondary-btn">Abrir bot studio</Link>} />
            <ModuleCard title="Contenido" description={hasContent ? `Productos: ${formatNumber(Number(summary.products || 0))}. Servicios: ${formatNumber(Number(summary.services || 0))}. Promos: ${formatNumber(Number(summary.promotions || 0))}.` : "Todavia falta contenido visible para que la prueba sea seria."} icon="catalog" tone={readinessTone(hasContent, true)} footer={<Link href="/catalog" className="secondary-btn">Abrir catalogo</Link>} />
            <ModuleCard title="Experiencia cliente" description={appointmentsVisible ? `Ya hay ${formatNumber(Number((agenda.upcoming || []).length || 0))} citas o eventos visibles para revisar la historia completa.` : "Aun no hay suficiente movimiento visible para revisar experiencia con contexto."} icon="client" tone={readinessTone(appointmentsVisible, true)} footer={<Link href="/client" className="secondary-btn">Abrir portal cliente</Link>} />
          </div>
        </Section>
      ) : null}

      {step === "publicar" ? (
        <Section title="Paso 5 · Go / no-go de produccion" subtitle="Aqui ya solo queda responder si el sistema esta listo para salir con release y monitoreo." icon="rocket">
          {readyToPublish ? (
            <SuccessState title="Go: listo para produccion" description={productionNarrative} actions={<><Link href="/releases" className="primary-btn">Abrir releases</Link>{selectedBot ? <form action={requestReleaseAction}><input type="hidden" name="bot_id" value={selectedBot.id} /><input type="hidden" name="title" value={`Release ${selectedBot.name}`} /><input type="hidden" name="notes" value="Solicitado desde onboarding con semáforo listo." /><input type="hidden" name="redirect_to" value={`/releases?stage=all&bot_id=${encodeURIComponent(selectedBot.id)}`} /><button className="secondary-btn" type="submit">Solicitar release ahora</button></form> : null}<Link href="/status" className="secondary-btn">Ver estado</Link></>} />
          ) : (
            <EmptyActionState title="No-go: todavia hay huecos por cerrar" description={productionNarrative} primaryAction={<Link href={blockers[0]?.href || "/onboarding?step=validar"} className="primary-btn">Cerrar principal bloqueo</Link>} secondaryAction={<Link href="/onboarding?step=validar" className="secondary-btn">Volver a validar</Link>} />
          )}
          <div className="mt-5 mb-5 grid gap-4 md:grid-cols-3">
            <StatCard label="Semáforo" value={safeText(String(releaseReadinessSummary.status || (readyToPublish ? "green" : "red")))} hint={`${formatNumber(Number(releaseReadinessSummary.score || 0))} puntos`} icon="alert" tone={String(releaseReadinessSummary.status || "").toLowerCase() === "green" ? "green" : String(releaseReadinessSummary.status || "").toLowerCase() === "amber" ? "gold" : "red"} />
            <StatCard label="Bloqueos" value={formatNumber(Number(releaseReadinessSummary.blocking_count || blockers.length))} hint="Checks críticos pendientes" icon="alert" tone={Number(releaseReadinessSummary.blocking_count || blockers.length) ? "red" : "green"} />
            <StatCard label="Warnings" value={formatNumber(Number(releaseReadinessSummary.warning_count || 0))} hint="Señales no bloqueantes" icon="stats" tone="gold" />
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {readiness.map((item) => (
              <ModuleCard
                key={`publish-${item.title}`}
                title={item.title}
                description={item.detail}
                icon={item.ok ? "check" : "alert"}
                tone={readinessTone(item.ok, item.title !== "Canal principal conectado")}
                footer={item.href ? <Link href={item.href} className="secondary-btn">{item.action || "Abrir"}</Link> : undefined}
              />
            ))}
          </div>
        </Section>
      ) : null}
    </Shell>
  );
}
