import { safeText } from "@/app/lib/ui";
import { SummaryCard } from "@/features/bot-studio/ui/flowUi";

export function WizardReviewSummary({
  industry,
  subvertical,
  objective,
  services,
  policies,
  integrations,
}: {
  industry: string;
  subvertical: string;
  objective: string;
  services: string[];
  policies: string[];
  integrations: string[];
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-2" data-testid="wizard-review-summary">
      <SummaryCard title="Contexto" tone="accent">{safeText(industry, "Sin industria")} · {subvertical || "Sin subvertical"} · objetivo {objective || "sin objetivo"}</SummaryCard>
      <SummaryCard title="Oferta">{services.slice(0, 4).join(" · ") || "Sin servicios visibles"}</SummaryCard>
      <SummaryCard title="Knowledge">{policies.slice(0, 4).join(" · ") || "Sin políticas visibles"}</SummaryCard>
      <SummaryCard title="Integraciones">{integrations.join(" · ") || "Sin integraciones seleccionadas"}</SummaryCard>
    </div>
  );
}
