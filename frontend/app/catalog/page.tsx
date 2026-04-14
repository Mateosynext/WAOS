import { DataTable, Section, Shell, StatCard } from "../components";
import { formatMoney, formatNumber, safeText } from "../lib/ui";
import { getCatalogProducts, getCatalogServices } from "../lib/waos";

export default async function CatalogPage() {
  const [products, services] = await Promise.all([getCatalogProducts(), getCatalogServices()]);
  return (
    <Shell title="Catálogo" subtitle="Todo el contenido comercial en un solo lugar para que sea fácil cargar, revisar y mantener.">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Productos" value={formatNumber(products.length)} hint="Items físicos o digitales" icon="catalog" tone="green" />
        <StatCard label="Servicios" value={formatNumber(services.length)} hint="Servicios agendables o consultivos" icon="briefcase" tone="blue" />
        <StatCard label="Con precio" value={formatNumber(products.filter((item) => item.price).length)} hint="Listos para vender" icon="money" tone="gold" />
        <StatCard label="Sin revisar" value={formatNumber(products.filter((item) => !item.short_description).length)} hint="Les falta descripción" icon="alert" tone="slate" />
      </div>
      <Section title="Productos" subtitle="Revisión rápida de nombre, precio y disponibilidad." icon="catalog">
        <DataTable columns={["Producto", "Precio", "Stock", "Entrega"]} rows={products.map((item) => [safeText(item.name), formatMoney(item.promotional_price || item.price, item.currency || 'MXN'), safeText(item.inventory?.[0]?.status, 'sin dato'), safeText(item.delivery_eta, 'sin dato')])} />
      </Section>
      <Section title="Servicios" subtitle="Qué servicios tiene el bot y cómo se presentan al cliente." icon="briefcase">
        <DataTable columns={["Servicio", "Precio", "Duración", "Sucursal"]} rows={services.map((item) => [safeText(item.name), formatMoney(item.price, item.currency || 'MXN'), safeText(item.duration_minutes ? `${item.duration_minutes} min` : null, 'sin dato'), safeText(item.branch, 'sin dato')])} />
      </Section>
    </Shell>
  );
}
