import Link from "next/link";
import { DataTable, Section, Shell, StatCard } from "../components";
import { formatMoney, formatNumber, safeText } from "../lib/ui";
import { getBusinessHubOverview, getCatalogProducts, getCatalogServices, getCommerceInsights, getCRMLeads, getPayments, getPromotionRules, getPromotions, getReactivationRecommendations } from "../lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

export default async function BusinessHubPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const tab = first(params.tab) || "resumen";
  const [hub, products, services, promotions, rules, insights, payments, leads, recommendations] = await Promise.all([
    getBusinessHubOverview(),
    getCatalogProducts(),
    getCatalogServices(),
    getPromotions(),
    getPromotionRules(),
    getCommerceInsights(),
    getPayments(),
    getCRMLeads(),
    getReactivationRecommendations(),
  ]);

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
          ["ingresos", "Ingresos"],
        ].map(([id, label]) => <Link key={id} href={`/business-hub?tab=${id}`} className={tab === id ? "primary-btn" : "secondary-btn"}>{label}</Link>)}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Productos" value={formatNumber(Number(summary.products || products.length || 0))} hint="Oferta visible" icon="catalog" tone="blue" />
        <StatCard label="Promociones" value={formatNumber(Number(summary.promotions || promotions.length || 0))} hint="Ofertas activas" icon="promo" tone="gold" />
        <StatCard label="Ingresos" value={formatMoney(paymentTotal, payments[0]?.currency || "MXN")} hint="Cobros visibles" icon="money" tone="green" />
        <StatCard label="Alertas" value={formatNumber((insights.alerts || []).length)} hint="Puntos a revisar" icon="alert" tone="slate" />
      </div>

      {tab === "resumen" ? (
        <Section title="Resumen comercial" subtitle="La foto corta de catálogo, promociones y resultados." icon="briefcase">
          <DataTable columns={["Tema", "Valor"]} rows={[
            ["Productos", formatNumber(products.length)],
            ["Servicios", formatNumber(services.length)],
            ["Promociones activas", formatNumber(promotions.length)],
            ["Leads visibles", formatNumber(leads.length)],
          ]} />
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
