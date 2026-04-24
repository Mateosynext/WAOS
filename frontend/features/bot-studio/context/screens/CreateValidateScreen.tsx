"use client";

import { safeText } from "@/shared/lib/ui";
import { ValidationSnapshotPanel } from "@/features/bot-studio/review/ValidationSnapshotPanel";
import { VerticalScorecardPanel } from "@/features/bot-studio/review/VerticalScorecardPanel";
import { FieldGroup, SummaryCard } from "@/features/bot-studio/ui/flowUi";
import { WizardErrorPanel } from "@/features/bot-studio/ui/WizardErrorPanel";
import type { CreateValidationViewModel } from "../createScreenTypes";

export function CreateValidateScreen({ viewModel: state }: { viewModel: CreateValidationViewModel }) {
  const snapshot = state.validationSnapshot || state.wizard?.validation_snapshot || null;
  return (
    <div className="grid gap-6" data-testid="validate-step">
      <FieldGroup title="Valida antes de aplicar" description="La decisión de esta pantalla es simple: ver si el draft está listo o si debe regresar a un paso anterior.">
        <div className="grid gap-4 lg:grid-cols-3">
          <SummaryCard title="Wizard">{safeText(state.wizard?.id, "Sin wizard")}</SummaryCard>
          <SummaryCard title="Gate" tone={snapshot?.gate?.status === "green" ? "success" : snapshot?.gate?.status === "yellow" ? "warning" : "default"}>{safeText(snapshot?.gate?.label, "Pendiente de validación")}</SummaryCard>
          <SummaryCard title="Dry run">{safeText(state.dryRunResult?.summary?.status || snapshot?.simulation_result?.status, "Aún no corre")}</SummaryCard>
        </div>
      </FieldGroup>
      <WizardErrorPanel error={state.wizardError} context="validate" />
      <ValidationSnapshotPanel title="Checklist de salida" description="Esta lectura ya no compite con edición ni confirmación." snapshot={snapshot} />
      <VerticalScorecardPanel title="Cobertura por vertical" description="Señales visibles para saber si el setup cubre la vertical elegida." snapshot={snapshot} />
    </div>
  );
}
