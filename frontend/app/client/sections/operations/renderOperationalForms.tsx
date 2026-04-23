import { ClientEmptyBlock, ClientSectionBlock } from "../../../components/client/ClientPortalPrimitives";
import { createAuthorizedOperationalNumberAction, executeRescheduleBatchAction, previewRescheduleBatchAction, submitOperationalCommandAction } from "../../../actions/operational_control";
import { safeText } from "../../../lib/ui";
import type { ClientOperationsPayload } from "./types";

export function renderOperationalForms({ organizationId, botId, authorizedNumbers }: { organizationId: string; botId: string; authorizedNumbers: ClientOperationsPayload["summary"]["authorized_numbers"] }) {
  return (
    <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
      <ClientSectionBlock title="Reprogramación masiva guiada" subtitle="Haz preview y ejecución con matching real de slots usando la capacidad declarada.">
        <div className="grid gap-3 lg:grid-cols-2">
          <form action={previewRescheduleBatchAction} className="grid gap-3 rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
            <input type="hidden" name="organization_id" value={organizationId} />
            <input type="hidden" name="bot_id" value={botId} />
            <input type="hidden" name="redirect_to" value="/client/operaciones" />
            <input name="scope_day" defaultValue="tomorrow" placeholder="today | tomorrow | custom" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
            <input name="target_date" placeholder="2026-04-20" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
            <input name="target_start_time" defaultValue="09:00" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
            <input name="target_end_time" defaultValue="18:00" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
            <input name="delay_minutes" defaultValue="30" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
            <button type="submit" className="secondary-btn">Simular reprogramación</button>
          </form>
          <form action={executeRescheduleBatchAction} className="grid gap-3 rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
            <input type="hidden" name="organization_id" value={organizationId} />
            <input type="hidden" name="bot_id" value={botId} />
            <input type="hidden" name="redirect_to" value="/client/operaciones" />
            <input name="scope_day" defaultValue="tomorrow" placeholder="today | tomorrow | custom" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
            <input name="target_date" placeholder="2026-04-20" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
            <input name="target_start_time" defaultValue="09:00" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
            <input name="target_end_time" defaultValue="18:00" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
            <input name="delay_minutes" defaultValue="30" className="rounded-3xl border border-[color:var(--border-soft)] bg-white/70 px-4 py-3 text-sm" />
            <label className="flex items-center gap-2 text-sm text-[color:var(--text-secondary)]"><input type="checkbox" name="notify_clients" /> Notificar clientes</label>
            <button type="submit" className="primary-btn">Ejecutar reprogramación</button>
          </form>
        </div>
      </ClientSectionBlock>

      <ClientSectionBlock title="Comando libre" subtitle="Escribe un comando natural como 'bloquéame mañana de 2 a 6' o 'apaga el bot'.">
        <form action={submitOperationalCommandAction} className="space-y-4">
          <input type="hidden" name="organization_id" value={organizationId} />
          <input type="hidden" name="bot_id" value={botId} />
          <input type="hidden" name="redirect_to" value="/client/operaciones" />
          <textarea name="text" rows={4} className="w-full rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm text-[color:var(--text-primary)]" placeholder="Ejemplo: avísale a mis citas de hoy que voy 30 minutos tarde" />
          <div className="flex flex-wrap gap-3">
            <button type="submit" name="mode" value="preview" className="secondary-btn">Simular impacto</button>
            <button type="submit" name="mode" value="execute" className="primary-btn">Ejecutar comando</button>
          </div>
        </form>
      </ClientSectionBlock>

      <ClientSectionBlock title="Autorizar número" subtitle="Da de alta números que sí pueden controlar el bot por WhatsApp.">
        <form action={createAuthorizedOperationalNumberAction} className="grid gap-3">
          <input type="hidden" name="organization_id" value={organizationId} />
          <input type="hidden" name="bot_id" value={botId} />
          <input type="hidden" name="redirect_to" value="/client/operaciones" />
          <input name="phone_e164" placeholder="+5215550001111" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
          <input name="role" placeholder="owner" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
          <input name="allowed_intents" placeholder="appointment.notify_affected,bot.pause" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
          <input name="scope_branches" placeholder="Centro,Norte" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
          <input name="scope_resource_names" placeholder="Dra. Ana,Dr. Luis" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
          <input name="scope_service_names" placeholder="Limpieza,Consulta" className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm" />
          <button type="submit" className="primary-btn">Autorizar número</button>
        </form>
        <div className="mt-4 space-y-3">
          {authorizedNumbers.length ? authorizedNumbers.slice(0, 4).map((item) => (
            <div key={String(item.id)} className="surface-row">
              <div className="font-medium text-[color:var(--text-primary)]">{safeText(String(item.phone_e164 || ""), "Sin número")}</div>
              <div className="text-sm text-[color:var(--text-secondary)]">{safeText(String(item.role || "owner"), "owner")} · {safeText(String(item.status || "verified"), "verified")} · {safeText(String(item.scope_summary || "Sin restricción"), "Sin restricción")}</div>
            </div>
          )) : <ClientEmptyBlock title="Sin números autorizados" description="Hasta que autorices un número, los mensajes por chat no ejecutarán comandos operativos." />}
        </div>
      </ClientSectionBlock>
    </div>
  );
}
