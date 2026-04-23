import { Badge } from "../../../components";
import { ClientEmptyBlock, ClientSectionBlock } from "../../../components/client/ClientPortalPrimitives";
import { approveOperationalCommandAction, cancelOperationalCommandAction, confirmOperationalCommandAction, undoOperationalCommandAction } from "../../../actions/operational_control";
import { safeText } from "../../../lib/ui";
import type { ClientOperationsPayload } from "./types";

export function renderOperationalRecentCommands({ recentCommands }: { recentCommands: ClientOperationsPayload["summary"]["recent_commands"] }) {
  return (
    <ClientSectionBlock title="Comandos recientes" subtitle="Incluye previews, comandos confirmados y acciones cancelables.">
      <div className="space-y-3">
        {recentCommands.length ? recentCommands.map((item) => (
          <div key={String(item.id)} className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={String(item.risk_level || "low") === "high" ? "gold" : "sky"}>{safeText(String(item.detected_intent || "sin intención"), "sin intención")}</Badge>
              <Badge tone="slate">{safeText(String(item.status || "queued"), "queued")}</Badge>
              {item.requires_confirmation ? <Badge tone="gold">Requiere confirmación</Badge> : null}
            </div>
            <div className="mt-3 text-sm text-[color:var(--text-secondary)]">{safeText(item.result_summary || item.created_at || "", "Sin detalle")}</div>
            <div className="mt-3 flex flex-wrap gap-3">
              {String(item.status) === "awaiting_confirmation" ? (
                <>
                  <form action={confirmOperationalCommandAction}>
                    <input type="hidden" name="command_id" value={String(item.id)} />
                    <input type="hidden" name="confirmation_code" value={safeText(String(item.confirmation_code || ""), "")} />
                    <input type="hidden" name="redirect_to" value="/client/operaciones" />
                    <button type="submit" className="secondary-btn">Confirmar</button>
                  </form>
                  <form action={cancelOperationalCommandAction}>
                    <input type="hidden" name="command_id" value={String(item.id)} />
                    <input type="hidden" name="reason" value="cancelled_from_portal" />
                    <input type="hidden" name="redirect_to" value="/client/operaciones" />
                    <button type="submit" className="secondary-btn">Cancelar</button>
                  </form>
                </>
              ) : null}
              {String(item.status) === "awaiting_second_approval" ? (
                <form action={approveOperationalCommandAction}>
                  <input type="hidden" name="command_id" value={String(item.id)} />
                  <input type="hidden" name="note" value="approved_from_portal" />
                  <input type="hidden" name="redirect_to" value="/client/operaciones" />
                  <button type="submit" className="secondary-btn">Aprobar segundo paso</button>
                </form>
              ) : null}
              {["executed", "partially_reverted"].includes(String(item.status)) && item.undoable_until ? (
                <form action={undoOperationalCommandAction}>
                  <input type="hidden" name="command_id" value={String(item.id)} />
                  <input type="hidden" name="reason" value="undo_from_portal" />
                  <input type="hidden" name="redirect_to" value="/client/operaciones" />
                  <button type="submit" className="secondary-btn">Deshacer</button>
                </form>
              ) : null}
            </div>
          </div>
        )) : <ClientEmptyBlock title="Sin comandos recientes" description="Cuando operes disponibilidad o estado del bot, aquí quedará el historial." />}
      </div>
    </ClientSectionBlock>
  );
}
