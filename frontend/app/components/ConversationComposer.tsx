"use client";

import { useState } from "react";
import { sendConversationMessageAction } from "../actions";

const QUICK_REPLIES = [
  "Hola, ya estoy revisando tu caso y te respondo con claridad en un momento.",
  "Gracias por escribir. ¿Me confirmas el pedido, cita o tema exacto para ayudarte más rápido?",
  "Ya tomé este caso manualmente. Te acompaño por aquí hasta cerrarlo.",
  "Entendido. Voy a verificarlo y te comparto el siguiente paso hoy mismo.",
];

const SNIPPETS = [
  { label: "Seguimiento", value: "Dame unos minutos para revisarlo y te confirmo por aquí el siguiente paso." },
  { label: "Agendar", value: "¿Qué horario te funciona mejor? Te comparto opciones en cuanto me confirmes." },
  { label: "Cobro", value: "Voy a revisar el estatus del cobro y te actualizo con la referencia exacta." },
];

export default function ConversationComposer({ conversationId, redirectTo }: { conversationId: string; redirectTo: string }) {
  const [body, setBody] = useState("");

  return (
    <form action={sendConversationMessageAction} className="sticky top-4 space-y-4 rounded-3xl border border-white/[0.08] bg-slate-950/70 p-4">
      <input type="hidden" name="conversation_id" value={conversationId} />
      <input type="hidden" name="redirect_to" value={redirectTo} />
      <div>
        <div className="eyebrow">Composer fijo</div>
        <div className="mt-1 text-lg font-semibold text-white">Responder sin perder el contexto</div>
        <p className="mt-2 text-sm leading-6 text-slate-300">Usa quick replies para contestar más rápido y luego ajusta el texto antes de enviarlo.</p>
      </div>

      <div className="space-y-2">
        <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Quick replies</div>
        <div className="flex flex-wrap gap-2">
          {QUICK_REPLIES.map((item) => (
            <button key={item} type="button" className="secondary-btn" onClick={() => setBody(item)}>{item.slice(0, 28)}…</button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Snippets operativos</div>
        <div className="flex flex-wrap gap-2">
          {SNIPPETS.map((item) => (
            <button key={item.label} type="button" className="secondary-btn" onClick={() => setBody((value) => value ? `${value}\n\n${item.value}` : item.value)}>{item.label}</button>
          ))}
        </div>
      </div>

      <textarea name="body" value={body} onChange={(event) => setBody(event.currentTarget.value)} className="field-input min-h-[180px] w-full" placeholder="Escribe una respuesta clara para el cliente" />
      <button className="primary-btn w-full" type="submit">Enviar mensaje</button>
      <div className="text-xs text-slate-400">Tip: responde breve, confirma el siguiente paso y evita mezclar temas comerciales con personales sin validarlo.</div>
    </form>
  );
}
