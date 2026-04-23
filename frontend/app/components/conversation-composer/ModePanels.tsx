import type { ConversationComposerState } from "./useConversationComposerState";
import { ConversationComposerBasicModePanel } from "./modes/BasicModePanels";
import { ConversationComposerCommerceModePanel } from "./modes/CommerceModePanel";
import { ConversationComposerFlowModePanel } from "./modes/FlowModePanel";
import { ConversationComposerInteractiveModePanel } from "./modes/InteractiveModePanel";
import { ConversationComposerMarkAsReadModePanel } from "./modes/MarkAsReadModePanel";
import { ConversationComposerMediaModePanel } from "./modes/MediaModePanel";

export function ConversationComposerModePanels({ state }: { state: ConversationComposerState }) {
  return (
    <>
      <ConversationComposerBasicModePanel state={state} />
      <ConversationComposerMediaModePanel state={state} />
      <ConversationComposerInteractiveModePanel state={state} />
      <ConversationComposerFlowModePanel state={state} />
      <ConversationComposerCommerceModePanel state={state} />
      <ConversationComposerMarkAsReadModePanel state={state} />
    </>
  );
}
