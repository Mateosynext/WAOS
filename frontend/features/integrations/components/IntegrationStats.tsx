import { StatCard } from "@/app/components/primitives/cards";
import { formatNumber } from "@/app/lib/ui";
import type { IntegrationsPageModel } from "@/features/integrations/server/getIntegrationsPageModel";

export function IntegrationStats({ model }: { model: IntegrationsPageModel }) {
  const { section, integrations, stats } = model;
  return (
    <div className="grid gap-4 md:grid-cols-5">
      <StatCard label="Integraciones" value={formatNumber(integrations.length)} hint="Conexiones registradas" icon="plug" tone="blue" />
      <StatCard label="Activas" value={formatNumber(stats.active)} hint="Listas para operar" icon="check" tone="green" />
      <StatCard label="Con alerta" value={formatNumber(stats.risk.length)} hint="Requieren revisión" icon={stats.risk.length ? "alert" : "check"} tone={stats.risk.length ? "gold" : "green"} />
      <StatCard label="Pagos pendientes" value={section === "sync" ? formatNumber(stats.pendingPayments.length) : "Abrir"} hint="Se carga al abrir Sincronizaciones" icon="money" tone={section === "sync" && stats.pendingPayments.length ? "gold" : "slate"} />
      <StatCard label="Eventos proveedor" value={section === "observabilidad" ? formatNumber(stats.observedEvents) : "Abrir"} hint="Se carga al abrir Observabilidad" icon="stats" tone="slate" />
      <StatCard label="Receipts fallidos" value={section === "riesgo" ? formatNumber(stats.failedReceipts.length) : "Abrir"} hint="Se carga al abrir Riesgo" icon="alert" tone={section === "riesgo" && stats.failedReceipts.length ? "red" : "slate"} />
    </div>
  );
}
