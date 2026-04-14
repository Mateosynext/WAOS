import { DataTable, Section, Shell, StatCard } from "../components";
import { formatMoney, formatNumber, safeText } from "../lib/ui";
import { getCommerceInsights } from "../lib/waos";

export default async function CommerceInsightsPage() {
  const data = await getCommerceInsights();
  const summary = data.summary || {};
  return (
    <Shell title="Resultados comerciales" subtitle="Una vista simple de qué está vendiendo, qué está frenando y dónde conviene intervenir primero.">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Ingresos" value={formatMoney(Number(summary.revenue || 0), safeText(summary.currency, "MXN"))} hint="Valor generado" icon="money" tone="green" />
        <StatCard label="Conversión" value={safeText(summary.conversion_rate ? `${summary.conversion_rate}%` : null, '-')} hint="De oportunidad a cierre" icon="stats" tone="blue" />
        <StatCard label="Tickets" value={formatNumber(Number(summary.orders || 0))} hint="Pedidos detectados" icon="catalog" tone="gold" />
        <StatCard label="Alertas" value={formatNumber((data.alerts || []).length)} hint="Puntos a revisar" icon="alert" tone="slate" />
      </div>
      <Section title="Alertas comerciales" subtitle="Te ayuda a encontrar rápido qué ajustar en oferta, seguimiento o catálogo." icon="alert">
        <DataTable columns={["Tema", "Detalle"]} rows={(data.alerts || []).map((item) => [safeText(item.title), safeText(item.detail)])} />
      </Section>
    </Shell>
  );
}
