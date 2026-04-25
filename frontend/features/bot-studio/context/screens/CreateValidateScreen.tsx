"use client";

import { useState } from "react";
import { safeText } from "@/app/lib/ui";
import { ValidationSnapshotPanel } from "@/features/bot-studio/review/ValidationSnapshotPanel";
import { VerticalScorecardPanel } from "@/features/bot-studio/review/VerticalScorecardPanel";
import { FieldGroup, SummaryCard } from "@/features/bot-studio/ui/flowUi";
import type { CreateValidationActions, CreateValidationViewModel } from "../createScreenTypes";

export function CreateValidateScreen({ viewModel: state, actions }: { viewModel: CreateValidationViewModel; actions: CreateValidationActions }) {
  const snapshot = state.validationSnapshot || state.wizard?.validation_snapshot || null;
  const [aiFixing, setAiFixing] = useState(false);
  const [aiFixError, setAiFixError] = useState("");
  const [aiFixSummary, setAiFixSummary] = useState("");

  const handleAiAutofix = async () => {
    setAiFixing(true);
    setAiFixError("");
    setAiFixSummary("");
    try {
      const result = await actions.autofixWithAi();
      const dryRun = result.dry_run_result && typeof result.dry_run_result === "object" ? result.dry_run_result as Record<string, unknown> : result;
      const drySummary = dryRun.summary && typeof dryRun.summary === "object" ? dryRun.summary as Record<string, unknown> : {};
      setAiFixSummary(String(result.summary || drySummary.status || "La IA aplicó un patch y volvió a correr el dry run."));
    } catch (error) {
      setAiFixError(error instanceof Error ? error.message : "No se pudo arreglar el wizard con IA.");
    } finally {
      setAiFixing(false);
    }
  };

  return (
    <div className="grid gap-6" data-testid="validate-step">
      <FieldGroup title="Valida antes de aplicar" description="La decisión de esta pantalla es simple: ver si el draft está listo o si debe regresar a un paso anterior.">
        <div className="grid gap-4 lg:grid-cols-3">
          <SummaryCard title="Wizard">{safeText(state.wizard?.id, "Sin wizard")}</SummaryCard>
          <SummaryCard title="Gate" tone={snapshot?.gate?.status === "green" ? "success" : snapshot?.gate?.status === "yellow" ? "warning" : "default"}>{safeText(snapshot?.gate?.label, "Pendiente de validación")}</SummaryCard>
          <SummaryCard title="Dry run">{safeText(state.dryRunResult?.summary?.status || snapshot?.simulation_result?.status, "Aún no corre")}</SummaryCard>
        </div>
        <div className="rounded-[24px] border border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-sm font-semibold text-[color:var(--text-primary)]">Autofix en validación</div>
              <p className="mt-1 text-xs leading-5 text-[color:var(--text-secondary)]">Si el dry run falla por subvertical, catalog, knowledge, integrations o handoff, la IA propone y aplica un patch seguro; después vuelve a validar.</p>
            </div>
            <button type="button" className="primary-btn" disabled={aiFixing || !state.wizard?.id} onClick={handleAiAutofix}>
              {aiFixing ? "Arreglando..." : "Arreglar pendientes con IA"}
            </button>
          </div>
          {aiFixSummary ? <p className="mt-3 text-sm text-[color:var(--success-text)]">{aiFixSummary}</p> : null}
          {aiFixError ? <p className="mt-3 text-sm text-[color:var(--warning-text)]">{aiFixError}</p> : null}
        </div>
      </FieldGroup>
      <ValidationSnapshotPanel title="Checklist de salida" description="Esta lectura ya no compite con edición ni confirmación." snapshot={snapshot} />
      <VerticalScorecardPanel title="Cobertura por vertical" description="Señales visibles para saber si el setup cubre la vertical elegida." snapshot={snapshot} />
    </div>
  );
}
