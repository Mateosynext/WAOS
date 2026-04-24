import Link from "next/link";
import { EmptyActionState } from "@/app/components/feedback";
import { Section } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { formatNumber, safeText } from "@/app/lib/ui";
import { replayWebhookReceiptAction } from "@/features/integrations/actions";
import type { IntegrationsPageModel } from "@/features/integrations/server/getIntegrationsPageModel";

export function RiskSection({ model }: { model: IntegrationsPageModel }) {
  const { stats } = model;
  return (
    <Section title="Integraciones con riesgo" subtitle="Solo aparecen las conexiones que pueden frenar operación, reporting, agenda o cobros." icon="alert">
      {stats.risk.length ? <DataTable columns={["Integración", "Proveedor", "Salud", "Detalle"]} rows={stats.risk.map((item) => [safeText(item.name), safeText(item.provider), safeText(item.health_status || item.status), safeText(item.last_error || item.credential_status || item.status)])} /> : <EmptyActionState title="No hay integraciones con riesgo visible" description="Buen signo: por ahora la salud visible no muestra conexiones degradadas o cortadas." primaryAction={<Link href="/status" className="primary-btn">Ver estado</Link>} />}
      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <div>
          <div className="eyebrow mb-3">Hotspots de retry</div>
          {stats.retryHotspots.length ? <DataTable columns={["Integración", "Retries", "Salud", "Último error"]} rows={stats.retryHotspots.slice(0, 10).map((item) => [safeText(String(item.name || item.integration_id || "Integración")), formatNumber(Number(item.retry_count || 0)), safeText(String(item.health_status || "unknown")), safeText(String(item.last_error || "sin dato"))])} /> : <div className="surface-row text-sm text-slate-300">No hay integraciones reintentando activamente.</div>}
        </div>
        <div>
          <div className="eyebrow mb-3">Webhook replay seguro</div>
          {stats.failedReceipts.length ? <DataTable columns={["Receipt", "Canal", "Estado", "Acción"]} rows={stats.failedReceipts.slice(0, 10).map((item) => [safeText(String(item.external_event_id || item.id)), safeText(String(item.channel || "provider")), safeText(String(item.status || "unknown")), <form key={String(item.id)} action={replayWebhookReceiptAction}><input type="hidden" name="receipt_id" value={String(item.id || "")} /><input type="hidden" name="redirect_to" value="/integrations?section=riesgo" /><button className="secondary-btn" type="submit">Dry-run replay</button></form>])} /> : <div className="surface-row text-sm text-slate-300">No hay receipts fallidos pendientes de replay.</div>}
        </div>
      </div>
    </Section>
  );
}
