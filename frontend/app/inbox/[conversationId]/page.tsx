import Link from "next/link";
import { reactivateConversationAction, takeoverConversationAction } from "@/app/actions/conversations";
import ConversationComposer from "../../components/ConversationComposer";
import { ContextTip, PermissionGate } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable, KeyValueList, TimelineList } from "@/app/components/primitives/data-display";
import { Badge } from "@/app/components/primitives/shared";
import ConfirmSubmitButton from "../../components/ConfirmSubmitButton";
import { canReactivateConversation, canReplyConversation, canTakeoverConversation, roleLabel } from "../../lib/permissions";
import { getSession } from "../../lib/session";
import { formatNumber, safeText } from "../../lib/ui";
import { getConversation } from "@/app/lib/data/inbox";

function urgencyLabel(level?: string) {
  const normalized = String(level || "normal").toLowerCase();
  if (normalized === "critical") return "Crítica";
  if (normalized === "high") return "Alta";
  if (normalized === "medium") return "Media";
  return "Normal";
}

export default async function ConversationDetailPage({ params }: { params: Promise<{ conversationId: string }> }) {
  const { conversationId } = await params;
  const session = await getSession();
  const role = session?.user.global_role;
  const data = await getConversation(conversationId);
  const conversation = data.conversation;
  const messages = data.messages;
  const memory = data.memory;
  const relationship = (memory.memory as Record<string, unknown> | undefined)?.relationship_intelligence as Record<string, unknown> | undefined;
  const inbound = messages.filter((message) => String(message.direction || "").toLowerCase() !== "outbound");
  const outbound = messages.filter((message) => String(message.direction || "").toLowerCase() === "outbound");

  const nextSteps = [
    String(conversation.status || "").toLowerCase() === "human_takeover"
      ? { title: "Caso en takeover humano", detail: "Mantén el responsable visible y contesta antes de devolverlo a IA.", tone: "gold" as const }
      : { title: "IA todavía puede operar", detail: "Solo intervén manualmente si el contexto, la relación o el cliente lo exigen.", tone: "green" as const },
    !conversation.last_outbound_at ? { title: "Sin salida reciente", detail: "Conviene responder o reasignar para no dejar congelado el hilo.", tone: "red" as const } : null,
    relationship?.attention_tier === "owner_now" ? { title: "Escala sugerida al dueño", detail: "La capa relacional detectó prioridad alta por vínculo o contexto sensible.", tone: "red" as const } : null,
    conversation.lead_stage ? { title: "Etapa comercial", detail: `La conversación está en ${safeText(conversation.lead_stage)} y el tono debe acompañar ese momento del lead.`, tone: "slate" as const } : null,
  ].filter(Boolean) as Array<{ title: string; detail: string; tone?: "slate" | "green" | "gold" | "red" | "blue" }>;

  return (
    <Shell
      title={safeText(data.contact?.full_name || data.contact?.name || conversation.contact_name, "Conversación")}
      subtitle="El detalle separa lectura, decisiones y respuesta. Las acciones viven arriba y el composer queda fijo para que no pierdas contexto mientras revisas el hilo."
      action={<><Link href="/inbox" className="secondary-btn">Volver al inbox</Link><Link href="/operations" className="secondary-btn">Operaciones</Link></>}
    >
      <ContextTip title="Cómo operar este hilo">Tu rol visible ahora es {roleLabel(role)}. Esta pantalla ya distingue relación, urgencia, intervención y respuesta para reducir errores de operación.</ContextTip>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Mensajes" value={formatNumber(messages.length)} hint="Hilo visible" icon="chat" tone="blue" />
        <StatCard label="Entrantes" value={formatNumber(inbound.length)} hint="Mensajes del cliente" icon="support" tone="slate" />
        <StatCard label="Salientes" value={formatNumber(outbound.length)} hint="Respuestas del sistema o humanas" icon="spark" tone="green" />
        <StatCard label="Lead score" value={formatNumber(conversation.lead_score || 0)} hint="Señal comercial visible" icon="target" tone={Number(conversation.lead_score || 0) >= 70 ? "red" : "gold"} />
      </div>

      <Section title="Acciones rápidas" subtitle="La toma de decisiones ya no está enterrada al final del hilo." icon="route">
        <div className="flex flex-wrap gap-3">
          <PermissionGate allowed={canTakeoverConversation(role)} fallback={<span className="mono-pill">No puedes tomar el caso</span>}>
            <form action={takeoverConversationAction}>
              <input type="hidden" name="conversation_id" value={conversationId} />
              <input type="hidden" name="redirect_to" value={`/inbox/${conversationId}`} />
              <ConfirmSubmitButton message="¿Seguro que quieres tomar este caso manualmente?">Tomar caso</ConfirmSubmitButton>
            </form>
          </PermissionGate>
          <PermissionGate allowed={canReactivateConversation(role)} fallback={<span className="mono-pill">No puedes reactivar IA</span>}>
            <form action={reactivateConversationAction}>
              <input type="hidden" name="conversation_id" value={conversationId} />
              <input type="hidden" name="redirect_to" value={`/inbox/${conversationId}`} />
              <ConfirmSubmitButton message="¿Seguro que quieres devolver esta conversación a la IA?">Devolver a IA</ConfirmSubmitButton>
            </form>
          </PermissionGate>
          <Link href="#composer" className="secondary-btn">Ir al composer</Link>
        </div>
      </Section>

      <div className="grid gap-6 xl:grid-cols-[0.86fr_1.14fr_0.92fr]">
        <div className="xl:col-span-3 flex flex-wrap gap-2 text-xs text-slate-300">
          <span className="mono-pill">Relación: {safeText(relationship?.relation_label || "nuevo")}</span>
          <span className="mono-pill">Urgencia: {urgencyLabel(String(relationship?.urgency_level || conversation.urgency_level || "normal"))}</span>
          <span className="mono-pill">Modo: {safeText(relationship?.current_mode || conversation.recommended_mode || "universal")}</span>
          <span className="mono-pill">Atención: {safeText(relationship?.attention_tier || conversation.attention_tier || "normal")}</span>
        </div>
        <div className="space-y-6 xl:col-span-1">
          <Section title="Resumen" subtitle="Lo más útil antes de responder." icon="chat" aside={<Badge tone={String(conversation.status).toLowerCase() === "human_takeover" ? "amber" : "green"}>{safeText(conversation.status)}</Badge>}>
            <KeyValueList items={[
              { label: "Cliente", value: safeText(data.contact?.full_name || data.contact?.name) },
              { label: "Teléfono", value: safeText(data.contact?.phone || conversation.contact_phone) },
              { label: "Bot", value: safeText(data.bot?.name || conversation.bot_name) },
              { label: "Lead stage", value: safeText(conversation.lead_stage) },
              { label: "Resumen", value: safeText(conversation.summary) },
            ]} />
          </Section>

          <Section title="Perfil relacional" subtitle="Negocio puro, conocido, proveedor, familia o mezcla." icon="support">
            <DataTable columns={["Dato", "Valor"]} rows={[
              ["Relación detectada", safeText(relationship?.relation_label || "nuevo")],
              ["Contacto conocido", safeText(relationship?.known_contact ? "sí" : "no")],
              ["Confianza", safeText(relationship?.relation_confidence || 0)],
              ["Modo recomendado", safeText(relationship?.current_mode || conversation.recommended_mode || "universal")],
              ["Urgencia", safeText(urgencyLabel(String(relationship?.urgency_level || conversation.urgency_level || "normal")))],
              ["Tier de atención", safeText(relationship?.attention_tier || conversation.attention_tier || "normal")],
              ["Intención actual", safeText(relationship?.current_intent || "general")],
              ["Temas top", safeText(Array.isArray(relationship?.top_topics) ? relationship?.top_topics.join(", ") : "sin datos")],
            ]} />
          </Section>

          <Section title="Qué sigue" subtitle="Ruta corta para intervenir con orden." icon="target">
            <TimelineList items={nextSteps} />
          </Section>
        </div>

        <Section title="Mensajes" subtitle="El hilo completo para revisar el contexto real antes de responder." icon="chat">
          <div className="space-y-3 xl:max-h-[980px] xl:overflow-y-auto xl:pr-2">
            {messages.length ? messages.map((message, index) => (
              <div key={message.id || index} className={`rounded-3xl border px-4 py-3 text-sm ${String(message.direction).toLowerCase() === "outbound" ? "ml-auto max-w-[85%] border-emerald-400/[0.20] bg-emerald-400/[0.10] text-emerald-50" : "max-w-[85%] border-white/[0.08] bg-white/[0.04] text-slate-100"}`}>
                <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-slate-400">
                  <span>{safeText(message.direction, "mensaje")}</span>
                  <span className="mono-pill">{safeText(message.kind || "text")}</span>
                  <span className="mono-pill">{safeText(message.status || "received")}</span>
                  <span className="mono-pill">{safeText(message.source || "whatsapp")}</span>
                </div>
                <div className="mt-2 leading-6">{safeText(message.body)}</div>
                <div className="mt-2 text-[11px] text-slate-400">{safeText(message.created_at || message.sent_at || message.timestamp)}</div>
              </div>
            )) : <TimelineList items={[{ title: "Sin mensajes todavía", detail: "Cuando esta conversación tenga actividad, el historial aparecerá aquí.", tone: "slate" }]} />}
          </div>
        </Section>

        <div className="xl:col-span-1" id="composer">
          <Section title="Memoria y contexto" subtitle="Lo que el sistema sabe para ayudarte a responder mejor." icon="stack">
            <DataTable columns={["Dato", "Valor"]} rows={[
              ["Último outbound", safeText(conversation.last_outbound_at || "sin salida reciente")],
              ["Último inbound", safeText(conversation.last_inbound_at || "sin dato")],
              ["Owner", safeText(conversation.owner_name || conversation.owner_id || "sin asignar")],
              ["Memoria corta", safeText(memory.summary || memory.short_summary || JSON.stringify(memory))],
            ]} />
          </Section>
          <div className="mt-6">
            <PermissionGate allowed={canReplyConversation(role)} fallback={<div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-4 text-sm text-slate-300">Tu rol puede revisar el hilo pero no enviar mensajes desde esta pantalla.</div>}>
              <ConversationComposer conversationId={conversationId} redirectTo={`/inbox/${conversationId}`} />
            </PermissionGate>
          </div>
        </div>
      </div>
    </Shell>
  );
}
