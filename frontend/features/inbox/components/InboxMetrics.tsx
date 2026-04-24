import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import { formatNumber, safeText } from "@/app/lib/ui";
import { autoAssignInboxAction } from "@/features/inbox/actions";
import type { InboxPageModel } from "@/features/inbox/server/getInboxPageModel";

export function InboxMetrics({ model }: { model: InboxPageModel }) {
  const { metrics, verticalProfile, currentOrg, queueSummary, ownership, owners, activeOrganizationId, hasOrganizationContext } = model;
  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Conversaciones" value={formatNumber(metrics.total)} hint="Total visible" icon="chat" tone="blue" />
        <StatCard label="Takeover humano" value={formatNumber(metrics.human)} hint="Casos ya tomados manualmente" icon="support" tone="gold" />
        <StatCard label="Pendientes" value={formatNumber(metrics.pending)} hint="Sin salida reciente" icon="alert" tone="green" />
        <StatCard label="Dueño ahora" value={formatNumber(metrics.ownerNow)} hint="Relación o urgencia que escalan" icon="target" tone={metrics.ownerNow ? "red" : "slate"} />
      </div>

      {verticalProfile?.id ? (
        <Section title="Inbox alineado a la industria" subtitle="La prioridad ya no debería sentirse genérica: esta bandeja se interpreta con el tipo de operación activo como contexto comercial y operativo." icon="wand">
          <div className="grid gap-4 xl:grid-cols-4">
            <StatCard label="Tipo de operación" value={safeText(verticalProfile.selected_subvertical?.name, currentOrg?.subvertical || "sin definir")} hint={safeText(String(verticalProfile.runtime_connection?.surface_focus?.inbox || "calificación operativa"))} icon="spark" tone="green" />
            <StatCard label="Preguntas clave" value={formatNumber((verticalProfile.selected_subvertical?.qualification_questions || []).length)} hint="Qué debería detectar el asistente operativo u operador" icon="chat" tone="blue" />
            <StatCard label="Objeciones foco" value={formatNumber((verticalProfile.selected_subvertical?.objections || []).length)} hint="Qué conviene resolver rápido" icon="support" tone="gold" />
            <StatCard label="Comando operativo" value={safeText((verticalProfile.selected_subvertical?.recommended_commands || [])[0], "sin comando")} hint="Control sugerido para esta industria" icon="tool" tone="slate" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <ModuleCard title="Motion comercial" description={safeText(verticalProfile.selected_subvertical?.growth_motion, "Sin motion")} icon="target" tone="green" />
            <ModuleCard title="Buyer activo" description={safeText(verticalProfile.selected_subvertical?.buyer, verticalProfile.buyer.primary)} icon="client" tone="blue" />
            <ModuleCard title="Promesa" description={safeText(verticalProfile.selected_subvertical?.promise, verticalProfile.ten_x_narrative)} icon="rocket" tone="gold" />
          </div>
        </Section>
      ) : null}

      <Section title="Colas y SLA" subtitle="La inbox ya separa ventas, soporte, agenda y cobranza con riesgo visible de incumplimiento." icon="stats">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <form action={autoAssignInboxAction}>
            <input type="hidden" name="organization_id" value={activeOrganizationId} />
            <input type="hidden" name="redirect_to" value="/inbox" />
            <button className="secondary-btn disabled:cursor-not-allowed disabled:opacity-50" type="submit" disabled={!hasOrganizationContext}>Auto-asignar no dueñas</button>
          </form>
          <span className="mono-pill">Sin owner {formatNumber(Number((ownership as Record<string, unknown>).unassigned_open || 0))}</span>
          {!hasOrganizationContext ? <span className="text-xs text-amber-300">Selecciona una organización antes de ejecutar acciones masivas o guardar vistas.</span> : null}
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {(queueSummary.queues || []).length ? queueSummary.queues.map((queue) => (
            <div key={queue.role_key} className="surface-row">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-white capitalize">{safeText(queue.role_key)}</div>
                <span className="mono-pill">{formatNumber(queue.count)}</span>
              </div>
              <div className="mt-3 text-xs text-slate-400">Humano {formatNumber(queue.requires_human)} · Estancadas {formatNumber(queue.stalled)} · SLA breach {formatNumber(queue.sla_breached)}</div>
            </div>
          )) : <div className="surface-row text-sm text-slate-300">Todavía no hay colas calculadas para esta organización.</div>}
        </div>
        {owners.length ? (
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {owners.slice(0, 8).map((owner) => (
              <div key={String(owner.user_id || owner.full_name)} className="surface-row">
                <div className="text-sm font-medium text-white">{safeText(String(owner.full_name || ""), "Sin nombre")}</div>
                <div className="mt-2 text-xs text-slate-400">Abiertas {formatNumber(Number(owner.open_count || 0))} · Takeover {formatNumber(Number(owner.human_takeover_count || 0))}</div>
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      <Section title="Leyenda operativa" subtitle="Así se interpreta la capa relacional y la prioridad." icon="stack">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="surface-row text-sm text-slate-300"><span className="mono-pill">Urgencia</span><div className="mt-2">Qué tan rápido hay que responder.</div></div>
          <div className="surface-row text-sm text-slate-300"><span className="mono-pill">Lead</span><div className="mt-2">Qué tan cerca está de comprar o cerrar.</div></div>
          <div className="surface-row text-sm text-slate-300"><span className="mono-pill">Relación</span><div className="mt-2">Si es cliente, conocido, proveedor, familia o mixto.</div></div>
          <div className="surface-row text-sm text-slate-300"><span className="mono-pill">Modo</span><div className="mt-2">Si conviene tratarlo como ventas, soporte, operación o asistente operativo.</div></div>
        </div>
      </Section>
    </>
  );
}
