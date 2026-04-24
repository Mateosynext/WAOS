import { Shell } from "@/app/components/layout/shell";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { createAgendaCapacityRuleAction, createAgendaResourceAction } from "@/app/actions/scheduling";
import { formatNumber, safeText } from "../lib/ui";
import { getAgendaCapacityOverview, getAgendaCapacityRules, getAgendaOverview, getAgendaResources, getAppointments } from "@/app/lib/data/inbox";
import { getVerticalProfile } from "@/app/lib/data/verticals";
import { getCurrentBotId, getSession } from "../lib/session";

export default async function AgendaPage() {
  const session = await getSession();
  const currentBotId = await getCurrentBotId();
  const [overview, appointments, capacityOverview, resources, capacityRules] = await Promise.all([getAgendaOverview(), getAppointments(), getAgendaCapacityOverview(), getAgendaResources(), getAgendaCapacityRules()]);
  const currentOrg = session?.user.organizations.find((item) => item.id === session?.organizationId) || null;
  const verticalProfile = currentOrg?.vertical ? await getVerticalProfile(currentOrg.vertical, currentBotId || undefined, currentOrg.subvertical, session?.organizationId || undefined) : null;
  const summary = overview.summary || {};
  const capacitySummary = (capacityOverview.summary || {}) as Record<string, unknown>;
  return (
    <Shell title="Agenda" subtitle="Una agenda clara para revisar citas, próximos movimientos y disponibilidad del día.">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Citas" value={formatNumber(appointments.length)} hint="Total registradas" icon="calendar" tone="blue" />
        <StatCard label="Pendientes" value={formatNumber(Number(summary.pending || 0))} hint="Todavía por confirmar" icon="clock" tone="gold" />
        <StatCard label="Confirmadas" value={formatNumber(Number(summary.confirmed || 0))} hint="Listas para atender" icon="check" tone="green" />
        <StatCard label="Próximas" value={formatNumber((overview.upcoming || []).length)} hint="Vienen en camino" icon="route" tone="slate" />
      </div>

      {verticalProfile?.id ? (
        <Section title="Agenda conectada a la vertical" subtitle="La agenda ya entiende qué servicio y qué operación importan según la subvertical activa, no solo slots genéricos." icon="spark">
          <div className="grid gap-4 xl:grid-cols-4">
            <StatCard label="Subvertical" value={safeText(verticalProfile.selected_subvertical?.name, currentOrg?.subvertical || 'sin definir')} hint={safeText(String(verticalProfile.runtime_connection?.surface_focus?.agenda || 'agenda vertical'))} icon="wand" tone="green" />
            <StatCard label="Servicios semilla" value={formatNumber((verticalProfile.selected_subvertical?.service_bundle || []).length)} hint="Oferta que debería verse en agenda" icon="catalog" tone="blue" />
            <StatCard label="Comando sugerido" value={safeText((verticalProfile.selected_subvertical?.recommended_commands || [])[0], 'sin comando')} hint="Control operativo sugerido" icon="tool" tone="gold" />
            <StatCard label="Pack vertical" value={`${formatNumber(Number((verticalProfile.runtime_connection?.pack_status || {}).coverage_score || 0))}%`} hint="Cobertura del pack aplicado" icon="target" tone="slate" />
          </div>
        </Section>
      ) : null}

      <Section title="Capacidad por recurso" subtitle="Esta capa ya separa recursos, reglas de capacidad y citas futuras sin obligarte a modelar todo de una vez." icon="layers">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Recursos" value={formatNumber(Number(capacitySummary.resources || 0))} hint="Profesionales, salas o equipos" icon="support" tone="blue" />
          <StatCard label="Reglas" value={formatNumber(Number(capacitySummary.capacity_rules || 0))} hint="Ventanas activas declaradas" icon="clock" tone="gold" />
          <StatCard label="Slots/semana" value={formatNumber(Number(capacitySummary.declared_weekly_slots || 0))} hint="Capacidad declarada" icon="target" tone="green" />
          <StatCard label="Sin recurso" value={formatNumber(Number(capacitySummary.unassigned_upcoming_appointments || 0))} hint="Citas por asignar" icon="alert" tone={Number(capacitySummary.unassigned_upcoming_appointments || 0) ? "red" : "slate"} />
        </div>
        <div className="mt-4 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <form action={createAgendaResourceAction} className="grid gap-3 rounded-3xl border border-white/[0.08] bg-white/[0.03] p-4">
            <input type="hidden" name="organization_id" value={session?.organizationId || ""} />
            <input type="hidden" name="bot_id" value={currentBotId || ""} />
            <input type="hidden" name="redirect_to" value="/agenda" />
            <label className="field-label">Nuevo recurso
              <input className="field-input" name="name" placeholder="Ej. Dra. Sofía / Sala 2" required />
            </label>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="field-label">Tipo
                <select className="field-input" name="resource_type" defaultValue="professional">
                  <option value="professional">Profesional</option>
                  <option value="room">Sala</option>
                  <option value="seat">Sillón</option>
                  <option value="machine">Equipo</option>
                  <option value="branch">Sede</option>
                </select>
              </label>
              <label className="field-label">Sede
                <input className="field-input" name="branch" placeholder="Ej. Polanco" />
              </label>
            </div>
            <button className="secondary-btn" type="submit">Crear recurso</button>
          </form>
          <form action={createAgendaCapacityRuleAction} className="grid gap-3 rounded-3xl border border-white/[0.08] bg-white/[0.03] p-4">
            <input type="hidden" name="organization_id" value={session?.organizationId || ""} />
            <input type="hidden" name="bot_id" value={currentBotId || ""} />
            <input type="hidden" name="redirect_to" value="/agenda" />
            <label className="field-label">Recurso
              <select className="field-input" name="resource_id" defaultValue={String(resources[0]?.id || '')}>
                {resources.map((item) => <option key={String(item.id)} value={String(item.id)}>{safeText(String(item.name || 'recurso'))}</option>)}
              </select>
            </label>
            <div className="grid gap-3 md:grid-cols-4">
              <label className="field-label">Día
                <select className="field-input" name="day_of_week" defaultValue="1">
                  <option value="0">Dom</option><option value="1">Lun</option><option value="2">Mar</option><option value="3">Mié</option><option value="4">Jue</option><option value="5">Vie</option><option value="6">Sáb</option>
                </select>
              </label>
              <label className="field-label">Inicio
                <input className="field-input" name="start_time" defaultValue="09:00" />
              </label>
              <label className="field-label">Fin
                <input className="field-input" name="end_time" defaultValue="18:00" />
              </label>
              <label className="field-label">Capacidad
                <input className="field-input" name="slot_capacity" defaultValue="1" />
              </label>
            </div>
            <button className="primary-btn" type="submit">Guardar regla</button>
          </form>
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <DataTable columns={["Recurso", "Tipo", "Slots/semana", "Citas asignadas"]} rows={resources.length ? resources.map((item) => {
            const overviewResource = Array.isArray(capacityOverview.resources) ? (capacityOverview.resources as Array<Record<string, unknown>>).find((row) => String(row.resource_id || '') === String(item.id || '')) : null;
            return [safeText(String(item.name || 'recurso')), safeText(String(item.resource_type || '-')), safeText(String((overviewResource || {}).weekly_slots || 0)), safeText(String((overviewResource || {}).assigned_appointments || 0))];
          }) : [["Sin recursos", "-", "0", "0"]]} />
          <DataTable columns={["Recurso", "Día", "Ventana", "Capacidad"]} rows={capacityRules.length ? capacityRules.map((item) => [safeText(String(item.resource_name || item.resource_id || 'recurso')), safeText(String(item.day_of_week || '-')), `${safeText(String(item.start_time || '-'))} - ${safeText(String(item.end_time || '-'))}`, safeText(String(item.slot_capacity || 0))]) : [["Sin reglas", "-", "-", "0"]]} />
        </div>
      </Section>

      <Section title="Citas registradas" subtitle="Consulta nombre, fecha, estado y conciliación de cobro sin navegar por pantallas técnicas." icon="calendar">
        <DataTable columns={["Cliente", "Servicio", "Fecha", "Estado", "Pago"]} rows={appointments.map((item) => [safeText(item.contact_name), safeText(item.service_name), safeText(item.starts_at), safeText(item.status), safeText(item.payment_status || item.reconciliation_status || "sin conciliar")])} />
      </Section>
    </Shell>
  );
}
