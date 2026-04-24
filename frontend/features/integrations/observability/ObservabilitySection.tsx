import Link from "next/link";
import { EmptyActionState } from "@/app/components/feedback";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { Badge } from "@/app/components/primitives/shared";
import { formatNumber, safeText } from "@/app/lib/ui";
import type { IntegrationsPageModel } from "@/features/integrations/server/getIntegrationsPageModel";

export function ObservabilitySection({ model }: { model: IntegrationsPageModel }) {
  const { center, observability, events } = model;
  return (
    <Section title="Observabilidad por integración" subtitle="Aquí ya se ve el provider de verdad: eventos recientes, errores y último código HTTP reportado por proveedor." icon="stats">
      <div className="mb-4 grid gap-3 md:grid-cols-3">
        {(center.dependency_map || []).map((item, index) => <div key={`${String(item.integration_type || index)}`} className="surface-row text-sm text-slate-300"><div className="font-medium text-white">{safeText(String(item.integration_type || "integración"))}</div><div className="mt-2">Impacta: {safeText((Array.isArray(item.modules) ? item.modules.join(", ") : "sin dato") as string)}</div></div>)}
      </div>
      <div className="grid gap-4 md:grid-cols-3 mb-4">
        <StatCard label="OK" value={formatNumber(Number(observability.totals?.ok || 0))} hint="Eventos saludables" icon="check" tone="green" />
        <StatCard label="Warnings" value={formatNumber(Number(observability.totals?.warning || 0))} hint="Estados degradados o expirados" icon="alert" tone="gold" />
        <StatCard label="Fallos" value={formatNumber(Number(observability.totals?.failed || 0))} hint="Eventos con error visible" icon="alert" tone="red" />
      </div>
      {events.length ? <DataTable columns={["Proveedor", "Evento", "Estado", "Detalle"]} rows={events.slice(0, 20).map((item) => [safeText(item.provider), safeText(item.event_type), <Badge key={`${item.id}-evt`} tone={String(item.status || "").toLowerCase() === "ok" || String(item.status || "").toLowerCase() === "paid" ? "green" : String(item.status || "").toLowerCase() === "warning" ? "amber" : "red"}>{safeText(item.status)}</Badge>, safeText(item.detail || item.summary)])} /> : <EmptyActionState title="Todavía no hay eventos de proveedor" description="Cuando empiecen pruebas reales, OAuth, syncs o webhooks, aquí quedará la traza operativa sin ir a logs crudos." primaryAction={<Link href="/integrations?section=estado" className="primary-btn">Probar</Link>} />}
    </Section>
  );
}
