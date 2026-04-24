"use client";

import { safeText } from "@/app/lib/ui";
import { ValidationSnapshotPanel } from "@/features/bot-studio/review/ValidationSnapshotPanel";
import { VerticalScorecardPanel } from "@/features/bot-studio/review/VerticalScorecardPanel";
import { FieldGroup, SummaryCard } from "@/features/bot-studio/ui/flowUi";
import type { ReconfigureValidationViewModel } from "../reconfigureScreenTypes";

export function ReconfigureDryRunScreen({ viewModel: state }: { viewModel: ReconfigureValidationViewModel }) {
  const snapshot = state.validationSnapshot || state.wizard?.validation_snapshot || null;
  return (
    <div className="grid gap-6" data-testid="dry-run-step">
      <FieldGroup title="Corre el dry run" description="Esta pantalla existe solo para validar impacto.">
        <div className="grid gap-4 lg:grid-cols-3">
          <SummaryCard title="Bot">{safeText(state.selectedBot?.name, "Sin bot")}</SummaryCard>
          <SummaryCard title="Dry run">{safeText(state.dryRunResult?.summary?.status || snapshot?.simulation_result?.status, "Pendiente")}</SummaryCard>
          <SummaryCard title="Gate">{safeText(snapshot?.gate?.label, "Sin gate visible")}</SummaryCard>
        </div>
      </FieldGroup>
      <ValidationSnapshotPanel title="Checklist de reconfiguración" description="La validación vive sola aquí." snapshot={snapshot} />
      <VerticalScorecardPanel title="Cobertura del cambio" description="Lectura de señales para no aplicar una reconfiguración a ciegas." snapshot={snapshot} />
    </div>
  );
}
