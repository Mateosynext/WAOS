import type { ConversationComposerState } from "../useConversationComposerState";

export function ConversationComposerBasicModePanel({ state }: { state: ConversationComposerState }) {
  const {
    mode,
    body,
    setBody,
    templateName,
    setTemplateName,
    templateLanguageCode,
    setTemplateLanguageCode,
    templateBodyParams,
    setTemplateBodyParams,
  } = state;

  if (mode === "text" || mode === "note") {
    return (
      <label className="field-label">
        {mode === "note" ? "Nota interna" : "Mensaje"}
        <textarea
          value={body}
          onChange={(event) => setBody(event.currentTarget.value)}
          className="field-input min-h-[180px] w-full"
          placeholder={mode === "note" ? "Escribe una nota para el equipo" : "Escribe una respuesta clara para el cliente"}
        />
      </label>
    );
  }

  if (mode === "template") {
    return (
      <div className="grid gap-3 md:grid-cols-2">
        <label className="field-label">Template name
          <input className="field-input" value={templateName} onChange={(event) => setTemplateName(event.currentTarget.value)} placeholder="follow_up_v1" />
        </label>
        <label className="field-label">Language code
          <input className="field-input" value={templateLanguageCode} onChange={(event) => setTemplateLanguageCode(event.currentTarget.value)} placeholder="es_MX" />
        </label>
        <label className="field-label md:col-span-2">Body params, uno por línea
          <textarea className="field-input min-h-[120px]" value={templateBodyParams} onChange={(event) => setTemplateBodyParams(event.currentTarget.value)} placeholder={"Cliente\nPedido 123\nHoy 18:00"} />
        </label>
      </div>
    );
  }

  return null;
}
