import type { WizardMode } from "@/features/bot-studio/domain/wizardTypes";

function HandoffPreviewField({
  label,
  currentValue,
  proposedValue,
  compare,
}: {
  label: string;
  currentValue: string;
  proposedValue: string;
  compare?: boolean;
}) {
  return (
    <div className="rounded-[20px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{label}</div>
      {compare ? (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Actual</div>
            <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)] whitespace-pre-wrap">{currentValue}</p>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Propuesto</div>
            <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)] whitespace-pre-wrap">{proposedValue}</p>
          </div>
        </div>
      ) : (
        <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)] whitespace-pre-wrap">{proposedValue}</p>
      )}
    </div>
  );
}

export function HandoffPreviewCard({
  mode,
  compare,
  current,
  proposed,
  escalateWhenText,
  onEscalateWhenChange,
  handoffKeywordsText,
  onHandoffKeywordsChange,
  handoffSlaText,
  onHandoffSlaChange,
  humanDestinationChannelText,
  onHumanDestinationChannelChange,
  ruleOverridesText,
  onRuleOverridesChange,
  onGoToDryRun,
}: {
  mode: WizardMode;
  compare?: boolean;
  current: {
    escalateWhen: string;
    handoffKeywords: string;
    expectedHandoffSla: string;
    humanDestinationChannel: string;
    ruleOverridesSummary: string;
  };
  proposed: {
    escalateWhen: string;
    handoffKeywords: string;
    expectedHandoffSla: string;
    humanDestinationChannel: string;
    ruleOverridesSummary: string;
  };
  escalateWhenText: string;
  onEscalateWhenChange: (value: string) => void;
  handoffKeywordsText: string;
  onHandoffKeywordsChange: (value: string) => void;
  handoffSlaText: string;
  onHandoffSlaChange: (value: string) => void;
  humanDestinationChannelText: string;
  onHumanDestinationChannelChange: (value: string) => void;
  ruleOverridesText: string;
  onRuleOverridesChange: (value: string) => void;
  onGoToDryRun?: () => void;
}) {
  return (
    <div className="mt-5 rounded-[24px] border border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] p-4" data-testid="handoff-preview-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Pack preview fijo · handoff</div>
          <h4 className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">Reglas de handoff explícitas antes del apply</h4>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">El pack preview ya no deja estas reglas escondidas. Aquí comparas actual vs propuesto y todavía puedes editar antes del apply real.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="mono-pill">Escalar cuando</span>
          <span className="mono-pill">Palabras de handoff</span>
          <span className="mono-pill">SLA esperado</span>
          <span className="mono-pill">Canal humano destino</span>
          <span className="mono-pill">Reglas override</span>
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <HandoffPreviewField label="Escalar cuando" currentValue={current.escalateWhen} proposedValue={proposed.escalateWhen} compare={compare} />
        <HandoffPreviewField label="Palabras de handoff" currentValue={current.handoffKeywords} proposedValue={proposed.handoffKeywords} compare={compare} />
        <HandoffPreviewField label="SLA esperado" currentValue={current.expectedHandoffSla} proposedValue={proposed.expectedHandoffSla} compare={compare} />
        <HandoffPreviewField label="Canal humano destino" currentValue={current.humanDestinationChannel} proposedValue={proposed.humanDestinationChannel} compare={compare} />
        <div className="xl:col-span-2">
          <HandoffPreviewField label="Reglas override" currentValue={current.ruleOverridesSummary} proposedValue={proposed.ruleOverridesSummary} compare={compare} />
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <label className="field-label">Escalar cuando
          <textarea className="field-input min-h-[132px]" value={escalateWhenText} onChange={(event) => onEscalateWhenChange(event.target.value)} placeholder="cliente pide humano
caso urgente
requiere excepción" />
        </label>
        <label className="field-label">Palabras de handoff
          <textarea className="field-input min-h-[132px]" value={handoffKeywordsText} onChange={(event) => onHandoffKeywordsChange(event.target.value)} placeholder="asesor
humano
urgente" />
        </label>
        <label className="field-label">SLA esperado
          <input className="field-input" value={handoffSlaText} onChange={(event) => onHandoffSlaChange(event.target.value)} placeholder="15 minutos" />
        </label>
        <label className="field-label">Canal humano destino
          <input className="field-input" value={humanDestinationChannelText} onChange={(event) => onHumanDestinationChannelChange(event.target.value)} placeholder="Equipo humano / CRM" />
        </label>
        <label className="field-label md:col-span-2">Reglas override
          <textarea className="field-input min-h-[176px] font-mono" value={ruleOverridesText} onChange={(event) => onRuleOverridesChange(event.target.value)} placeholder='{"after_hours": "escalar", "vip": "handoff_inmediato"}' />
        </label>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <span className="mono-pill">Se puede editar antes del apply</span>
        {compare && mode === "reconfigure" ? <span className="mono-pill">Comparación actual vs propuesto activa</span> : null}
        {onGoToDryRun ? <button type="button" className="secondary-btn" onClick={onGoToDryRun}>Guardar cambios y volver al dry run</button> : null}
      </div>
    </div>
  );
}
