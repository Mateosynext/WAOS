import Link from "next/link";
import { safeText } from "@/app/lib/ui";
import { saveInboxViewAction } from "@/features/inbox/actions";
import { buildInboxQuery, type InboxPageModel } from "@/features/inbox/server/getInboxPageModel";

export function InboxFilters({ model }: { model: InboxPageModel }) {
  const { savedViews, filters, selected, activeOrganizationId, hasOrganizationContext } = model;
  const { filter, sort, q, relation, mode, urgency } = filters;

  return (
    <>
      {savedViews.length ? (
        <div className="mb-4 flex flex-wrap gap-2">
          {savedViews.map((view) => {
            const savedFilters = view.filters || {};
            const query = buildInboxQuery({
              filter: String(savedFilters.filter || "all"),
              sort: String(savedFilters.sort || "priority"),
              q: String(savedFilters.q || ""),
              relation: String(savedFilters.relation || "all"),
              mode: String(savedFilters.mode || "all"),
              urgency: String(savedFilters.urgency || "all"),
            });
            return <Link key={view.id} href={`/inbox${query}`} className="secondary-btn">{safeText(view.name)}{view.is_default ? " · default" : ""}</Link>;
          })}
        </div>
      ) : null}

      <form action={saveInboxViewAction} className="mb-4 flex flex-wrap gap-3 rounded-3xl border border-white/[0.08] bg-white/[0.03] p-4">
        <input type="hidden" name="organization_id" value={activeOrganizationId} />
        <input type="hidden" name="filters" value={JSON.stringify({ filter, sort, q, relation, mode, urgency })} />
        <input type="hidden" name="redirect_to" value={`/inbox${buildInboxQuery({ filter, sort, q, relation, mode, urgency, selected: selected?.id || undefined })}`} />
        <label className="field-label min-w-[220px]">Guardar vista
          <input className="field-input" type="text" name="name" placeholder="Ej. cierres hoy" />
        </label>
        <label className="field-label">Default
          <select className="field-input" name="is_default" defaultValue="0"><option value="0">No</option><option value="1">Sí</option></select>
        </label>
        <div className="flex items-end"><button className="secondary-btn disabled:cursor-not-allowed disabled:opacity-50" type="submit" disabled={!hasOrganizationContext}>Guardar filtros</button></div>
      </form>

      <form className="mb-4 grid gap-3 rounded-3xl border border-white/[0.08] bg-white/[0.03] p-4 xl:sticky xl:top-4 xl:z-10 xl:grid-cols-[minmax(0,1.4fr)_repeat(4,180px)_auto]">
        <label className="field-label">Buscar<input className="field-input" type="search" name="q" defaultValue={q} placeholder="Nombre, teléfono, asistente operativo, resumen…" /></label>
        <label className="field-label">Foco<select className="field-input" name="filter" defaultValue={filter}><option value="all">Todo</option><option value="human">Humano</option><option value="pending">Pendiente</option><option value="hot">Caliente</option><option value="owner">Dueño</option></select></label>
        <label className="field-label">Relación<select className="field-input" name="relation" defaultValue={relation}><option value="all">Todas</option><option value="client">Cliente</option><option value="known">Conocido</option><option value="family">Familia</option><option value="provider">Proveedor</option></select></label>
        <label className="field-label">Modo<select className="field-input" name="mode" defaultValue={mode}><option value="all">Todos</option><option value="sales">Ventas</option><option value="support">Soporte</option><option value="operations">Operación</option><option value="personal_assistant">Asistente</option><option value="universal">Universal</option></select></label>
        <label className="field-label">Urgencia<select className="field-input" name="urgency" defaultValue={urgency}><option value="all">Todas</option><option value="critical">Crítica</option><option value="high">Alta</option><option value="medium">Media</option><option value="normal">Normal</option></select></label>
        <label className="field-label">Orden<select className="field-input" name="sort" defaultValue={sort}><option value="priority">Prioridad WAOS</option><option value="recent">Actividad reciente</option><option value="urgency">Urgencia</option><option value="lead">Lead score</option><option value="owner">Owner</option><option value="name">Nombre</option></select></label>
        <div className="flex items-end"><button className="primary-btn w-full" type="submit">Aplicar</button></div>
      </form>

      <div className="mb-4 flex flex-wrap gap-2 text-xs text-slate-300">
        <span className="mono-pill">Foco: {filter}</span>
        <span className="mono-pill">Relación: {relation}</span>
        <span className="mono-pill">Modo: {mode}</span>
        <span className="mono-pill">Urgencia: {urgency}</span>
        <span className="mono-pill">Orden: {sort}</span>
      </div>
    </>
  );
}
