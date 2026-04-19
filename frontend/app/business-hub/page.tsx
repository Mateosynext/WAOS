import Link from "next/link";
import { DataTable, ModuleCard, Section, Shell, StatCard } from "../components";
import { getCurrentBotId, getSession } from "../lib/session";
import { formatMoney, formatNumber, safeText } from "../lib/ui";
import { getBusinessHubOverview, getCRMPipelineSummary, getCatalogProducts, getCatalogServices, getCommerceInsights, getCRMLeads, getPayments, getPromotionRules, getPromotions, getReactivationRecommendations, getVerticalProfile } from "../lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

export default async function BusinessHubPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const tab = first(params.tab) || "resumen";
  const session = await getSession();
  const currentBotId = await getCurrentBotId();
  const [hub, products, services, promotions, rules, insights, payments, leads, recommendations, pipeline] = await Promise.all([
    getBusinessHubOverview(),
    getCatalogProducts(),
    getCatalogServices(),
    getPromotions(),
    getPromotionRules(),
    getCommerceInsights(),
    getPayments(),
    getCRMLeads(),
    getReactivationRecommendations(),
    getCRMPipelineSummary(),
  ]);

  const currentOrg = session?.user.organizations.find((item) => item.id === session?.organizationId) || null;
  const verticalProfile = currentOrg?.vertical ? await getVerticalProfile(currentOrg.vertical, currentBotId || undefined, currentOrg.subvertical, session?.organizationId || undefined) : null;
  const summary = hub.summary || {};
  const insightSummary = insights.summary || {};
  const paymentTotal = payments.reduce((acc: number, item) => acc + Number(item.amount || 0), 0);

  return (
    <Shell title="Centro comercial" subtitle="Catálogo, promociones, insights e ingresos ya no viven en cuatro productos distintos. Todo comercial se navega desde aquí." action={<Link href="/client/promociones" className="secondary-btn">Ver portal cliente</Link>}>
      <div className="flex flex-wrap gap-2 rounded-3xl border border-white/[0.08] bg-white/[0.03] p-2">
        {[
          ["resumen", "Resumen"],
          ["catalogo", "Catálogo"],
          ["promociones", "Promociones"],
          ["insights", "Insights"],
          ["pipeline", "Pipeline"],
          ["ingresos", "Ingresos"],
        ].map(([id, label]) => <Link key={id} href={`/business-hub?tab=${id}`} className={tab === id ? "primary-btn" : "secondary-btn"}>{label}</Link>)}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Productos" value={formatNumber(Number(summary.products || products.length || 0))} hint="Oferta visible" icon="catalog" tone="blue" />
        <StatCard label="Promociones" value={formatNumber(Number(summary.promotions || promotions.length || 0))} hint="Ofertas activas" icon="promo" tone="gold" />
        <StatCard label="Ingresos" value={formatMoney(paymentTotal, payments[0]?.currency || "MXN")} hint="Cobros visibles" icon="money" tone="green" />
        <StatCard label="Alertas" value={formatNumber((insights.alerts || []).length)} hint="Puntos a revisar" icon="alert" tone="slate" />
        <StatCard label="Pipeline weighted" value={formatMoney(Number(pipeline.weighted_amount || 0), payments[0]?.currency || "MXN")} hint="Monto ponderado por probabilidad" icon="target" tone="blue" />
      </div>


      {verticalProfile?.id ? (
        <Section title="Comercial conectado a la vertical" subtitle="El pipeline, las ofertas y los follow-ups ahora se leen con la subvertical activa como contexto comercial real." icon="target">
          <div className="grid gap-4 xl:grid-cols-4">
            <StatCard label="Subvertical" value={safeText(verticalProfile.selected_subvertical?.name, currentOrg?.subvertical || 'sin definir')} hint={safeText(String(verticalProfile.runtime_connection?.surface_focus?.commercial || 'seguimiento'))} icon="wand" tone="green" />
            <StatCard label="Bundle de servicios" value={formatNumber((verticalProfile.selected_subvertical?.service_bundle || []).length)} hint="Servicios que deberían venderse" icon="catalog" tone="blue" />
            <StatCard label="Objeciones foco" value={formatNumber((verticalProfile.selected_subvertical?.objections || []).length)} hint="Objeciones operables" icon="support" tone="gold" />
            <StatCard label="Automations" value={formatNumber((verticalProfile.selected_subvertical?.automation_priorities || []).length)} hint="Secuencias prioritarias" icon="refresh" tone="slate" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <ModuleCard title="Promesa comercial" description={safeText(verticalProfile.selected_subvertical?.promise, verticalProfile.ten_x_narrative)} icon="rocket" tone="green" />
            <ModuleCard title="Buyer y motion" description={`${safeText(verticalProfile.selected_subvertical?.buyer, verticalProfile.buyer.primary)} · ${safeText(verticalProfile.selected_subvertical?.growth_motion, 'motion')}`} icon="client" tone="blue" />
            <ModuleCard title="Preguntas de calificación" description={safeText((verticalProfile.selected_subvertical?.qualification_questions || []).join(' • '), 'Sin preguntas')} icon="chat" tone="gold" />
          </div>
        </Section>
      ) : null}

      {tab === "resumen" ? (
        <Section title="Resumen comercial" subtitle="La foto corta de catálogo, promociones y resultados." icon="briefcase">
          <DataTable columns={["Tema", "Valor"]} rows={[
            ["Productos", formatNumber(products.length)],
            ["Servicios", formatNumber(services.length)],
            ["Promociones activas", formatNumber(promotions.length)],
            ["Leads visibles", formatNumber(leads.length)],
            ["Pipeline weighted", formatMoney(Number(pipeline.weighted_amount || 0), payments[0]?.currency || "MXN")],
          ]} />
          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {(pipeline.stages || []).slice(0, 4).map((item, index) => <div key={`${String(item.stage || index)}`} className="surface-row"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">{safeText(String(item.stage || "etapa"))}</div><div className="mt-1 text-lg font-semibold text-white">{formatNumber(Number(item.total || 0))}</div><div className="mt-2 text-xs text-slate-400">Monto {formatMoney(Number(item.amount || 0), payments[0]?.currency || "MXN")}</div></div>)}
          </div>
        </Section>
      ) : null}

      {tab === "catalogo" ? (
        <Section title="Catálogo" subtitle="Productos y servicios en una sola lectura." icon="catalog">
          <DataTable columns={["Nombre", "Tipo", "Precio", "Estado"]} rows={[
            ...products.slice(0, 20).map((item) => [safeText(item.name), "Producto", formatMoney(item.promotional_price || item.price, item.currency || "MXN"), safeText(item.inventory?.[0]?.status, "sin dato")]),
            ...services.slice(0, 20).map((item) => [safeText(item.name), "Servicio", formatMoney(item.price, item.currency || "MXN"), safeText(item.branch, "sin dato")]),
          ]} />
        </Section>
      ) : null}

      {tab === "promociones" ? (
        <Section title="Promociones" subtitle="Ofertas y reglas comerciales sin brincar de pantalla." icon="promo">
          <DataTable columns={["Promoción", "Vigencia", "CTA", "Regla"]} rows={promotions.map((item, index) => [safeText(item.name), `${safeText(item.starts_at)} → ${safeText(item.ends_at)}`, safeText(item.cta_label), safeText(rules[index]?.name || rules[index]?.condition || "sin regla")])} />
        </Section>
      ) : null}

      {tab === "insights" ? (
        <Section title="Insights comerciales" subtitle="Qué vende, qué frena y qué conviene tocar primero." icon="stats">
          <DataTable columns={["Tema", "Valor"]} rows={[
            ["Ingresos", formatMoney(Number(insightSummary.revenue || 0), safeText(insightSummary.currency, "MXN"))],
            ["Conversión", safeText(insightSummary.conversion_rate ? `${insightSummary.conversion_rate}%` : null, "-")],
            ["Pedidos", formatNumber(Number(insightSummary.orders || 0))],
            ["Alertas", formatNumber((insights.alerts || []).length)],
          ]} />
        </Section>
      ) : null}


      {tab === "pipeline" ? (
        <Section title="Pipeline y motivos de pérdida" subtitle="Resumen comercial accionable por etapa, monto y pérdida estructurada." icon="target">
          <DataTable columns={["Etapa", "Leads", "Monto", "Prob. cierre"]} rows={(pipeline.stages || []).map((item) => [safeText(String(item.stage || "etapa")), formatNumber(Number(item.total || 0)), formatMoney(Number(item.amount || 0), payments[0]?.currency || "MXN"), `${formatNumber(Number(item.avg_close_probability || 0))}%`])} />
          <div className="mt-5 grid gap-4 xl:grid-cols-2">
            <div>
              <div className="eyebrow mb-3">Motivos de pérdida</div>
              <DataTable columns={["Motivo", "Total"]} rows={(pipeline.lost_reasons || []).map((item) => [safeText(String(item.lost_reason || "sin_motivo")), formatNumber(Number(item.total || 0))])} />
            </div>
            <div>
              <div className="eyebrow mb-3">Cambios recientes de etapa</div>
              <DataTable columns={["Lead", "De", "A", "Fecha"]} rows={(pipeline.recent_stage_changes || []).slice(0, 10).map((item) => [safeText(String(item.crm_lead_id || item.id || "lead")), safeText(String(item.previous_stage || "-")), safeText(String(item.new_stage || "-")), safeText(String(item.created_at || "-"))])} />
            </div>
          </div>
        </Section>
      ) : null}

      {tab === "ingresos" ? (
        <Section title="Ingresos y reactivación" subtitle="Pagos, leads y recomendaciones de reactivación en una sola capa." icon="money">
          <DataTable columns={["Tema", "Detalle"]} rows={[
            ...payments.slice(0, 10).map((item) => [safeText(item.id || item.reference), `${formatMoney(item.amount, item.currency || "MXN")} · ${safeText(item.status)}`]),
            ...recommendations.slice(0, 10).map((item) => [safeText(item.contact_name || item.id), safeText(item.next_step || item.reason)]),
          ]} />
        </Section>
      ) : null}
    </Shell>
  );
}
