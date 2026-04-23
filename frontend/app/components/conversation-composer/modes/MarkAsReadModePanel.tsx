import type { ConversationComposerState } from "../useConversationComposerState";

export function ConversationComposerMarkAsReadModePanel({ state }: { state: ConversationComposerState }) {
  const { mode, markAsReadTarget, setMarkAsReadTarget } = state;

  if (mode !== "mark_as_read") {
    return null;
  }

  return (
    <label className="field-label">Message ID a marcar como leído
      <input className="field-input" value={markAsReadTarget} onChange={(event) => setMarkAsReadTarget(event.currentTarget.value)} placeholder="wamid.HBg..." />
    </label>
  );
}
