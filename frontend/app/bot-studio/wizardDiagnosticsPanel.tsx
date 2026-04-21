import type { WizardAutosaveMetrics, WizardTimelineEvent } from "./wizardEnterpriseGuards";
import type { WizardMode, WizardInstance } from "./wizard-types";
import type { WizardUiActiveStep } from "./wizardStepFlow";

type DirtyStepItem = {
  stepKey: string;
  clientFingerprint: string;
  serverFingerprint: string | null;
};

type Props = {
  mode: WizardMode;
  activeStep: WizardUiActiveStep;
  allowedStep: WizardUiActiveStep;
  wizard: WizardInstance | null;
  autosaveState: string;
  wizardError: string;
  dirtySteps: DirtyStepItem[];
  timelineEvents: WizardTimelineEvent[];
  autosaveMetrics: WizardAutosaveMetrics;
  onRefresh?: () => void;
  onCopy?: () => void;
  copyFeedback?: string;
};

function safeText(value: unknown, fallback = ""): string {
  const rendered = String(value || "").trim();
  return rendered || fallback;
}

function formatTs(value: unknown): string {
  const rendered = safeText(value);
  if (!rendered) return "—";
  const parsed = Date.parse(rendered);
  if (!Number.isFinite(parsed)) return rendered;
  return new Date(parsed).toLocaleString("es-MX", { hour: "2-digit", minute: "2-digit", second: "2-digit", day: "2-digit", month: "2-digit" });
}

