"use client";

import { ChecklistChips, FieldGroup, InputField, TextAreaField } from "@/features/bot-studio/ui/flowUi";
import { recommendedIntegrations } from "../createScreenHelpers";
import type { CreateIntegrationsActions, CreateIntegrationsViewModel } from "../createScreenTypes";

export function CreateIntegrationsScreen({ viewModel: state, actions: handlers }: { viewModel: CreateIntegrationsViewModel; actions: CreateIntegrationsActions }) {
  const options = recommendedIntegrations(state);
  return (
    <FieldGroup testId="create-integrations-step" title="Configura integraciones y reglas operativas" description="Aquí solo decides qué sistemas toca el bot y cuándo debe escalar.">
      {options.length ? (
        <ChecklistChips
          label="Integraciones recomendadas"
          options={options}
          selected={state.selectedIntegrationKeys}
          onToggle={(value) => handlers.setSelectedIntegrationKeys((prev) => prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value])}
        />
      ) : null}
      <TextAreaField testId="escalate-when-textarea" label="Escalar cuando" value={state.escalateWhenText} onChange={handlers.setEscalateWhenText} />
      <TextAreaField testId="handoff-keywords-textarea" label="Palabras clave de handoff" value={state.handoffKeywordsText} onChange={handlers.setHandoffKeywordsText} rows={4} />
      <div className="grid gap-4 lg:grid-cols-2">
        <InputField testId="handoff-sla-input" label="SLA de handoff" value={state.handoffSlaText} onChange={handlers.setHandoffSlaText} />
        <InputField testId="human-destination-input" label="Destino humano" value={state.humanDestinationChannelText} onChange={handlers.setHumanDestinationChannelText} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <TextAreaField testId="can-say-textarea" label="Puede decir" value={state.canSayText} onChange={handlers.setCanSayText} rows={5} />
        <TextAreaField testId="cannot-say-textarea" label="No puede decir" value={state.cannotSayText} onChange={handlers.setCannotSayText} rows={5} />
      </div>
      <TextAreaField testId="rule-overrides-textarea" label="Overrides avanzados" value={state.ruleOverridesText} onChange={handlers.setRuleOverridesText} rows={6} />
    </FieldGroup>
  );
}
