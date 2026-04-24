import type { WizardError } from "../domain/wizardTypes";
import { wizardErrorToMessage } from "../services/wizardClient";

type WizardErrorPanelProps = {
  error?: WizardError | string | null;
  context?: "validate" | "apply" | "dry-run" | "confirm" | "result";
};

function titleFor(context: WizardErrorPanelProps["context"]) {
  if (context === "validate" || context === "dry-run") return "Validacion bloqueada";
  if (context === "apply" || context === "confirm") return "Apply bloqueado";
  if (context === "result") return "Resultado con advertencias";
  return "Error del wizard";
}

export function WizardErrorPanel({ error, context }: WizardErrorPanelProps) {
  if (!error) return null;
  const message = typeof error === "string" ? error : wizardErrorToMessage(error);
  return (
    <div className="rounded-[24px] border border-rose-400/[0.22] bg-rose-400/[0.10] p-4 text-sm text-rose-50" data-testid="wizard-error-panel">
      <div className="font-semibold text-white">{titleFor(context)}</div>
      <p className="mt-2 leading-6">{message}</p>
      {typeof error !== "string" && error.type === "revision_conflict" ? <p className="mt-2 text-xs text-rose-100">Revision servidor: {error.serverRevision}</p> : null}
      {typeof error !== "string" && error.type === "partial_failure" ? <p className="mt-2 text-xs text-rose-100">Completado: {error.completed.join(", ") || "-"}. Fallido: {error.failed.join(", ") || "-"}.</p> : null}
    </div>
  );
}