function StatusPill({ label, tone = "neutral" }: { label: string; tone?: "neutral" | "success" | "warning" | "danger" }) {
  const className = tone === "success"
    ? "border-emerald-300 bg-emerald-50 text-emerald-700"
    : tone === "warning"
      ? "border-amber-300 bg-amber-50 text-amber-700"
      : tone === "danger"
        ? "border-rose-300 bg-rose-50 text-rose-700"
        : "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-secondary)]";
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium ${className}`}>{label}</span>;
}

export default function WizardDiagnosticsPanel({
  mode,
  activeStep,
  allowedStep,
  wizard,
  autosaveState,
  wizardError,
  dirtySteps,
  timelineEvents,
  autosaveMetrics,
  onRefresh,
  onCopy,
  copyFeedback,
}: Props) {
  const backendDiagnostics = wizard?.diagnostics as Record<string, unknown> | undefined;
  const backendEvents = Array.isArray(wizard?.event_log) ? wizard?.event_log.slice(-8).reverse() : [];
  const clientEvents = timelineEvents.slice(-12).reverse();
  const pendingSteps = Array.isArray(backendDiagnostics?.required_steps_pending) ? backendDiagnostics?.required_steps_pending as string[] : [];
  const gateStatus = safeText(wizard?.validation_snapshot?.gate?.status).toLowerCase();
  const gateTone = gateStatus === "green" ? "success" : gateStatus === "yellow" ? "warning" : gateStatus === "red" ? "danger" : "neutral";
  const integrityMismatch = Boolean(backendDiagnostics?.integrity_mismatch);
  const integrityFields = Array.isArray(backendDiagnostics?.integrity_mismatch_fields) ? backendDiagnostics?.integrity_mismatch_fields as string[] : [];
  const stepRunDrift = (backendDiagnostics?.step_run_drift || {}) as { missing?: string[]; mismatched?: string[]; extra?: string[]; count?: number };

  return (
    <section className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-sm)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Diagnóstico visible</div>
          <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">Caja negra abierta del wizard</h3>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Muestra el estado real del flujo, lo que el cliente cree, lo que el backend aceptó y qué pasos siguen sucios o pendientes.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {onRefresh ? <button type="button" className="secondary-btn" onClick={onRefresh}>Refrescar diagnóstico</button> : null}
          {onCopy ? <button type="button" className="secondary-btn" onClick={onCopy}>{copyFeedback || "Copiar diagnóstico"}</button> : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <StatusPill label={`modo: ${mode}`} />
        <StatusPill label={`UI: ${activeStep}`} tone={activeStep === allowedStep ? "success" : "warning"} />
        <StatusPill label={`permitido: ${allowedStep}`} tone="success" />
        <StatusPill label={`backend: ${safeText(wizard?.current_step, "sin step")}`} tone="neutral" />
        <StatusPill label={`autosave: ${autosaveState}`} tone={autosaveState === "error" ? "danger" : autosaveState === "saving" ? "warning" : autosaveState === "saved" ? "success" : "neutral"} />
        <StatusPill label={`gate: ${safeText(wizard?.validation_snapshot?.gate?.status, "n/a")}`} tone={gateTone} />
        <StatusPill label={`integridad: ${integrityMismatch ? "drift" : "ok"}`} tone={integrityMismatch ? "warning" : "success"} />
        <StatusPill label={`revision: ${safeText(wizard?.wizard_revision, "0")}`} />
        <StatusPill label={`dirty steps: ${dirtySteps.length}`} tone={dirtySteps.length ? "warning" : "success"} />
      </div>

      {integrityMismatch ? (
        <div className="mt-5 rounded-[22px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <div className="font-semibold">Se detectó drift interno y el wizard puede requerir reconciliación.</div>
          <div className="mt-1 text-[12px] leading-5">Campos afectados: {integrityFields.length ? integrityFields.join(", ") : "sin detalle"}. Step runs fuera de sync: {Number(stepRunDrift.count || 0)}.</div>
          <div className="mt-1 text-[12px] leading-5">Step guardado: {safeText(backendDiagnostics?.stored_current_step, "—")} → calculado: {safeText(backendDiagnostics?.computed_current_step, "—")}. Progreso: {safeText(backendDiagnostics?.stored_progress_percent, "0")}% → {safeText(backendDiagnostics?.computed_progress_percent, "0")}%.</div>
        </div>
      ) : null}

      <div className="mt-5 grid gap-4 xl:grid-cols-3">
        <div className="rounded-[22px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-sm font-semibold text-[color:var(--text-primary)]">Integridad</div>
          <div className="mt-3 grid gap-2 text-sm text-[color:var(--text-secondary)]">
            <div><strong className="text-[color:var(--text-primary)]">wizard_id:</strong> {safeText(wizard?.id, "sin wizard")}</div>
            <div><strong className="text-[color:var(--text-primary)]">estado:</strong> {safeText(wizard?.status, "draft")}</div>
            <div><strong className="text-[color:var(--text-primary)]">último guardado:</strong> {formatTs(wizard?.updated_at)}</div>
            <div><strong className="text-[color:var(--text-primary)]">primer required pendiente:</strong> {safeText(backendDiagnostics?.first_incomplete_required_step, pendingSteps[0] || "ninguno")}</div>
            <div><strong className="text-[color:var(--text-primary)]">recompute pendiente:</strong> {String(Boolean(backendDiagnostics?.validation_snapshot_pending || backendDiagnostics?.dry_run_pending))}</div>
            <div><strong className="text-[color:var(--text-primary)]">error visible:</strong> {safeText(wizardError, "ninguno")}</div>
            <div><strong className="text-[color:var(--text-primary)]">firma integridad:</strong> {safeText(backendDiagnostics?.integrity_signature, "n/a")}</div>
          </div>
        </div>

        <div className="rounded-[22px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-sm font-semibold text-[color:var(--text-primary)]">Autosave</div>
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm text-[color:var(--text-secondary)]">
            <div><strong className="block text-[color:var(--text-primary)]">Intentos</strong>{autosaveMetrics.attempts}</div>
            <div><strong className="block text-[color:var(--text-primary)]">Éxitos</strong>{autosaveMetrics.successes}</div>
            <div><strong className="block text-[color:var(--text-primary)]">Errores</strong>{autosaveMetrics.errors}</div>
            <div><strong className="block text-[color:var(--text-primary)]">Ignorados</strong>{autosaveMetrics.ignored}</div>
            <div><strong className="block text-[color:var(--text-primary)]">Promedio</strong>{autosaveMetrics.averageDurationMs} ms</div>
            <div><strong className="block text-[color:var(--text-primary)]">Máximo</strong>{autosaveMetrics.maxDurationMs} ms</div>
          </div>
          <div className="mt-3 text-xs text-[color:var(--text-tertiary)]">Actualizado: {formatTs(autosaveMetrics.updatedAt)}</div>
        </div>

        <div className="rounded-[22px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-sm font-semibold text-[color:var(--text-primary)]">Paso sucio vs backend</div>
          <div className="mt-3 grid gap-2 text-sm text-[color:var(--text-secondary)]">
            {dirtySteps.length ? dirtySteps.map((item) => (
              <div key={item.stepKey} className="rounded-2xl border border-amber-300 bg-amber-50 px-3 py-2">
                <div className="font-medium text-amber-800">{item.stepKey}</div>
                <div className="mt-1 text-[11px] leading-5 text-amber-700">client {item.clientFingerprint} · server {item.serverFingerprint || "none"}</div>
              </div>
            )) : <div className="rounded-2xl border border-emerald-300 bg-emerald-50 px-3 py-2 text-emerald-700">No hay pasos divergentes entre cliente y backend.</div>}
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <div className="rounded-[22px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-sm font-semibold text-[color:var(--text-primary)]">Timeline cliente</div>
          <div className="mt-3 grid gap-2">
            {clientEvents.length ? clientEvents.map((item) => (
              <div key={item.id} className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-2 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <strong className="text-[color:var(--text-primary)]">{item.type}</strong>
                  <span className="text-[11px] text-[color:var(--text-tertiary)]">{formatTs(item.createdAt)}</span>
                </div>
                {item.payload && Object.keys(item.payload).length ? <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-[11px] leading-5 text-[color:var(--text-secondary)]">{JSON.stringify(item.payload, null, 2)}</pre> : null}
              </div>
            )) : <div className="text-sm text-[color:var(--text-secondary)]">Sin eventos de sesión todavía.</div>}
          </div>
        </div>

        <div className="rounded-[22px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <div className="text-sm font-semibold text-[color:var(--text-primary)]">Timeline backend</div>
          <div className="mt-3 grid gap-2">
            {backendEvents.length ? backendEvents.map((item, index) => {
              const record = item as Record<string, unknown>;
              const eventType = safeText(record.event_type, `event_${index}`);
              const payload = record.payload as Record<string, unknown> | undefined;
              return (
                <div key={`${eventType}_${index}`} className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-2 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <strong className="text-[color:var(--text-primary)]">{eventType}</strong>
                    <span className="text-[11px] text-[color:var(--text-tertiary)]">{formatTs(record.created_at)}</span>
                  </div>
                  <div className="mt-1 text-[11px] text-[color:var(--text-secondary)]">step: {safeText(record.step_key, "—")}</div>
                  {payload && Object.keys(payload).length ? <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-[11px] leading-5 text-[color:var(--text-secondary)]">{JSON.stringify(payload, null, 2)}</pre> : null}
                </div>
              );
            }) : <div className="text-sm text-[color:var(--text-secondary)]">Sin eventos backend visibles todavía.</div>}
          </div>
        </div>
      </div>
    </section>
  );
}
