import { DataTable, Section, Shell, StatCard } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getAgendaOverview, getAppointments } from "../lib/waos";

export default async function AgendaPage() {
  const [overview, appointments] = await Promise.all([getAgendaOverview(), getAppointments()]);
  const summary = overview.summary || {};
  return (
    <Shell title="Agenda" subtitle="Una agenda clara para revisar citas, próximos movimientos y disponibilidad del día.">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Citas" value={formatNumber(appointments.length)} hint="Total registradas" icon="calendar" tone="blue" />
        <StatCard label="Pendientes" value={formatNumber(Number(summary.pending || 0))} hint="Todavía por confirmar" icon="clock" tone="gold" />
        <StatCard label="Confirmadas" value={formatNumber(Number(summary.confirmed || 0))} hint="Listas para atender" icon="check" tone="green" />
        <StatCard label="Próximas" value={formatNumber((overview.upcoming || []).length)} hint="Vienen en camino" icon="route" tone="slate" />
      </div>
      <Section title="Citas registradas" subtitle="Consulta nombre, fecha, estado y conciliación de cobro sin navegar por pantallas técnicas." icon="calendar">
        <DataTable columns={["Cliente", "Servicio", "Fecha", "Estado", "Pago"]} rows={appointments.map((item) => [safeText(item.contact_name), safeText(item.service_name), safeText(item.starts_at), safeText(item.status), safeText(item.payment_status || item.reconciliation_status || "sin conciliar")])} />
      </Section>
    </Shell>
  );
}
