import { safeText } from "@/shared/lib/ui";
import type { WizardMode } from "@/features/bot-studio/domain/wizardTypes";
import { SummaryList } from "./reviewUtils";

export function StickySummaryRail({
  mode,
  organizationName,
  industry,
  operationType,
  objective,
  businessName,
  assistantName,
  recommendedChannels,
  seededServices,
  createdTemplates,
  readinessScore,
  readinessLabel,
  readinessTone,
  risks,
}: {
  mode: WizardMode;
  organizationName: string;
  industry: string;
  operationType: string;
  objective: string;
  businessName: string;
  assistantName: string;
  recommendedChannels: string[];
  seededServices: string[];
  createdTemplates: string[];
  readinessScore: number;
  readinessLabel: string;
  readinessTone: "success" | "warning" | "danger";
  risks: string[];
}) {
  const readinessClasses = readinessTone === "success"
    ? "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success-text)]"
    : readinessTone === "warning"
      ? "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] text-[color:var(--warning-text)]"
      : "border-[color:var(--danger-border)] bg-[color:var(--danger-soft)] text-[color:var(--danger-text)]";

  return (
    <div className="sticky top-6 grid gap-6 self-start" data-testid="sticky-summary-rail">
      <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Resumen vivo del draft</div>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">Sticky summary rail</h3>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">La configuración generada ya se siente real porque el resumen se actualiza mientras avanzas por el wizard.</p>
          </div>
          <span className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${readinessClasses}`}>{readinessLabel}</span>
        </div>

        <div className="mt-5 grid gap-3">
          <div className="surface-row" data-testid="summary-organization"><span>Organización</span><strong>{safeText(organizationName, "Pendiente")}</strong></div>
          <div className="surface-row" data-testid="summary-industry"><span>Industria</span><strong>{safeText(industry, "Pendiente")}</strong></div>
          <div className="surface-row" data-testid="summary-operation"><span>Tipo de operación</span><strong>{safeText(operationType, "Pendiente")}</strong></div>
          <div className="surface-row" data-testid="summary-objective"><span>Objetivo</span><strong>{safeText(objective, "Pendiente")}</strong></div>
          <div className="surface-row" data-testid="summary-business-name"><span>Nombre del negocio</span><strong>{safeText(businessName, mode === "create" ? "Pendiente" : "Se conserva el actual")}</strong></div>
          <div className="surface-row" data-testid="summary-assistant-name"><span>Asistente operativo</span><strong>{safeText(assistantName, mode === "create" ? "Pendiente" : "Pendiente de elegir")}</strong></div>
          <div className="surface-row"><span>Readiness del draft</span><strong>{readinessScore}%</strong></div>
        </div>

        <div className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Canales recomendados</div>
          <SummaryList items={recommendedChannels} fallback="Aún no hay canales sugeridos visibles." />
        </div>
        <div className="mt-4 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Servicios semilla</div>
          <SummaryList items={seededServices} fallback="Todavía no hay servicios semilla visibles." />
        </div>
        <div className="mt-4 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Templates que se van a crear</div>
          <SummaryList items={createdTemplates} fallback="Todavía no hay templates visibles." />
        </div>
        <div className="mt-4 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Riesgos y faltantes</div>
          <SummaryList items={risks} fallback="No hay riesgos bloqueantes visibles." />
        </div>
      </div>
    </div>
  );
}
