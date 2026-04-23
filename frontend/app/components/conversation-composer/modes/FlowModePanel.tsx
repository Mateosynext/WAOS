import type { ConversationComposerState } from "../useConversationComposerState";

export function ConversationComposerFlowModePanel({ state }: { state: ConversationComposerState }) {
  const { mode, flowId, setFlowId, flowToken, setFlowToken, flowCta, setFlowCta, flowBody, setFlowBody, flowFooter, setFlowFooter } = state;

  if (mode !== "flow_entrypoint") {
    return null;
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      <label className="field-label">Flow ID
        <input className="field-input" value={flowId} onChange={(event) => setFlowId(event.currentTarget.value)} placeholder="flow-123" />
      </label>
      <label className="field-label">Flow token
        <input className="field-input" value={flowToken} onChange={(event) => setFlowToken(event.currentTarget.value)} placeholder="token opcional" />
      </label>
      <label className="field-label">CTA
        <input className="field-input" value={flowCta} onChange={(event) => setFlowCta(event.currentTarget.value)} placeholder="Abrir flujo" />
      </label>
      <label className="field-label">Footer
        <input className="field-input" value={flowFooter} onChange={(event) => setFlowFooter(event.currentTarget.value)} placeholder="Opcional" />
      </label>
      <label className="field-label md:col-span-2">Texto principal
        <textarea className="field-input min-h-[110px]" value={flowBody} onChange={(event) => setFlowBody(event.currentTarget.value)} placeholder="Completa tu pre-registro" />
      </label>
    </div>
  );
}
