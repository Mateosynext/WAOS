import Link from "next/link";
import { EmptyActionState } from "@/app/components/feedback";
import { Section } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { Badge } from "@/app/components/primitives/shared";
import { safeText } from "@/app/lib/ui";
import { refreshPaymentStatusAction } from "@/features/integrations/actions";
import type { IntegrationsPageModel } from "@/features/integrations/server/getIntegrationsPageModel";

export function SyncSection({ model }: { model: IntegrationsPageModel }) {
  const { syncRuns, stats } = model;
  return (
    <Section title="Últimas sincronizaciones" subtitle="Aquí ves si la integración corre, falla o se queda a medias sin entrar a logs densos." icon="refresh">
      {syncRuns.length ? <DataTable columns={["Run", "Integración", "Estado", "Resumen"]} rows={syncRuns.map((item) => [safeText(item.id), safeText(item.integration_id || item.provider), <Badge key={`${item.id}-sync`} tone={String(item.status).toLowerCase() === "completed" ? "green" : String(item.status).toLowerCase() === "running" ? "sky" : "red"}>{safeText(item.status)}</Badge>, safeText(item.detail || JSON.stringify(item.summary || {}))])} /> : <EmptyActionState title="Todavía no hay sincronizaciones visibles" description="Cuando ejecutes pruebas o sincronizaciones manuales, el historial aparecerá aquí para soporte y operación." primaryAction={<Link href="/integrations?section=estado" className="primary-btn">Probar</Link>} />}
      {stats.pendingPayments.length ? (
        <div className="mt-5">
          <div className="eyebrow mb-3">Pagos que conviene refrescar</div>
          <DataTable columns={["Pago", "Estado", "Proveedor", "Acción"]} rows={stats.pendingPayments.slice(0, 10).map((item) => [safeText(item.reference || item.id), safeText(item.status), safeText(item.provider_status || item.provider || item.checkout_status), <form key={item.id} action={refreshPaymentStatusAction}><input type="hidden" name="payment_id" value={item.id} /><input type="hidden" name="redirect_to" value="/integrations?section=sync" /><button className="secondary-btn" type="submit">Refrescar</button></form>])} />
        </div>
      ) : null}
    </Section>
  );
}
