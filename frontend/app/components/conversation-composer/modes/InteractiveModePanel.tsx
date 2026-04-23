import { MAX_BUTTONS } from "../payload";
import type { ConversationComposerState } from "../useConversationComposerState";

export function ConversationComposerInteractiveModePanel({ state }: { state: ConversationComposerState }) {
  const {
    mode,
    interactiveBody,
    setInteractiveBody,
    interactiveFooter,
    setInteractiveFooter,
    buttons,
    setButtons,
    listButtonLabel,
    setListButtonLabel,
    listRows,
    setListRows,
  } = state;

  if (mode === "interactive_button") {
    return (
      <div className="space-y-3">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="field-label md:col-span-2">Texto principal
            <textarea className="field-input min-h-[110px]" value={interactiveBody} onChange={(event) => setInteractiveBody(event.currentTarget.value)} placeholder="¿Qué quieres hacer ahora?" />
          </label>
          <label className="field-label md:col-span-2">Footer
            <input className="field-input" value={interactiveFooter} onChange={(event) => setInteractiveFooter(event.currentTarget.value)} placeholder="Opcional" />
          </label>
        </div>
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Botones reply</div>
          <div className="mono-pill">Máximo {MAX_BUTTONS}</div>
        </div>
        <div className="space-y-3">
          {buttons.map((button, index) => (
            <div key={`button-${index}`} className="grid gap-3 rounded-3xl border border-white/[0.08] bg-white/[0.03] p-3 md:grid-cols-[1fr_1fr_auto]">
              <label className="field-label">ID
                <input className="field-input" value={button.id} onChange={(event) => setButtons((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, id: event.currentTarget.value } : item))} placeholder={`accion_${index + 1}`} />
              </label>
              <label className="field-label">Título
                <input className="field-input" value={button.title} onChange={(event) => setButtons((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, title: event.currentTarget.value } : item))} placeholder="Texto del botón" />
              </label>
              <div className="flex items-end">
                <button type="button" className="secondary-btn w-full" onClick={() => setButtons((value) => value.filter((_, itemIndex) => itemIndex !== index))} disabled={buttons.length <= 1}>Quitar</button>
              </div>
            </div>
          ))}
          {buttons.length < MAX_BUTTONS ? <button type="button" className="secondary-btn" onClick={() => setButtons((value) => [...value, { id: `accion_${value.length + 1}`, title: `Opción ${value.length + 1}` }])}>Agregar botón</button> : null}
        </div>
      </div>
    );
  }

  if (mode === "interactive_list") {
    return (
      <div className="space-y-3">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="field-label md:col-span-2">Texto principal
            <textarea className="field-input min-h-[110px]" value={interactiveBody} onChange={(event) => setInteractiveBody(event.currentTarget.value)} placeholder="¿Qué opción te interesa más?" />
          </label>
          <label className="field-label">Etiqueta del botón
            <input className="field-input" value={listButtonLabel} onChange={(event) => setListButtonLabel(event.currentTarget.value)} placeholder="Ver opciones" />
          </label>
          <label className="field-label">Footer
            <input className="field-input" value={interactiveFooter} onChange={(event) => setInteractiveFooter(event.currentTarget.value)} placeholder="Opcional" />
          </label>
        </div>
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Filas de lista</div>
          <div className="flex gap-2">
            {listRows.length > 1 ? <button type="button" className="secondary-btn" onClick={() => setListRows((value) => value.slice(0, -1))}>Quitar fila</button> : null}
            <button type="button" className="secondary-btn" onClick={() => setListRows((value) => [...value, { section: "Opciones", id: `opcion_${value.length + 1}`, title: `Nueva opción ${value.length + 1}`, description: "" }])}>Agregar fila</button>
          </div>
        </div>
        <div className="space-y-3">
          {listRows.map((row, index) => (
            <div key={`row-${index}`} className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-3">
              <div className="mb-2 flex items-center justify-between gap-3 text-xs uppercase tracking-[0.16em] text-slate-500"><span>Fila {index + 1}</span><span className="mono-pill">list_reply</span></div>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="field-label">Sección
                  <input className="field-input" value={row.section} onChange={(event) => setListRows((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, section: event.currentTarget.value } : item))} placeholder="Opciones" />
                </label>
                <label className="field-label">ID
                  <input className="field-input" value={row.id} onChange={(event) => setListRows((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, id: event.currentTarget.value } : item))} placeholder={`row_${index + 1}`} />
                </label>
                <label className="field-label">Título
                  <input className="field-input" value={row.title} onChange={(event) => setListRows((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, title: event.currentTarget.value } : item))} placeholder="Texto visible" />
                </label>
                <label className="field-label">Descripción
                  <input className="field-input" value={row.description} onChange={(event) => setListRows((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, description: event.currentTarget.value } : item))} placeholder="Opcional" />
                </label>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return null;
}
