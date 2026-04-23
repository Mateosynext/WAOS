"use client";

import { sendConversationMessageAction } from "../actions";
import { MODE_LABELS, QUICK_REPLIES, SNIPPETS } from "./conversation-composer/constants";
import { ConversationComposerModePanels } from "./conversation-composer/ModePanels";
import { useConversationComposerState } from "./conversation-composer/useConversationComposerState";

export default function ConversationComposer({ conversationId, redirectTo }: { conversationId: string; redirectTo: string }) {
  const state = useConversationComposerState();
  const { mode, setMode, setBody, composer } = state;
  const previewJson = composer.whatsappPayload ? JSON.stringify(composer.whatsappPayload, null, 2) : "Sin payload estructurado: se enviará texto o nota.";
  const currentMode = MODE_LABELS.find((item) => item.value === mode);

  return (
    <form action={sendConversationMessageAction} className="sticky top-4 space-y-4 rounded-3xl border border-white/[0.08] bg-slate-950/70 p-4">
      <input type="hidden" name="conversation_id" value={conversationId} />
      <input type="hidden" name="redirect_to" value={redirectTo} />
      <input type="hidden" name="kind" value={composer.kind} />
      <input type="hidden" name="body" value={composer.body} />
      <input type="hidden" name="whatsapp_payload" value={composer.whatsappPayload ? JSON.stringify(composer.whatsappPayload) : ""} />

      <div>
        <div className="eyebrow">Composer visual de WhatsApp</div>
        <div className="mt-1 text-lg font-semibold text-white">Responder con payload first-class, no solo texto</div>
        <p className="mt-2 text-sm leading-6 text-slate-300">Elige el tipo de salida y el composer arma el payload estructurado para media, templates, botones, listas, flows, productos, catálogo o mark-as-read.</p>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {MODE_LABELS.map((item) => {
          const active = item.value === mode;
          return (
            <button
              key={item.value}
              type="button"
              className={active ? "primary-btn justify-start text-left" : "secondary-btn justify-start text-left"}
              onClick={() => setMode(item.value)}
            >
              <span className="flex flex-col items-start">
                <span>{item.label}</span>
                <span className="text-[11px] uppercase tracking-[0.16em] opacity-80">{item.hint}</span>
              </span>
            </button>
          );
        })}
      </div>

      <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-3 text-xs text-slate-300">
        <div className="flex flex-wrap gap-2">
          <span className="mono-pill">Modo activo: {currentMode?.label}</span>
          <span className="mono-pill">Canal: WhatsApp</span>
          <span className="mono-pill">Payload: {composer.whatsappPayload ? "estructurado" : composer.kind === "note" ? "nota interna" : "texto plano"}</span>
        </div>
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

      <ConversationComposerModePanels state={state} />

      <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-3">
        <div className="mb-2 text-xs uppercase tracking-[0.16em] text-slate-500">Preview del payload</div>
        <pre className="max-h-[320px] overflow-auto whitespace-pre-wrap text-xs leading-6 text-slate-200">{previewJson}</pre>
      </div>

      {composer.errors.length ? (
        <div className="rounded-3xl border border-amber-400/20 bg-amber-400/10 p-3 text-sm text-amber-100">
          <div className="mb-2 font-semibold">Antes de enviar, corrige esto:</div>
          <ul className="space-y-1">
            {composer.errors.map((error) => <li key={error}>• {error}</li>)}
          </ul>
        </div>
      ) : null}

      <button className="primary-btn w-full" type="submit" disabled={composer.errors.length > 0}>Enviar por WhatsApp</button>
      <div className="text-xs text-slate-400">Tip: este composer ya manda payload estructurado first-class. Lo que ves en el preview es lo que entra al backend y sale al worker.</div>
    </form>
  );
}
