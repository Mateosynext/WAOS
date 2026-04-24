"use client";

import { safeText } from "@/app/lib/ui";
import { FieldGroup, SummaryCard } from "@/features/bot-studio/ui/flowUi";
import type { CreateApplyViewModel } from "../createScreenTypes";

export function CreateApplyScreen({ viewModel: state }: { viewModel: CreateApplyViewModel }) {
  const snapshot = state.validationSnapshot || state.wizard?.validation_snapshot || null;
  return (
    <div className="grid gap-6" data-testid="apply-step">
      <FieldGroup title="Confirma el apply" description="Aquí solo decides si aplicar el draft validado.">
        <div className="grid gap-4 lg:grid-cols-3">
          <SummaryCard title="Wizard" tone="accent">{safeText(state.wizard?.id, "Sin wizard")}</SummaryCard>
          <SummaryCard title="Gate de validación" tone={snapshot?.gate?.status === "green" ? "success" : "warning"}>{safeText(snapshot?.gate?.detail, "Revisa la validación antes de aplicar.")}</SummaryCard>
          <SummaryCard title="Knowledge autopublish">{state.autopublishKnowledge ? "Sí" : "No"}</SummaryCard>
        </div>
      </FieldGroup>
    </div>
  );
}
