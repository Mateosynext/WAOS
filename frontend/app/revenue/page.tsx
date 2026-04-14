import { refreshPaymentStatusAction } from "../actions";
import { DataTable, Section, Shell, StatCard } from "../components";
import { formatMoney, formatNumber, safeText } from "../lib/ui";
import { getCRMLeads, getPayments, getReactivationRecommendations } from "../lib/waos";

export default async function RevenuePage() {
  const [payments, leads, recommendations] = await Promise.all([getPayments(), getCRMLeads(), getReactivationRecommendations()]);
  const total = payments.reduce((acc: number, item) => acc + Number(item.amount || 0), 0);
  const pendingPayments = payments.filter((item) => ["pending", "pending_provider", "requires_action"].includes(String(item.status || "").toLowerCase()) || ["open", "unpaid", "requires_payment_method"].includes(String(item.provider_status || "").toLowerCase()));
  return (
    <Shell title="Ventas" subtitle="Una vista clara de cobros, clientes y oportunidades de reactivación para seguir vendiendo sin perder contexto.">
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Cobros" value={formatMoney(total, payments[0]?.currency || 'MXN')} hint="Suma visible de pagos" icon="money" tone="green" />
        <StatCard label="Clientes" value={formatNumber(leads.length)} hint="Oportunidades en CRM" icon="briefcase" tone="blue" />
        <StatCard label="Reactivación" value={formatNumber(recommendations.length)} hint="Casos para volver a tocar" icon="refresh" tone="gold" />
        <StatCard label="Pendientes" value={formatNumber(pendingPayments.length)} hint="Cobros por reconciliar" icon="alert" tone="red" />
      </div>
      <Section title="Pagos" subtitle="Resumen de pagos registrados por el sistema con capacidad de refrescar estado provider." icon="money">
        <DataTable
          columns={["Referencia", "Monto", "Estado", "Proveedor", "Reconciliación", "Acción"]}
          rows={payments.map((item) => [
            safeText(item.id || item.reference),
            formatMoney(item.amount, item.currency || 'MXN'),
            safeText(item.status),
            safeText(item.provider_status || item.provider || item.checkout_status),
            safeText(item.reconciliation_status || item.appointment_id || "pendiente"),
            <form action={refreshPaymentStatusAction} key={`refresh-${item.id}`}>
              <input type="hidden" name="payment_id" value={String(item.id || "")} />
              <input type="hidden" name="redirect_to" value="/revenue" />
              <button className="secondary-btn" type="submit">Refrescar</button>
            </form>,
          ])}
        />
      </Section>
      <Section title="Clientes para reactivar" subtitle="Contactos que vale la pena retomar con una oferta o seguimiento." icon="refresh">
        <DataTable columns={["Cliente", "Motivo", "Siguiente paso"]} rows={recommendations.map((item) => [safeText(item.contact_name || item.id), safeText(item.reason), safeText(item.next_step)])} />
      </Section>
    </Shell>
  );
}
