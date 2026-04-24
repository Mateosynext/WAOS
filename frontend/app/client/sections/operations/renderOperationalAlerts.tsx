import { Badge } from "@/app/components/primitives/shared";
import { ClientEmptyBlock, ClientSectionBlock } from "../../../components/client/ClientPortalPrimitives";
import { safeText } from "../../../lib/ui";
import type { ClientOperationsPayload } from "./types";

export function renderOperationalAlerts({ alerts }: { alerts: ClientOperationsPayload["alerts"] }) {
  return (
    <ClientSectionBlock title="Alertas operativas" subtitle="Abuso, rate limits y ejecuciones parciales que requieren seguimiento.">
      <div className="space-y-3">
        {alerts.length ? alerts.slice(0, 6).map((item) => (
          <div key={String(item.id)} className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={String(item.severity || "warning") === "critical" ? "gold" : "slate"}>{safeText(String(item.alert_type || "alerta"), "alerta")}</Badge>
              <Badge tone="sky">{safeText(String(item.status || "open"), "open")}</Badge>
            </div>
            <div className="mt-3 font-medium text-[color:var(--text-primary)]">{safeText(String(item.title || "Alerta operativa"), "Alerta operativa")}</div>
            <div className="mt-2 text-sm text-[color:var(--text-secondary)]">{safeText(String(item.body || ""), "")}</div>
          </div>
        )) : <ClientEmptyBlock title="Sin alertas abiertas" description="Cuando haya abuso, rate limits o fallos parciales, aparecerán aquí." />}
      </div>
    </ClientSectionBlock>
  );
}
