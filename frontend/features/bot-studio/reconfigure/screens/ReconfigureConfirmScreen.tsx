"use client";

import { safeText } from "@/app/lib/ui";
import { FieldGroup, SummaryCard } from "@/features/bot-studio/ui/flowUi";
import type { ReconfigureValidationViewModel } from "../reconfigureScreenTypes";

export function ReconfigureConfirmScreen({ viewModel: state }: { viewModel: ReconfigureValidationViewModel }) {
  const snapshot = state.validationSnapshot || state.wizard?.validation_snapshot || null;
  return (
    <FieldGroup testId="confirm-step" title="Confirma la reconfiguración" description="Confirmar es su propia pantalla.">
      <div className="grid gap-4 lg:grid-cols-3">
        <SummaryCard title="Bot" tone="accent">{safeText(state.selectedBot?.name, "Sin bot")}</SummaryCard>
        <SummaryCard title="Gate de salida" tone={snapshot?.gate?.status === "green" ? "success" : "warning"}>{safeText(snapshot?.gate?.detail, "Sin detalle")}</SummaryCard>
        <SummaryCard title="Wizard">{safeText(state.wizard?.id, "Sin wizard")}</SummaryCard>
      </div>
    </FieldGroup>
  );
}
