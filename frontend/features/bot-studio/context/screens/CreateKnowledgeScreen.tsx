"use client";

import { FieldGroup, TextAreaField } from "@/features/bot-studio/ui/flowUi";
import type { CreateKnowledgeActions, CreateKnowledgeViewModel } from "../createScreenTypes";

export function CreateKnowledgeScreen({ viewModel: state, actions: handlers }: { viewModel: CreateKnowledgeViewModel; actions: CreateKnowledgeActions }) {
  return (
    <FieldGroup testId="create-knowledge-step" title="Separa el knowledge del bot" description="FAQs, políticas y fuentes viven en esta pantalla.">
      <TextAreaField testId="faq-textarea" label="FAQs" hint="Formato: pregunta | respuesta" value={state.faqText} onChange={handlers.setFaqText} rows={8} />
      <TextAreaField testId="policies-textarea" label="Políticas" value={state.policiesText} onChange={handlers.setPoliciesText} />
      <TextAreaField testId="knowledge-sources-textarea" label="Fuentes de conocimiento" value={state.knowledgeSourcesText} onChange={handlers.setKnowledgeSourcesText} />
    </FieldGroup>
  );
}
