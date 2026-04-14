import Link from "next/link";
import { reactivateConversationAction, sendConversationMessageAction, takeoverConversationAction } from "../../actions";
import { Badge, ContextTip, DataTable, KeyValueList, PermissionGate, Section, Shell, StatCard, TimelineList } from "../../components";
import ConfirmSubmitButton from "../../components/ConfirmSubmitButton";
import { canReactivateConversation, canReplyConversation, canTakeoverConversation, roleLabel } from "../../lib/permissions";
import { getSession } from "../../lib/session";
import { formatNumber, safeText } from "../../lib/ui";
import { getConversation } from "../../lib/waos";

export default async function ConversationDetailPage({ params }: { params: Promise<{ conversationId: string }> }) {
  const { conversationId } = await params;
  const session = await getSession();
  const role = session?.user.global_role;
  const data = await getConversation(conversationId);
  const conversation = data.conversation;
  const messages = data.messages;
  const memory = data.memory;
  const inbound = messages.filter((message) => String(message.direction || "").toLowerCase() !== "outbound");
  const outbound = messages.filter((message) => String(message.direction || "").toLowerCase() === "outbound");
  const nextSteps = [
    String(conversation.status || "").toLowerCase() === "human_takeover" ? { title: "Caso en takeover humano", detail: "Mantener responsable visible y responder antes de devolver a IA.", tone: "gold" as const } : { title: "IA en curso", detail: "Solo interviene manualmente si el contexto o el cliente lo exigen.", tone: "green" as const },
    !conversation.last_outbound_at ? { title: "Sin salida reciente", detail: "Conviene responder o reasignar para no dejar la conversacion congelada.", tone: "red" as const } : null,
    conversation.lead_stage ? { title: "Etapa comercial", detail: `La conversacion esta en ${safeText(conversation.lead_stage)} y debe tratarse acorde al momento del lead.`, tone: "slate" as const } : null,
  ].filter(Boolean) as Array<{ title: string; detail: string; tone?: "slate" | "green" | "gold" | "red" | "blue" }>;

  return (
    <Shell title={safeText(data.contact?.full_name || data.contact?.name || conversation.contact_name, "Conversacion")} subtitle="Todo el hilo en una vista clara: contexto, memoria, mensajes y acciones protegidas por rol para intervenir sin perder orden." action={<><Link href="/inbox?filter=all" className="secondary-btn">Volver al inbox</Link><Link href="/support" className="secondary-btn">Modo soporte</Link></>}>
      <ContextTip>Tu rol visible ahora es {roleLabel(role)}. Esta pantalla ya separa leer, tomar, reactivar y responder para reducir acciones accidentales.</ContextTip>
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Mensajes" value={formatNumber(messages.length)} hint="Hilo visible" icon="chat" tone="blue" />
        <StatCard label="Entrantes" value={formatNumber(inbound.length)} hint="Mensajes del cliente" icon="support" tone="slate" />
        <StatCard label="Salientes" value={formatNumber(outbound.length)} hint="Respuestas del sistema o humanas" icon="spark" tone="green" />
        <StatCard label="Score lead" value={formatNumber(conversation.lead_score || 0)} hint="Intencion visible" icon="target" tone={Number(conversation.lead_score || 0) >= 70 ? "red" : "gold"} />
      </div>
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-6">
          <Section title="Resumen" subtitle="Lo mas util antes de responder o tomar el caso." icon="chat" aside={<Badge tone={String(conversation.status).toLowerCase() === "human_takeover" ? "amber" : "green"}>{safeText(conversation.status)}</Badge>}>
            <KeyValueList items={[
              { label: "Cliente", value: safeText(data.contact?.full_name || data.contact?.name) },
              { label: "Telefono", value: safeText(data.contact?.phone || conversation.contact_phone) },
              { label: "Bot", value: safeText(data.bot?.name || conversation.bot_name) },
              { label: "Lead stage", value: safeText(conversation.lead_stage) },
              { label: "Resumen", value: safeText(conversation.summary) },
            ]} />
            <div className="mt-4 flex flex-wrap gap-2">
              <PermissionGate allowed={canTakeoverConversation(role)} fallback={<span className="mono-pill">No puedes tomar el caso</span>}>
                <form action={takeoverConversationAction}>
                  <input type="hidden" name="conversation_id" value={conversationId} />
                  <input type="hidden" name="redirect_to" value={`/inbox/${conversationId}`} />
                  <ConfirmSubmitButton message="Seguro que quieres tomar este caso manualmente?">Tomar caso</ConfirmSubmitButton>
                </form>
              </PermissionGate>
              <PermissionGate allowed={canReactivateConversation(role)} fallback={<span className="mono-pill">No puedes reactivar IA</span>}>
                <form action={reactivateConversationAction}>
                  <input type="hidden" name="conversation_id" value={conversationId} />
                  <input type="hidden" name="redirect_to" value={`/inbox/${conversationId}`} />
                  <ConfirmSubmitButton message="Seguro que quieres devolver esta conversacion a la IA?">Devolver a IA</ConfirmSubmitButton>
                </form>
              </PermissionGate>
            </div>
          </Section>
          <Section title="Que sigue" subtitle="Una ruta corta para intervenir sin romper el orden comercial u operativo." icon="route">
            <TimelineList items={nextSteps} />
          </Section>
          <Section title="Memoria y contexto" subtitle="Lo que el sistema sabe de esta conversacion y puede ayudarte a responder mejor." icon="stack">
            <DataTable columns={["Dato", "Valor"]} rows={[
              ["Ultimo outbound", safeText(conversation.last_outbound_at || "sin salida reciente")],
              ["Ultimo inbound", safeText(conversation.last_inbound_at || "sin dato")],
              ["Owner", safeText(conversation.owner_name || conversation.owner_id || "sin asignar")],
              ["Memoria corta", safeText(memory.summary || memory.short_summary || JSON.stringify(memory))],
            ]} />
          </Section>
        </div>
        <Section title="Mensajes" subtitle="El hilo completo para revisar contexto y responder con precision." icon="chat">
          <div className="space-y-3">
            {messages.length ? messages.map((message, index) => <div key={message.id || index} className={`rounded-3xl border px-4 py-3 text-sm ${String(message.direction).toLowerCase() === "outbound" ? "ml-auto max-w-[85%] border-emerald-400/[0.20] bg-emerald-400/[0.10] text-emerald-50" : "max-w-[85%] border-white/[0.08] bg-white/[0.04] text-slate-100"}`}>
              <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">{safeText(message.direction, "mensaje")}</div>
              <div className="mt-2 leading-6">{safeText(message.body)}</div>
              <div className="mt-2 text-[11px] text-slate-400">{safeText(message.created_at || message.sent_at || message.timestamp)}</div>
            </div>) : <TimelineList items={[{ title: "Sin mensajes todavia", detail: "Cuando esta conversacion tenga actividad, el historial aparecera aqui para que puedas actuar con contexto.", tone: "slate" }]} />}
          </div>
          <PermissionGate allowed={canReplyConversation(role)} fallback={<div className="mt-5 rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-4 text-sm text-slate-300">Tu rol puede revisar el hilo pero no enviar mensajes desde esta pantalla.</div>}>
            <form action={sendConversationMessageAction} className="mt-5 space-y-3">
              <input type="hidden" name="conversation_id" value={conversationId} />
              <input type="hidden" name="redirect_to" value={`/inbox/${conversationId}`} />
              <textarea name="body" className="field-input min-h-[120px] w-full" placeholder="Escribe una respuesta clara para el cliente" />
              <button className="primary-btn" type="submit">Enviar mensaje</button>
            </form>
          </PermissionGate>
        </Section>
      </div>
    </Shell>
  );
}
