import type { ConversationComposerState } from "../useConversationComposerState";

const MEDIA_MODES = new Set(["image", "audio", "document", "video"]);

export function ConversationComposerMediaModePanel({ state }: { state: ConversationComposerState }) {
  const {
    mode,
    mediaSourceType,
    setMediaSourceType,
    mediaRef,
    setMediaRef,
    mediaCaption,
    setMediaCaption,
    mediaFilename,
    setMediaFilename,
  } = state;

  if (!MEDIA_MODES.has(mode)) {
    return null;
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      <label className="field-label">Origen del media
        <select className="field-input" value={mediaSourceType} onChange={(event) => setMediaSourceType(event.currentTarget.value as "link" | "id") }>
          <option value="link">Link</option>
          <option value="id">Media ID</option>
        </select>
      </label>
      <label className="field-label">{mediaSourceType === "link" ? "URL del media" : "Media ID"}
        <input className="field-input" value={mediaRef} onChange={(event) => setMediaRef(event.currentTarget.value)} placeholder={mediaSourceType === "link" ? "https://..." : "media-123"} />
      </label>
      <label className="field-label md:col-span-2">Caption / resumen
        <textarea className="field-input min-h-[110px]" value={mediaCaption} onChange={(event) => setMediaCaption(event.currentTarget.value)} placeholder="Texto visible o resumen del adjunto" />
      </label>
      {mode === "document" ? (
        <label className="field-label md:col-span-2">Nombre de archivo
          <input className="field-input" value={mediaFilename} onChange={(event) => setMediaFilename(event.currentTarget.value)} placeholder="cotizacion.pdf" />
        </label>
      ) : null}
    </div>
  );
}
