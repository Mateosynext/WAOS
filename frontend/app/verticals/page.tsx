import Link from "next/link";
import { Badge, ContextTip, DataTable, ModuleCard, Section, SegmentedLinks, Shell, StatCard } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getStrongestVerticals, getVerticalCatalog, getVerticalProfile } from "../lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

function tierLabel(value?: string) {
  switch (value) {
    case "tier_1": return "Tier 1";
    case "tier_2": return "Tier 2";
    case "tier_3_guarded": return "Tier 3 controlado";
    default: return safeText(value, "Sin tier");
  }
}

function toneForTier(value?: string): "green" | "blue" | "gold" | "slate" {
  switch (value) {
    case "tier_1": return "green";
    case "tier_2": return "blue";
    case "tier_3_guarded": return "gold";
    default: return "slate";
  }
}

function waveLabel(value?: string) {
  switch (value) {
    case "ola_1": return "Ola 1";
    case "ola_2": return "Ola 2";
    case "ola_3": return "Ola 3";
    default: return safeText(value, "Sin ola");
  }
}

export default async function VerticalsPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const selectedVerticalId = first(params.vertical);
  const selectedSubvertical = first(params.subvertical);
  const [verticals, strongestVerticals] = await Promise.all([getVerticalCatalog(), getStrongestVerticals()]);
  const selected = verticals.find((item) => item.id === selectedVerticalId) || (verticals.length === 1 ? verticals[0] : null);

  if (!selected) {
    return (
      <Shell
        title="Portafolio vertical WAOS"
        subtitle="No se pudo cargar el catálogo de verticales."
        action={<Link href="/bot-studio" className="primary-btn">Ir a Bot Studio</Link>}
      >
        <Section title="Elige una vertical" subtitle="Esta vista ya no cae silenciosamente a la primera vertical del catálogo." icon="layers">
          {verticals.length ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {verticals.map((item) => (
                <ModuleCard
                  key={item.id}
                  title={safeText(item.name)}
                  description={safeText(item.description || item.problem, "Sin descripción visible.")}
                  icon="layers"
                  tone="green"
                  footer={<Link href={`/verticals?vertical=${encodeURIComponent(item.id)}`} className="secondary-btn">Abrir vertical</Link>}
                />
              ))}
            </div>
          ) : (
            <ModuleCard
              title="Sin verticales disponibles"
              description="Recarga la página, vuelve a iniciar sesión o revisa la conexión del frontend con /api/v1/verticals."
              icon="alert"
              tone="red"
            />
          )}
        </Section>
      </Shell>
    );
  }

  const profile = await getVerticalProfile(selected.id, undefined, selectedSubvertical);
  const strongestIds = new Set(strongestVerticals.map((item) => item.id));

  const segmented = verticals.map((item) => ({
    href: `/verticals?vertical=${encodeURIComponent(item.id)}`,
    label: safeText(item.name).replace(/^WAOS\s+/i, ""),
    active: item.id === selected.id,
  }));

  const subverticalSegmented = (profile.subvertical_profiles.length ? profile.subvertical_profiles : profile.subverticals.map((item) => ({ id: item.toLowerCase().replace(/[^a-z0-9]+/g, "-"), name: item }))).map((item) => ({
    href: `/verticals?vertical=${encodeURIComponent(profile.id)}&subvertical=${encodeURIComponent(item.name)}` ,
    label: safeText(item.name),
    active: safeText(item.name).toLowerCase() === safeText(profile.selected_subvertical?.name).toLowerCase(),
  }));
  const activeSubvertical = profile.selected_subvertical || null;

  const pipelineRows = [
    ...(profile.pipeline.primary ? [[safeText(profile.pipeline.primary.name), safeText(profile.pipeline.primary.states.join(" • "), "Sin estados")]] : []),
    ...profile.pipeline.secondary.map((item) => [safeText(item.name), safeText(item.states.join(" • "), "Sin estados")]),
  ];

  const automationRows = profile.automation_sequences.map((item) => [
    safeText(item.name),
    safeText(item.trigger, "Sin trigger"),
    safeText(item.goal, "Sin objetivo"),
    safeText(item.steps.join(" • "), "Sin pasos"),
  ]);

  const dashboardRows = profile.dashboard.sections.map((section) => [safeText(section.name), safeText(section.metrics.join(" • "), "Sin métricas")]);
  const playbookRows = profile.subvertical_playbooks.map((item) => [safeText(item.name), safeText(item.focus, "Sin foco")]);
  const e2eRows = profile.business_e2e_tests.map((item, index) => [`${index + 1}`, safeText(item.name), safeText(item.status, "Sin estado")]);
  const runtimeTransitionRows = ((profile.vertical_runtime.pipeline_machine.transitions as Array<Record<string, unknown>>) || []).map((item) => [safeText(item.from), safeText(item.to), safeText(item.trigger), safeText(item.business_effect)]);
  const pricingRuleRows = ((profile.vertical_runtime.pricing_engine.rules as Array<Record<string, unknown>>) || []).map((item, index) => [`${index + 1}`, safeText(item.rule), safeText(item.effect)]);
  const recurrenceRows = ((profile.vertical_runtime.recurrence_engine.policies as Array<Record<string, unknown>>) || []).map((item) => [safeText(item.type), safeText(item.interval_days), safeText(item.anchor)]);
  const kpiFormulaRows = ((profile.vertical_runtime.kpi_engine.definitions as Array<Record<string, unknown>>) || []).map((item) => [safeText(item.name), safeText(item.formula)]);
  const automationPolicyRows = ((profile.vertical_runtime.automation_engine.money_automation_policies as Array<Record<string, unknown>>) || []).map((item) => [safeText(item.trigger), safeText(((item.actions as string[]) || []).join(" • ")), safeText(item.goal)]);
  const v12CommandRows = (profile.transactional_motor_v12.command_catalog || []).map((item, index) => [`${index + 1}`, safeText(item.command), safeText(item.writes), safeText(item.guard)]);
  const v12EventRows = (profile.transactional_motor_v12.event_catalog || []).map((item, index) => [`${index + 1}`, safeText(item.event), safeText(((item.updates as string[]) || []).join(" • ")), safeText(item.next_action)]);
  const v12ViewsRecord = profile.transactional_motor_v12.transaction_views as Record<string, unknown> || {};
  const v12ViewRows = Object.entries(v12ViewsRecord).map(([name, value]) => [safeText(name), safeText(((Array.isArray(value) ? value : []) as string[]).join(" • "))]);

  return (
    <Shell
      title="Portafolio vertical WAOS"
      subtitle="Una capa de producto y GTM para vender WAOS como sistema operativo conversacional por vertical, no como bot horizontal. Cada vertical baja a buyer, lanzamiento, objetos nativos, pipeline, playbook, automatizaciones y KPIs."
      action={<Link href="/onboarding" className="primary-btn">Ir a onboarding</Link>}
    >
      <Section title="Vertical activa" subtitle="Selecciona una línea de producto para ver su tesis comercial y operativa." icon="layers">
        <SegmentedLinks items={segmented} />
      </Section>

      <ContextTip title="Qué cambia con esta capa">
        WAOS ya no se presenta como un bot que responde, sino como una torre de control comercial y operativa sobre WhatsApp: inbox, takeover humano, memoria, follow-ups, agenda, pagos, catálogo, promociones, revenue, operaciones, insights, launch y despliegue.
      </ContextTip>


      <Section title="Las 5 verticales más fuertes" subtitle="Prioridad 10x para vender, activar y operar WAOS con más profundidad por vertical y subvertical." icon="rocket">
        <div className="grid gap-4 xl:grid-cols-5">
          {strongestVerticals.map((item) => (
            <ModuleCard
              key={item.id}
              title={`${item.strongest_rank || "-"}. ${safeText(item.name).replace(/^WAOS\s+/i, "")}`}
              description={safeText(item.ten_x_narrative, item.description)}
              icon="target"
              tone={item.id === profile.id ? "green" : "slate"}
              footer={<div className="text-xs text-slate-400">Score {safeText(item.ten_x_score)} • Subverticales foco: {safeText(item.recommended_subverticals.join(" • "), "Sin foco")}</div>}
            />
          ))}
        </div>
      </Section>

      <Section title="Resumen ejecutivo" subtitle="Lectura rápida para dirección, producto, ventas y onboarding." icon="briefcase">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Vertical" value={profile.name} hint={safeText(profile.description)} icon="stack" tone="green" />
          <StatCard label="Tier" value={tierLabel(profile.portfolio_tier)} hint="Prioridad del portafolio" icon="layers" tone={toneForTier(profile.portfolio_tier)} />
          <StatCard label="Subverticales" value={formatNumber(profile.subverticals.length)} hint="Cobertura de la familia" icon="folder" tone="blue" />
          <StatCard label="Integraciones" value={formatNumber(profile.recommended_integrations.length)} hint="Base operativa sugerida" icon="plug" tone="gold" />
          <StatCard label="Ola de endurecimiento" value={waveLabel(profile.hardening_model.wave)} hint="Prioridad recomendada" icon="rocket" tone="slate" />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          <ModuleCard title="Tesis maestra" description={safeText(profile.master_thesis, "Sin tesis definida.")} icon="target" tone="green" />
          <ModuleCard title="Buyer principal" description={safeText(profile.buyer.primary, "Sin buyer principal.")} icon="client" tone="blue" footer={<div className="text-xs text-slate-400">Secundarios: {safeText(profile.buyer.secondary.join(" • "), "Sin secundarios")}</div>} />
          <ModuleCard title="Problema estructural" description={safeText(profile.problem, "Sin problema definido.")} icon="alert" tone="gold" />
        </div>
      </Section>


      {profile.is_strongest_vertical ? (
        <Section title="Subvertical 10x" subtitle="Empaque táctico para bajar la vertical a una subvertical vendible, operable y medible." icon="spark">
          {subverticalSegmented.length ? <SegmentedLinks items={subverticalSegmented} /> : null}
          <div className="mt-4 grid gap-4 xl:grid-cols-4">
            <StatCard label="Score subvertical" value={safeText(activeSubvertical?.strength_score, "-")} hint={safeText(activeSubvertical?.growth_motion, "Sin motion")} icon="rocket" tone="green" />
            <StatCard label="Buyer" value={safeText(activeSubvertical?.buyer, profile.buyer.primary)} hint="Quién compra primero" icon="client" tone="blue" />
            <StatCard label="Servicios pack" value={formatNumber(activeSubvertical?.service_bundle.length || 0)} hint="Bundle seed aplicable" icon="folder" tone="gold" />
            <StatCard label="KPIs pack" value={formatNumber(activeSubvertical?.kpi_pack.length || 0)} hint="Métricas subverticales" icon="stats" tone="slate" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            <ModuleCard title="Promesa subvertical" description={safeText(activeSubvertical?.promise, "Sin promesa subvertical") } icon="wand" tone="green" footer={<div className="text-xs text-slate-400">Monetiza: {safeText(activeSubvertical?.monetizes.join(" • "), "Sin monetización")}</div>} />
            <ModuleCard title="Growth loops 10x" description={safeText(profile.ten_x_growth_loops.join(" • "), "Sin loops") } icon="refresh" tone="blue" footer={<div className="text-xs text-slate-400">Comandos: {safeText(activeSubvertical?.recommended_commands.join(" • "), safeText((profile.ten_x_operational_pack.recommended_commands as string[] || []).join(" • ")))}</div>} />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <ModuleCard title="Bundle de servicios" description={safeText(activeSubvertical?.service_bundle.join(" • "), "Sin bundle")} icon="stack" tone="green" />
            <ModuleCard title="Preguntas de calificación" description={safeText(activeSubvertical?.qualification_questions.join(" • "), "Sin preguntas")} icon="support" tone="gold" />
            <ModuleCard title="Objeciones" description={safeText(activeSubvertical?.objections.join(" • "), "Sin objeciones")} icon="alert" tone="slate" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <ModuleCard title="Automatizaciones prioritarias" description={safeText(activeSubvertical?.automation_priorities.join(" • "), "Sin automatizaciones")} icon="bot" tone="blue" />
            <ModuleCard title="KPIs del pack" description={safeText(activeSubvertical?.kpi_pack.join(" • "), "Sin KPIs")} icon="stats" tone="green" />
            <ModuleCard title="Assets de lanzamiento" description={safeText(activeSubvertical?.launch_assets.join(" • "), "Sin assets")} icon="check" tone="gold" />
          </div>
        </Section>
      ) : null}

      <Section title="One-pager comercial" subtitle="La versión vendible de la vertical: qué vende, qué promete y cómo se empaqueta." icon="rocket">
        <div className="grid gap-4 xl:grid-cols-2">
          <ModuleCard title={safeText(profile.one_pager.headline, profile.name)} description={safeText(profile.one_pager.thesis, "Sin tesis comercial.")} icon="wand" tone="green" footer={<div className="text-xs text-slate-400">Promesa: {safeText(profile.one_pager.promise, "Sin promesa")}</div>} />
          <ModuleCard title="Qué monetiza" description={safeText(profile.one_pager.monetizes.join(" • "), "Sin monetización definida.")} icon="money" tone="gold" footer={<div className="text-xs text-slate-400">Empaque: {safeText(profile.one_pager.packaging.join(" • "), "Sin empaque")}</div>} />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <ModuleCard title="Problema comercial" description={safeText(profile.one_pager.problem, "Sin problema") } icon="support" tone="blue" />
          <ModuleCard title="Cuidado estratégico" description={safeText(profile.one_pager.strategic_care, "Sin notas estratégicas") } icon="shield" tone="slate" />
        </div>
      </Section>

      <Section title="Demo flow" subtitle="Historia mínima que debe poder mostrarse como producto listo." icon="play">
        <DataTable columns={["Paso", "Qué valida WAOS"]} rows={profile.demo_flow.map((step, index) => [`${index + 1}`, step])} />
      </Section>

      <Section title="Esquema de objetos nativos" subtitle="No son solo chats y contactos: es el modelo operativo del negocio." icon="folder">
        <div className="grid gap-4 xl:grid-cols-3">
          <ModuleCard title="Core" description={safeText(profile.native_objects.core.join(" • "), "Sin objetos core")} icon="stack" tone="green" />
          <ModuleCard title="Comerciales" description={safeText(profile.native_objects.commercial.join(" • "), "Sin objetos comerciales")} icon="money" tone="blue" />
          <ModuleCard title="Operativos" description={safeText(profile.native_objects.operations.join(" • "), "Sin objetos operativos")} icon="tool" tone="gold" />
        </div>
      </Section>

      <Section title="Vertical duro / contrato de dominio" subtitle="La capa que convierte una vertical bonita en sistema especialista reusable." icon="shield">
        <div className="grid gap-4 xl:grid-cols-2">
          <ModuleCard title="Entidad reina" description={safeText(profile.hardening_model.entity_queen, "Sin entidad reina")} icon="target" tone="green" footer={<div className="text-xs text-slate-400">Meta: {safeText(profile.hardening_model.goal, "Sin meta")}</div>} />
          <ModuleCard title="Módulos reutilizables" description={safeText(profile.hardening_model.reusable_modules.join(" • "), "Sin módulos")} icon="layers" tone="blue" footer={<div className="text-xs text-slate-400">Mínimos: {safeText(profile.hardening_model.minimum_viable_hardening.join(" • "), "Sin mínimos")}</div>} />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <ModuleCard title="Entidades persistentes" description={safeText(profile.specialist_layers.persistent_entities.join(" • "), "Sin entidades persistentes")} icon="stack" tone="green" />
          <ModuleCard title="Pricing y quote types" description={safeText(profile.domain_contract.vertical_quote_types.join(" • "), "Sin quote types")} icon="money" tone="gold" footer={<div className="text-xs text-slate-400">Pricing: {safeText(profile.specialist_layers.pricing_and_quotes.join(" • "), "Sin pricing")}</div>} />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          <ModuleCard title="Agenda y recursos" description={safeText(profile.specialist_layers.agenda_and_resources.join(" • "), "Sin recursos")} icon="calendar" tone="blue" />
          <ModuleCard title="Postventa y recurrencia" description={safeText(profile.specialist_layers.post_sale_and_recurrence.join(" • "), "Sin recurrencia")} icon="refresh" tone="green" />
          <ModuleCard title="Documentos y compliance" description={safeText(profile.specialist_layers.documents_compliance.join(" • "), "Sin documentos")} icon="folder" tone="slate" />
        </div>
      </Section>

      <Section title="Pipeline y estados" subtitle="Los funnels no se comparten entre verticales: cada una necesita su propio lenguaje operacional." icon="flow">
        {pipelineRows.length ? <DataTable columns={["Pipeline", "Estados"]} rows={pipelineRows} /> : <ModuleCard title="Sin pipeline" description="Esta vertical todavía no define estados propios." icon="alert" tone="red" />}
      </Section>

      <Section title="Playbook del bot" subtitle="Qué debe hacer, preguntar, manejar y escalar el bot verticalizado." icon="bot">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <ModuleCard title="Debe hacer" description={safeText(profile.bot_playbook.must_do.join(" • "), "Sin acciones definidas")} icon="check" tone="green" />
          <ModuleCard title="Debe preguntar" description={safeText(profile.bot_playbook.must_ask.join(" • "), "Sin preguntas definidas")} icon="chat" tone="blue" />
          <ModuleCard title="Objeciones" description={safeText(profile.bot_playbook.objections.join(" • "), "Sin objeciones definidas")} icon="support" tone="gold" />
          <ModuleCard title="Escalar a humano" description={safeText(profile.bot_playbook.escalate_when.join(" • "), "Sin reglas de escalamiento")} icon="route" tone="red" />
          <ModuleCard title="Temas prohibidos" description={safeText(profile.bot_playbook.forbidden.join(" • "), "Sin límites definidos")} icon="shield" tone="slate" />
          <ModuleCard title="Señales de éxito" description={safeText(profile.bot_playbook.success_signals.join(" • "), "Sin señales definidas")} icon="spark" tone="green" />
        </div>
      </Section>

      <Section title="Secuencias automáticas" subtitle="Automatizaciones nativas que esta vertical debería traer de fábrica." icon="refresh">
        {automationRows.length ? <DataTable columns={["Secuencia", "Trigger", "Goal", "Pasos"]} rows={automationRows} /> : <ModuleCard title="Sin secuencias" description="No hay automatizaciones visibles para esta vertical." icon="alert" tone="red" />}
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <ModuleCard title="Automatizaciones que mueven dinero" description={safeText(profile.specialist_layers.money_automations.join(" • "), "Sin automatizaciones duras")} icon="money" tone="gold" />
          <ModuleCard title="Checklist de vertical duro" description={safeText(profile.hardening_model.hard_checklist.join(" • "), "Sin checklist")} icon="check" tone="green" />
        </div>
      </Section>

      <Section title="Dashboard / KPIs" subtitle="La vertical no se mide por mensajes respondidos, sino por movimiento real del negocio." icon="stats">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <Badge tone="green">North star</Badge>
          <span className="text-sm text-slate-300">{safeText(profile.dashboard.north_star, "Sin north star definido")}</span>
        </div>
        {dashboardRows.length ? <DataTable columns={["Sección", "Métricas"]} rows={dashboardRows} /> : <ModuleCard title="Sin métricas" description="No hay dashboard visible para esta vertical." icon="alert" tone="red" />}
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <ModuleCard title="KPIs que importan" description={safeText(profile.specialist_layers.kpis_that_matter.join(" • "), "Sin KPIs")} icon="stats" tone="blue" />
          <ModuleCard title="Playbooks por subvertical" description={safeText(profile.domain_contract.vertical_playbooks.join(" • "), "Sin playbooks")} icon="bot" tone="green" />
        </div>
      </Section>


      <Section title="Runtime ejecutable" subtitle="La vertical ya no solo define objetos: ahora expone lógica de ejecución para estados, pricing, capacidad, recurrencia, documentos, matching y automatizaciones." icon="tool">
        <div className="grid gap-4 xl:grid-cols-3">
          <ModuleCard title="Pipeline machine" description={safeText(((profile.vertical_runtime.pipeline_machine.states as string[]) || []).join(" • "), "Sin estados ejecutables")} icon="flow" tone="green" footer={<div className="text-xs text-slate-400">At risk: {safeText(profile.vertical_runtime.pipeline_machine.at_risk_state)}</div>} />
          <ModuleCard title="Pricing engine" description={safeText(((profile.vertical_runtime.pricing_engine.quote_types as string[]) || []).join(" • "), "Sin quote runtime")} icon="money" tone="gold" footer={<div className="text-xs text-slate-400">Base: {safeText(profile.vertical_runtime.pricing_engine.pricing_basis)}</div>} />
          <ModuleCard title="Resource capacity" description={safeText(((profile.vertical_runtime.resource_capacity.resource_types as string[]) || []).join(" • "), "Sin capacidad")} icon="calendar" tone="blue" footer={<div className="text-xs text-slate-400">Cola: {safeText(profile.vertical_runtime.resource_capacity.priority_queue)}</div>} />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          {runtimeTransitionRows.length ? <DataTable columns={["From", "To", "Trigger", "Efecto"]} rows={runtimeTransitionRows} /> : <ModuleCard title="Sin transiciones" description="No hay state machine visible para esta vertical." icon="alert" tone="red" />}
          {pricingRuleRows.length ? <DataTable columns={["#", "Regla", "Efecto"]} rows={pricingRuleRows} /> : <ModuleCard title="Sin pricing rules" description="No hay reglas de pricing visibles para esta vertical." icon="alert" tone="red" />}
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          {recurrenceRows.length ? <DataTable columns={["Política", "Días", "Ancla"]} rows={recurrenceRows} /> : <ModuleCard title="Sin recurrencia" description="No hay políticas de recurrencia visibles." icon="alert" tone="red" />}
          {kpiFormulaRows.length ? <DataTable columns={["KPI", "Fórmula"]} rows={kpiFormulaRows} /> : <ModuleCard title="Sin fórmulas" description="No hay fórmulas de KPI visibles." icon="alert" tone="red" />}
          {automationPolicyRows.length ? <DataTable columns={["Trigger", "Acciones", "Goal"]} rows={automationPolicyRows} /> : <ModuleCard title="Sin money automations" description="No hay políticas runtime de automatización visibles." icon="alert" tone="red" />}
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <ModuleCard title="Document flow" description={safeText(((profile.vertical_runtime.document_flow.required_documents as string[]) || []).join(" • "), "Sin documentos runtime")} icon="folder" tone="slate" />
          <ModuleCard title="Matching engine" description={safeText(((profile.vertical_runtime.matching_engine.rules as string[]) || []).join(" • "), "Sin matching runtime")} icon="spark" tone="green" />
        </div>
      </Section>

      <Section title="Motor v12 full transaccional" subtitle="Núcleo común que convierte el runtime vertical en sistema de registro, ejecución, cobro, cumplimiento y continuidad por vertical." icon="stack">
        <div className="grid gap-4 xl:grid-cols-4">
          <StatCard label="Versión" value={safeText(profile.transactional_motor_v12.version, "v12")} hint="Contrato transaccional" icon="rocket" tone="green" />
          <StatCard label="Aggregate root" value={safeText(profile.transactional_motor_v12.aggregate_root, "Sin root")} hint={safeText(profile.transactional_motor_v12.main_business_entity, "Sin entidad")} icon="stack" tone="blue" />
          <StatCard label="Unidad transaccional" value={safeText(profile.transactional_motor_v12.transaction_unit, "Sin unidad")} hint="Unidad mínima de operación" icon="tool" tone="gold" />
          <StatCard label="Comandos" value={formatNumber(profile.transactional_motor_v12.command_catalog.length)} hint="Catálogo ejecutable" icon="flow" tone="slate" />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          <ModuleCard title="Primitivas" description={safeText((((profile.transactional_motor_v12.transaction_primitives.commands as string[]) || []).slice(0, 8)).join(" • "), "Sin comandos")} icon="flow" tone="green" footer={<div className="text-xs text-slate-400">Eventos: {safeText((((profile.transactional_motor_v12.transaction_primitives.events as string[]) || []).slice(0, 6)).join(" • "), "Sin eventos")}</div>} />
          <ModuleCard title="Finanzas" description={safeText((((profile.transactional_motor_v12.finance.money_objects as string[]) || [])).join(" • "), "Sin objetos de dinero")} icon="money" tone="gold" footer={<div className="text-xs text-slate-400">Cobro: {safeText((((profile.transactional_motor_v12.finance.collection_modes as string[]) || [])).join(" • "), "Sin cobro")}</div>} />
          <ModuleCard title="Operación" description={safeText((((profile.transactional_motor_v12.operations.resource_locking as string[]) || [])).join(" • "), "Sin locking")} icon="calendar" tone="blue" footer={<div className="text-xs text-slate-400">Board: {safeText((((profile.transactional_motor_v12.operations.dispatch_or_schedule_board as string[]) || [])).join(" • "), "Sin board")}</div>} />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <ModuleCard title="Compliance y auditoría" description={safeText((((profile.transactional_motor_v12.audit_compliance.consent_gates as string[]) || [])).join(" • "), "Sin gates")} icon="shield" tone="slate" footer={<div className="text-xs text-slate-400">Evidencia: {safeText((((profile.transactional_motor_v12.audit_compliance.required_evidence as string[]) || [])).join(" • "), "Sin evidencia")}</div>} />
          <ModuleCard title="Orquestación" description={safeText((((profile.transactional_motor_v12.orchestration.sagas as string[]) || [])).join(" • "), "Sin sagas")} icon="wand" tone="green" footer={<div className="text-xs text-slate-400">Guards: {safeText((((profile.transactional_motor_v12.orchestration.money_guards as string[]) || [])).join(" • "), "Sin guards")}</div>} />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          {v12CommandRows.length ? <DataTable columns={["#", "Command", "Writes", "Guard"]} rows={v12CommandRows} /> : <ModuleCard title="Sin command catalog" description="No hay comandos visibles para esta vertical." icon="alert" tone="red" />}
          {v12EventRows.length ? <DataTable columns={["#", "Event", "Updates", "Next action"]} rows={v12EventRows} /> : <ModuleCard title="Sin event catalog" description="No hay eventos visibles para esta vertical." icon="alert" tone="red" />}
        </div>
        <div className="mt-4">
          {v12ViewRows.length ? <DataTable columns={["Vista", "Qué controla"]} rows={v12ViewRows} /> : <ModuleCard title="Sin transaction views" description="No hay vistas transaccionales visibles para esta vertical." icon="alert" tone="red" />}
        </div>
      </Section>

      <Section title="Subplaybooks y pruebas e2e" subtitle="La capa que prueba que cada vertical ya opera como negocio y no solo como preset." icon="wand">
        <div className="grid gap-4 xl:grid-cols-2">
          {playbookRows.length ? <DataTable columns={["Subvertical", "Foco"]} rows={playbookRows} /> : <ModuleCard title="Sin subplaybooks" description="No hay subplaybooks visibles para esta vertical." icon="alert" tone="red" />}
          {e2eRows.length ? <DataTable columns={["#", "Prueba e2e", "Estado"]} rows={e2eRows} /> : <ModuleCard title="Sin pruebas e2e" description="No hay pruebas e2e definidas para esta vertical." icon="alert" tone="red" />}
        </div>
      </Section>
    </Shell>
  );
}
