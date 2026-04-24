"use client";

import { safeText } from "@/shared/lib/ui";
import { ChecklistChips, FieldGroup, SummaryCard, TextAreaField } from "@/features/bot-studio/ui/flowUi";
import { WizardReviewSummary } from "@/features/bot-studio/review/WizardReviewSummary";
import { lines, recommendedPlaybooks } from "../createScreenHelpers";
import type { CreateReviewActions, CreateReviewViewModel } from "../createScreenTypes";

export function CreateReviewScreen({ viewModel: state, actions: handlers }: { viewModel: CreateReviewViewModel; actions: CreateReviewActions }) {
  const options = recommendedPlaybooks(state);
  return (
    <div className="grid gap-6" data-testid="create-review-step">
      <FieldGroup title="Revisa el setup antes de validar" description="Esta pantalla resume el draft y te deja decidir si está listo para validar.">
        {options.length ? (
          <ChecklistChips
            label="Playbooks sugeridos"
            options={options}
            selected={state.selectedPlaybookKeys}
            onToggle={(value) => handlers.setSelectedPlaybookKeys((prev) => prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value])}
          />
        ) : null}
        <TextAreaField testId="launch-notes-textarea" label="Notas de lanzamiento" value={state.launchNotesText} onChange={handlers.setLaunchNotesText} rows={5} />
        <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <label className="flex items-center gap-3 text-sm text-[color:var(--text-primary)]">
            <input data-testid="autopublish-knowledge-checkbox" type="checkbox" checked={state.autopublishKnowledge} onChange={() => handlers.setAutopublishKnowledge((prev) => !prev)} />
            Autopublicar knowledge al aplicar
          </label>
        </div>
      </FieldGroup>

      <WizardReviewSummary
        industry={safeText(state.verticals.find((item) => item.id === state.selectedVerticalId)?.name, "Sin industria")}
        subvertical={state.selectedSubvertical}
        objective={state.selectedPrimaryObjective}
        services={lines(state.servicesText)}
        policies={lines(state.policiesText)}
        integrations={state.selectedIntegrationKeys}
      />
      <SummaryCard title="Notas de lanzamiento">{state.launchNotesText || "Sin notas visibles"}</SummaryCard>
    </div>
  );
}
