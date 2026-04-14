import { ModuleCard, Section, Shell, StatCard } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getBusinessHubOverview } from "../lib/waos";

export default async function BusinessHubPage() {
  const data = await getBusinessHubOverview();
  const summary = data.summary || {};
  return (
    <Shell title="Centro de negocio" subtitle="Una vista ordenada de lo comercial: productos, promociones, puntos de atención y prioridades del día.">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Productos" value={formatNumber(Number(summary.products || 0))} hint="Items cargados" icon="catalog" tone="blue" />
        <StatCard label="Servicios" value={formatNumber(Number(summary.services || 0))} hint="Servicios disponibles" icon="briefcase" tone="green" />
        <StatCard label="Promociones" value={formatNumber(Number(summary.promotions || 0))} hint="Promociones activas" icon="promo" tone="gold" />
        <StatCard label="Pendientes" value={formatNumber((data.attention || []).length)} hint="Puntos a revisar" icon="alert" tone="slate" />
      </div>
      <Section title="Qué necesita atención" subtitle="Estas tarjetas ayudan a encontrar rápido lo que falta actualizar o corregir." icon="briefcase">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(data.attention || []).map((item, index: number) => (
            <ModuleCard key={index} title={safeText(item.title, `Pendiente ${index + 1}`)} description={safeText(item.detail, "Requiere revisión operativa.")} icon="alert" tone="gold" />
          ))}
        </div>
      </Section>
    </Shell>
  );
}
