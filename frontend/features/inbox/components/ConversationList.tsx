import Link from "next/link";
import { StatusPill } from "@/app/components/feedback";
import { formatNumber, safeText } from "@/app/lib/ui";
import { buildInboxQuery, type InboxPageModel } from "@/features/inbox/server/getInboxPageModel";
import { priorityLabel, urgencyLabel } from "./inboxViewHelpers";

export function ConversationList({ model }: { model: InboxPageModel }) {
  const { filtered, selected, filters } = model;
  const { filter, sort, q, relation, mode, urgency } = filters;

  return (
    <div className="space-y-3 xl:max-h-[900px] xl:overflow-y-auto xl:pr-2">
      {filtered.map((item) => {
        const active = selected?.id === item.id;
        return (
          <Link
            key={item.id}
            href={`/inbox${buildInboxQuery({ filter, sort, q, relation, mode, urgency, selected: item.id })}`}
            className={`block rounded-3xl border p-4 transition ${active ? "border-emerald-400/[0.24] bg-emerald-400/[0.10]" : "border-white/[0.08] bg-white/[0.03] hover:border-white/[0.16] hover:bg-white/[0.05]"}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate text-base font-semibold text-white">{safeText(item.contact_name, "Sin nombre")}</div>
                <div className="mt-1 text-xs text-slate-400">{safeText(item.contact_phone)}</div>
              </div>
              <span className="mono-pill">{priorityLabel(item)}</span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusPill status={safeText(item.status)} />
              <span className="mono-pill">{safeText(item.relationship_label || item.relationship_key || "nuevo")}</span>
              <span className="mono-pill">{urgencyLabel(item.urgency_level)}</span>
              <span className="mono-pill">Lead {formatNumber(item.lead_score || 0)}</span>
              <span className="mono-pill">Prioridad {formatNumber(item.priority_score || 0)}</span>
              <span className="mono-pill capitalize">{safeText(item.work_queue_role || "soporte")}</span>
              <span className="mono-pill">SLA {safeText(item.sla_status || "healthy")}</span>
            </div>
            <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-300">{safeText(item.latest_message_preview || item.summary, "Sin resumen visible")}</p>
            <div className="mt-2 text-xs text-slate-400">NBA: {safeText(item.next_best_action, "Dar seguimiento")}{item.stalled ? " · estancada" : ""}</div>
            <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
              <span>{safeText(item.bot_name, "Sin asistente operativo")}</span>
              <span>{safeText(item.recommended_mode || item.relationship_status || "universal")}</span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
