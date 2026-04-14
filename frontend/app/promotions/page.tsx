import { DataTable, Section, Shell, StatCard } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getPromotionRules, getPromotions } from "../lib/waos";

export default async function PromotionsPage() {
  const [promotions, rules] = await Promise.all([getPromotions(), getPromotionRules()]);
  return (
    <Shell title="Promociones" subtitle="Un lugar claro para revisar ofertas, vigencias y reglas sin perderte entre pantallas técnicas.">
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Promociones" value={formatNumber(promotions.length)} hint="Ofertas registradas" icon="promo" tone="gold" />
        <StatCard label="Reglas" value={formatNumber(rules.length)} hint="Condiciones activas" icon="gear" tone="blue" />
        <StatCard label="Con CTA" value={formatNumber(promotions.filter((item) => item.cta_label).length)} hint="Listas para cierre" icon="target" tone="green" />
      </div>
      <Section title="Promociones activas" subtitle="Lo que el equipo comercial puede mover hoy mismo." icon="promo">
        <DataTable columns={["Promoción", "Vigencia", "CTA", "Mensaje"]} rows={promotions.map((item) => [safeText(item.name), `${safeText(item.starts_at)} → ${safeText(item.ends_at)}`, safeText(item.cta_label), safeText(item.message_short)])} />
      </Section>
      <Section title="Reglas" subtitle="Condiciones que ayudan a decidir cuándo mostrar una promoción." icon="gear">
        <DataTable columns={["Regla", "Condición", "Resultado"]} rows={rules.map((item) => [safeText(item.name), safeText(item.condition), safeText(item.result)])} />
      </Section>
    </Shell>
  );
}
