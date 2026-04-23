import { safeText } from "../../../app/lib/ui";
import type {
  WizardDryRunDomain,
  WizardMode,
  WizardValidationSnapshot,
} from "../../../app/bot-studio/wizard-types";

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function diffStatusMeta(status: "replace" | "keep" | "suggest" | "add" | "remove" | undefined) {
  switch (status) {
    case "replace":
      return { pill: "se reemplaza", tone: "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] text-[color:var(--warning-text)]" };
    case "keep":
      return { pill: "se conserva", tone: "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success-text)]" };
    case "add":
      return { pill: "se agrega", tone: "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] text-[color:var(--text-primary)]" };
    case "remove":
      return { pill: "se elimina", tone: "border-[color:var(--danger-border)] bg-[color:var(--danger-soft)] text-[color:var(--danger-text)]" };
    default:
      return { pill: "se sugiere", tone: "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-secondary)]" };
  }
}

function validationStatusMeta(status: "green" | "yellow" | "red" | string | undefined) {
  switch (status) {
    case "green":
      return { pill: "verde", tone: "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success-text)]" };
    case "yellow":
      return { pill: "amarillo", tone: "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] text-[color:var(--warning-text)]" };
    default:
      return { pill: "rojo", tone: "border-[color:var(--danger-border)] bg-[color:var(--danger-soft)] text-[color:var(--danger-text)]" };
  }
}

function SummaryList({ items, fallback }: { items: string[]; fallback: string }) {
  const visible = unique(items).slice(0, 5);
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {visible.length
        ? visible.map((item) => <span key={item} className="mono-pill">{item}</span>)
        : <span className="text-sm leading-6 text-[color:var(--text-secondary)]">{fallback}</span>}
    </div>
  );
}

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

