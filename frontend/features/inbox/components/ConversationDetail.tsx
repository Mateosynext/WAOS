import Link from "next/link";
import { formatNumber, safeText } from "@/app/lib/ui";
import { reactivateConversationAction, takeoverConversationAction } from "@/features/inbox/actions";
import { buildInboxQuery, type InboxPageModel } from "@/features/inbox/server/getInboxPageModel";
import { urgencyLabel } from "./inboxViewHelpers";

export function ConversationDetail({ model }: { model: InboxPageModel }) {
  const { selected, decisionSupport, filters } = model;
  if (!selected) return null;
  const { filter, sort, q, relation, mode, urgency } = filters;
  const redirectTo = `/inbox${buildInboxQuery({ filter, sort, q, relation, mode, urgency, selected: selected.id })}`;

  return (
    <div className="space-y-4 xl:sticky xl:top-28">
      <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Preview</div>
            <div className="mt-1 text-2xl font-semibold text-white">{safeText(selected.contact_name, "Sin nombre")}</div>
            <div className="mt-2 text-sm text-slate-400">{safeText(selected.contact_phone)} · {safeText(selected.bot_name, "Sin asistente operativo")}</div>
          </div>
          <Link href={`/inbox/${selected.id}`} className="primary-btn">Abrir detalle</Link>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="surface-row"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">Relación</div><div className="mt-1 font-medium text-white">{safeText(selected.relationship_label || selected.relationship_key || "nuevo")}</div></div>
          <div className="surface-row"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">Urgencia</div><div className="mt-1 font-medium text-white">{urgencyLabel(selected.urgency_level)}</div></div>
          <div className="surface-row"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">Modo recomendado</div><div className="mt-1 font-medium text-white">{safeText(selected.recommended_mode || "universal")}</div></div>
          <div className="surface-row"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">Cola / SLA</div><div className="mt-1 font-medium text-white">{safeText(selected.work_queue_role || "soporte")} · {safeText(selected.sla_status || "healthy")}</div></div>
        </div>
        <p className="mt-4 text-sm leading-7 text-slate-300">{safeText(selected.summary || selected.latest_message_preview, "Sin resumen visible")}</p>
        <div className="mt-4 rounded-2xl border border-white/[0.08] bg-black/20 p-4">
          <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Next best action</div>
          <div className="mt-2 text-base font-medium text-white">{safeText(selected.next_best_action, "Dar seguimiento")}</div>
          <div className="mt-2 text-sm text-slate-400">Clase: {safeText(selected.attention_class, "ai_or_operator")} · Prioridad {formatNumber(selected.priority_score || 0)} · SLA {safeText(selected.sla_status || "healthy")}</div>
        </div>
        {decisionSupport ? (
          <div className="mt-4 rounded-2xl border border-white/[0.08] bg-black/20 p-4">
            <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Decisión IA y confianza</div>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className="mono-pill">Confianza {formatNumber(decisionSupport.confidence_score || 0)}</span>
              <span className="mono-pill">Banda {safeText(decisionSupport.confidence_band || "low")}</span>
              <span className="mono-pill capitalize">{safeText(String(decisionSupport.queue?.role_key || selected.work_queue_role || "soporte"))}</span>
            </div>
            <div className="mt-3 text-sm leading-6 text-slate-300">{safeText(String(decisionSupport.explanation?.policy_applied || decisionSupport.explanation?.intent_detected || "Sin explicación estructurada"))}</div>
            {(decisionSupport.risk_flags || []).length ? <div className="mt-3 text-xs text-amber-300">Riesgos: {(decisionSupport.risk_flags || []).map((item) => safeText(String(item.message || item.key || "riesgo"))).join(" · ")}</div> : null}
          </div>
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <form action={takeoverConversationAction}>
          <input type="hidden" name="conversation_id" value={selected.id} />
          <input type="hidden" name="redirect_to" value={redirectTo} />
          <button className="secondary-btn w-full" type="submit">Tomar caso</button>
        </form>
        <form action={reactivateConversationAction}>
          <input type="hidden" name="conversation_id" value={selected.id} />
          <input type="hidden" name="redirect_to" value={redirectTo} />
          <button className="secondary-btn w-full" type="submit">Devolver a IA</button>
        </form>
        <Link href={`/inbox/${selected.id}`} className="secondary-btn w-full">Responder</Link>
      </div>
    </div>
  );
}