export function ValidationSnapshotPanel({
  title,
  description,
  snapshot,
}: {
  title: string;
  description: string;
  snapshot: WizardValidationSnapshot | null;
}) {
  if (!snapshot) return null;
  const gate = snapshot.gate || {};
  const gateMeta = validationStatusMeta(gate.status);
  const counts = snapshot.counts || {};
  const simulation = snapshot.simulation_result || {};
  const checklist = Array.isArray(snapshot.checklist) ? snapshot.checklist : [];
  const coveredItems = checklist
    .filter((item) => item.status === "green")
    .map((item) => safeText(item.label, safeText(item.key, "")))
    .filter(Boolean);
  const missingItems = checklist
    .filter((item) => item.status === "yellow" || item.status === "red")
    .map((item) => safeText(item.label, safeText(item.key, "")))
    .filter(Boolean);
  return (
    <div className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Checklist formal de salida</div>
          <h4 className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">{title}</h4>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${gateMeta.tone}`}>{gateMeta.pill}</span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Puerta de salida</div>
          <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{safeText(gate.label, "Sin estado")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(gate.detail, "Sin detalle adicional.")}</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Verde</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.green || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Checks listos para operar.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Amarillo</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.yellow || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Todavía requieren atención.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Rojo</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.red || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Bloqueos visibles antes de publish.</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Señales cubiertas</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(coveredItems.length), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Lo que ya quedó resuelto por el draft actual.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Faltantes</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(missingItems.length), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Todavía no aparecen en el draft operativo.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Simulación</div>
          <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{simulation.approved ? "Aprobada" : safeText(String(simulation.status || "pendiente"), "pendiente")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Pass rate: {safeText(String(simulation.pass_rate ?? 0), "0")}% · casos: {safeText(String(simulation.cases_total ?? 0), "0")}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Señales cubiertas</div>
          <SummaryList items={coveredItems} fallback="Sin cobertura visible todavía." />
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Faltantes</div>
          <SummaryList items={missingItems} fallback="Sin faltantes visibles." />
        </div>
      </div>
    </div>
  );
}

export function VerticalScorecardPanel({
  title,
  description,
  snapshot,
}: {
  title: string;
  description: string;
  snapshot: WizardValidationSnapshot | null;
}) {
  const scorecard = snapshot?.scorecard;
  if (!scorecard) return null;
  const meta = validationStatusMeta(scorecard.status);
  const counts = scorecard.counts || {};
  return (
    <div className="mt-5 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{title}</div>
          <div className="mt-2 text-base font-semibold text-[color:var(--text-primary)]">{safeText(scorecard.label, "Vertical")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${meta.tone}`}>{meta.pill}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(scorecard.summary, "Sin scorecard visible.")}</p>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Verde</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.green || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Señales de negocio cubiertas.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Amarillo</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.yellow || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Requieren refuerzo antes de publish.</p>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Rojo</div>
          <div className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{safeText(String(counts.red || 0), "0")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Bloquean o debilitan el go-live.</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {(scorecard.items || []).map((item, index) => {
          const itemMeta = validationStatusMeta(item.status);
          const covered = Array.isArray(item.covered_signals) ? item.covered_signals.filter(Boolean) : [];
          const missing = Array.isArray(item.missing_signals) ? item.missing_signals.filter(Boolean) : [];
          return (
            <div key={safeText(item.key || item.label, `scorecard-${index}`)} className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="text-sm font-semibold text-[color:var(--text-primary)]">{safeText(item.label, "Señal")}</div>
                <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${itemMeta.tone}`}>{itemMeta.pill}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(item.detail, "Sin detalle adicional.")}</p>
              {covered.length ? <p className="mt-3 text-xs leading-5 text-[color:var(--success-text)]">Cubre: {covered.join(" · ")}</p> : null}
              {missing.length ? <p className="mt-2 text-xs leading-5 text-[color:var(--warning-text)]">Falta: {missing.join(" · ")}</p> : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function DiffCard({ title, before, after, status, detail }: { title: string; before: string; after: string; status: "replace" | "keep" | "suggest" | "add" | "remove"; detail: string }) {
  const meta = diffStatusMeta(status);
  return (
    <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="text-base font-semibold text-[color:var(--text-primary)]">{title}</div>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${meta.tone}`}>{meta.pill}</span>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Antes</div>
          <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{before}</p>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Después</div>
          <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{after}</p>
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{detail}</p>
    </div>
  );
}

export function OperationalDiffDomainCard({ block }: { block: WizardDryRunDomain }) {
  const meta = diffStatusMeta(block.status);
  const counters = block.counters || {};
  const items = block.items || [];
  return (
    <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-base font-semibold text-[color:var(--text-primary)]">{safeText(block.label, "Dominio")}</div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(block.detail, "Sin detalle adicional.")}</p>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${meta.tone}`}>{meta.pill}</span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {(block.badges?.length
          ? block.badges
          : [
            counters.added ? `+${counters.added} cambios` : "",
            counters.removed ? `-${counters.removed} cambios` : "",
            counters.replaced ? `reemplaza ${counters.replaced}` : "",
          ].filter(Boolean)
        ).slice(0, 6).map((badge) => (
          <span key={badge} className="mono-pill">{badge}</span>
        ))}
        {!block.badges?.length && !counters.added && !counters.removed && !counters.replaced ? <span className="mono-pill">Sin cambio material visible</span> : null}
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-4">
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-2 text-sm text-[color:var(--text-secondary)]">Se conserva <strong className="text-[color:var(--text-primary)]">{safeText(String(counters.kept || 0), "0")}</strong></div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-2 text-sm text-[color:var(--text-secondary)]">Se reemplaza <strong className="text-[color:var(--text-primary)]">{safeText(String(counters.replaced || 0), "0")}</strong></div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-2 text-sm text-[color:var(--text-secondary)]">Se agrega <strong className="text-[color:var(--text-primary)]">{safeText(String(counters.added || 0), "0")}</strong></div>
        <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-2 text-sm text-[color:var(--text-secondary)]">Se elimina <strong className="text-[color:var(--text-primary)]">{safeText(String(counters.removed || 0), "0")}</strong></div>
      </div>

      <div className="mt-4 grid gap-3">
        {items.map((item, index) => {
          const itemMeta = diffStatusMeta(item.status);
          return (
            <div key={safeText(item.key || item.label, `domain-item-${index}`)} className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="text-sm font-semibold text-[color:var(--text-primary)]">{safeText(item.label, "Cambio")}</div>
                <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${itemMeta.tone}`}>{itemMeta.pill}</span>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Antes</div>
                  <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(item.before, "Sin valor previo")}</p>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Después</div>
                  <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(item.after, "Sin valor propuesto")}</p>
                </div>
              </div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{safeText(item.detail, "Sin detalle adicional.")}</p>
            </div>
          );
        })}
      </div>
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

export function PackPreviewBlock({
  eyebrow,
  title,
  description,
  createItems,
  reuseItems,
  pendingItems,
  createLabel = "Qué se crea",
  reuseLabel = "Qué se reusa",
  pendingLabel = "Qué queda pendiente",
  pendingFallback = "Nada pendiente por cerrar en este bloque.",
}: {
  eyebrow: string;
  title: string;
  description: string;
  createItems: string[];
  reuseItems: string[];
  pendingItems: string[];
  createLabel?: string;
  reuseLabel?: string;
  pendingLabel?: string;
  pendingFallback?: string;
}) {
  return (
    <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{eyebrow}</div>
      <h4 className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">{title}</h4>
      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{description}</p>

      <div className="mt-4 grid gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{createLabel} ({createItems.length})</div>
          <SummaryList items={createItems} fallback="No hay creación nueva visible en este bloque." />
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{reuseLabel} ({reuseItems.length})</div>
          <SummaryList items={reuseItems} fallback="No se reusa nada visible del estado actual." />
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{pendingLabel} ({pendingItems.length})</div>
          <SummaryList items={pendingItems} fallback={pendingFallback} />
        </div>
      </div>
    </div>
  );
}

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
