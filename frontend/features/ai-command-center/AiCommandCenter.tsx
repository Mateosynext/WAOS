"use client";

import Link from "next/link";
import { useCallback, useMemo, useRef, useState } from "react";
import { AiCommandPrompt } from "./AiCommandPrompt";
import { AiRunTimeline } from "./AiRunTimeline";
import { useAiWorkflowStream } from "./useAiWorkflowStream";
import type { AiCommandBotOption, AiCommandOrganization, AiCommandPayload, AiCommandVerticalOption, AiGoLiveReadiness, AiHumanConfirmation, AiWorkflowRunEnvelope, BotAutopilotStartResponse } from "./types";

type Props = {
  organizations: AiCommandOrganization[];
  bots: AiCommandBotOption[];
  verticals: AiCommandVerticalOption[];
  initialRunId: string | null;
};

type UiMessage = { tone: "success" | "warning" | "danger"; title: string; detail?: string } | null;
type BusyKey = "start" | "refresh" | "prepare" | "apply" | "canary" | "confirm" | "";

const GODMODE_ENABLED = process.env.NEXT_PUBLIC_AI_ENABLE_GODMODE === "true";
const TERMINAL_EVENT_TYPES = new Set(["workflow.completed", "workflow.completed_partial", "workflow.failed", "workflow.cancelled", "workflow.paused_cost_limit"]);
const FINISHED_RUN_STATUSES = new Set(["completed"]);
const RESOLVED_CONFIRMATION_STATUSES = new Set(["confirmed", "not_applicable", "escalate_to_human", "blocked_response", "range_confirmed", "deferred_safe"]);

function unwrap<T>(payload: unknown): T {
  const value = payload as { data?: T } | T;
  return value && typeof value === "object" && "data" in value ? (value as { data: T }).data : (value as T);
}

async function readJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  let parsed: any = {};
  try {
    parsed = text ? JSON.parse(text) : {};
  } catch {
    parsed = { detail: text || `HTTP ${response.status}` };
  }
  if (!response.ok) {
    const detail = parsed?.detail || parsed?.error || parsed;
    const message = typeof detail === "string" ? detail : detail?.message || `HTTP ${response.status}`;
    throw new Error(message);
  }
  return unwrap<T>(parsed);
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item || "").trim()).filter(Boolean) : [];
}


function stableClientRequestId(prefix: string, value: unknown) {
  const serialized = JSON.stringify(value);
  let hash = 2166136261;
  for (let index = 0; index < serialized.length; index += 1) {
    hash ^= serialized.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `${prefix}_${(hash >>> 0).toString(16)}_${serialized.length}`;
}

function cleanOptionalString(value: unknown): string | null {
  if (typeof value === "string") {
    const cleaned = value.trim();
    return cleaned || null;
  }
  if (typeof value === "number") return String(value);
  if (typeof value === "boolean") return null;
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const record = value as Record<string, unknown>;
    for (const key of ["id", "bot_id", "organization_id", "value"]) {
      const nested = cleanOptionalString(record[key]);
      if (nested) return nested;
    }
    return null;
  }
  return null;
}

function getStartBlockingReason(payload: AiCommandPayload) {
  if (!cleanOptionalString(payload.organization_id)) return "Selecciona una organización antes de generar el bot con IA.";
  const descriptionLength = payload.user_description.trim().length;
  if (descriptionLength < 20) return `Describe el negocio con al menos 20 caracteres. Ahora hay ${descriptionLength}.`;
  return "";
}

function getResult(run: AiWorkflowRunEnvelope | null): Record<string, unknown> {
  return asRecord(run?.result);
}

function parseEnvelopeTimestamp(run: AiWorkflowRunEnvelope | null): number {
  const runRecord = asRecord(run?.run);
  const result = getResult(run);
  const candidates = [runRecord.updated_at, runRecord.completed_at, runRecord.created_at, result.updated_at, result.completed_at, result.created_at];
  for (const candidate of candidates) {
    const cleaned = cleanOptionalString(candidate);
    if (!cleaned) continue;
    const parsed = Date.parse(cleaned);
    if (Number.isFinite(parsed)) return parsed;
  }
  return 0;
}

function envelopeCompletenessScore(run: AiWorkflowRunEnvelope | null): number {
  if (!run) return 0;
  const result = getResult(run);
  return [
    getRunStatus(run) ? 2 : 0,
    getWizardId(run) ? 3 : 0,
    getBotId(run) ? 2 : 0,
    getReadiness(run) ? 3 : 0,
    Array.isArray(run.events) ? Math.min(run.events.length, 20) : 0,
    getConfirmations(run).length * 2,
    Object.keys(result).length,
  ].reduce((sum, item) => sum + item, 0);
}

function pickFreshestRun(localRun: AiWorkflowRunEnvelope | null, streamRun: AiWorkflowRunEnvelope | null): AiWorkflowRunEnvelope | null {
  if (!localRun) return streamRun;
  if (!streamRun) return localRun;
  const localTs = parseEnvelopeTimestamp(localRun);
  const streamTs = parseEnvelopeTimestamp(streamRun);
  if (localTs && streamTs && localTs !== streamTs) return localTs > streamTs ? localRun : streamRun;
  const localScore = envelopeCompletenessScore(localRun);
  const streamScore = envelopeCompletenessScore(streamRun);
  return localScore >= streamScore ? localRun : streamRun;
}

function getRunStatus(run: AiWorkflowRunEnvelope | null): string {
  const runRecord = asRecord(run?.run);
  return String(runRecord.status || getResult(run).status || "");
}

function getWizardId(run: AiWorkflowRunEnvelope | null): string | null {
  return cleanOptionalString(asRecord(run?.run).wizard_id) || cleanOptionalString(getResult(run).wizard_id) || cleanOptionalString(asRecord(getResult(run).wizard).id);
}

function getBotId(run: AiWorkflowRunEnvelope | null): string | null {
  const result = getResult(run);
  const applyResult = asRecord(result.apply_result);
  return cleanOptionalString(applyResult.bot_id) || cleanOptionalString(result.bot_id) || cleanOptionalString(asRecord(run?.run).bot_id);
}

function getApplyResult(run: AiWorkflowRunEnvelope | null): Record<string, unknown> {
  return asRecord(getResult(run).apply_result);
}

function getReadiness(run: AiWorkflowRunEnvelope | null): AiGoLiveReadiness | null {
  const result = getResult(run);
  const readiness = asRecord(result.go_live_readiness) as AiGoLiveReadiness;
  return Object.keys(readiness).length ? readiness : null;
}

function getConfirmations(run: AiWorkflowRunEnvelope | null): AiHumanConfirmation[] {
  const direct = run?.human_confirmations;
  if (Array.isArray(direct)) return direct;
  const fromResult = getResult(run).human_confirmations;
  return Array.isArray(fromResult) ? (fromResult as AiHumanConfirmation[]) : [];
}

function isConfirmationResolved(item: AiHumanConfirmation) {
  const status = String(item.status || "pending").trim();
  return RESOLVED_CONFIRMATION_STATUSES.has(status);
}

function confirmationFieldKey(item: AiHumanConfirmation, index: number) {
  return cleanOptionalString(item.field_key) || `confirmation_${index}`;
}

function initialPayload(organizations: AiCommandOrganization[]): AiCommandPayload {
  const firstOrg = organizations.length === 1 ? organizations[0] : undefined;
  return {
    organization_id: firstOrg?.id || "",
    bot_id: null,
    user_description: "",
    vertical_id: firstOrg?.vertical || null,
    subvertical: firstOrg?.subvertical || null,
    primary_objective: "agendar",
    language: "es",
    timezone: firstOrg?.timezone || "America/Mexico_City",
    intensity: "savage",
    auto_generate_knowledge: true,
    auto_generate_templates: true,
    auto_generate_tools: true,
    auto_run_simulations: true,
    auto_autofix: true,
    auto_prepare_go_live: true,
    auto_apply: false,
    max_cost_usd: 12,
  };
}

function normalizePayload(current: AiCommandPayload, patch: Partial<AiCommandPayload>, organizations: AiCommandOrganization[]): AiCommandPayload {
  const next: AiCommandPayload = { ...current, ...patch, auto_apply: false };
  if ("organization_id" in patch) {
    const org = organizations.find((item) => item.id === patch.organization_id);
    next.vertical_id = org?.vertical || next.vertical_id || null;
    next.subvertical = org?.subvertical || null;
    next.timezone = org?.timezone || next.timezone || "America/Mexico_City";
  }
  if ("vertical_id" in patch) {
    next.subvertical = patch.subvertical ?? null;
  }
  if (next.intensity === "godmode" && !GODMODE_ENABLED) {
    next.intensity = "savage";
  }
  return next;
}

function actionBlockReason({ runId, finished, wizardId, pendingCount, readiness, applied }: { runId: string | null; finished: boolean; wizardId: string | null; pendingCount: number; readiness: AiGoLiveReadiness | null; applied: boolean }) {
  if (!runId) return "Inicia un Autopilot antes de preparar o aplicar.";
  if (!finished) return "Espera a que el workflow termine en completed. completed_partial requiere waiver explícito y no habilita apply por default.";
  if (!wizardId) return "No hay wizard aplicable; reintenta la generación del bot.";
  if (pendingCount > 0) return `Resuelve ${pendingCount} confirmación(es) humana(s) antes de aplicar.`;
  if (!readiness) return "Calcula readiness antes de aplicar.";
  if (readiness.can_apply === false || readiness.status === "blocked") return "Readiness sigue bloqueado; revisa blockers y confirmaciones.";
  if (applied) return "El bot ya fue aplicado; puedes abrirlo o preparar canary.";
  return "";
}

function HumanConfirmationsPanel({ confirmations, values, busy, onValueChange, onConfirm }: { confirmations: AiHumanConfirmation[]; values: Record<string, string>; busy: boolean; onValueChange: (fieldKey: string, value: string) => void; onConfirm: (item: AiHumanConfirmation, value: string, index: number) => void }) {
  const pending = confirmations.filter((item) => !isConfirmationResolved(item));
  return (
    <div className="glass-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Confirmaciones humanas</p>
          <h2 className="text-lg font-semibold text-[color:var(--text-primary)]">Handoff y datos que la IA no debe inventar</h2>
          <p className="mt-1 text-sm text-[color:var(--text-secondary)]">Resuelve cada campo pendiente; al confirmar se recalcula readiness y se desbloquea Apply solo si todo queda seguro.</p>
        </div>
        <span className="mono-pill">pendientes: {pending.length}</span>
      </div>
      <div className="mt-4 grid gap-3">
        {confirmations.length ? confirmations.map((item, index) => {
          const fieldKey = confirmationFieldKey(item, index);
          const resolved = isConfirmationResolved(item);
          const currentValue = values[fieldKey] ?? cleanOptionalString(item.confirmed_value) ?? cleanOptionalString(item.suggested_value) ?? "";
          return (
            <div key={`${fieldKey}-${index}`} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-[color:var(--text-primary)]">{cleanOptionalString(item.label) || fieldKey}</p>
                  <p className="mt-1 text-xs text-[color:var(--text-secondary)]">{cleanOptionalString(item.reason) || "Validación requerida antes de aplicar."}</p>
                </div>
                <span className="mono-pill">{String(item.status || "pending")}</span>
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-[minmax(0,1fr)_auto]">
                <input
                  className="rounded-2xl border border-white/10 bg-black/20 px-4 py-2 text-sm text-[color:var(--text-primary)] outline-none focus:border-[color:var(--accent-primary)]"
                  value={currentValue}
                  disabled={busy || resolved}
                  placeholder="Ej. +52 55 0000 0000, operaciones@empresa.com o nombre del responsable"
                  onChange={(event) => onValueChange(fieldKey, event.target.value)}
                />
                <button type="button" className="primary-btn" disabled={busy || resolved || !currentValue.trim()} onClick={() => onConfirm(item, currentValue, index)}>
                  {resolved ? "Confirmado" : "Confirmar"}
                </button>
              </div>
            </div>
          );
        }) : <p className="rounded-2xl border border-white/10 p-4 text-sm text-[color:var(--text-secondary)]">Todavía no hay confirmaciones. Aparecerán aquí cuando readiness detecte blockers humanos.</p>}
      </div>
    </div>
  );
}

export function AiCommandCenter({ organizations, bots, verticals, initialRunId }: Props) {
  const [payload, setPayload] = useState<AiCommandPayload>(() => initialPayload(organizations));
  const [runId, setRunId] = useState<string | null>(initialRunId);
  const [run, setRun] = useState<AiWorkflowRunEnvelope | null>(null);
  const [busy, setBusy] = useState<BusyKey>("");
  const [message, setMessage] = useState<UiMessage>(null);
  const [confirmationValues, setConfirmationValues] = useState<Record<string, string>>({});
  const [lastAppliedBotId, setLastAppliedBotId] = useState<string | null>(null);
  const startInFlightRef = useRef(false);
  const refreshInFlightRef = useRef(false);
  const actionInFlightRef = useRef(false);
  const confirmInFlightRef = useRef(false);
  const stream = useAiWorkflowStream(runId);

  const mergedRun = useMemo(() => pickFreshestRun(run, stream.snapshot), [run, stream.snapshot]);
  const terminalEvent = useMemo(() => [...stream.events].reverse().find((event) => TERMINAL_EVENT_TYPES.has(String(event.event_type || ""))) || null, [stream.events]);
  const runStatus = getRunStatus(mergedRun);
  const finished = FINISHED_RUN_STATUSES.has(runStatus) || Boolean(terminalEvent && FINISHED_RUN_STATUSES.has(String(terminalEvent.event_type || "").replace("workflow.", "")));
  const wizardId = getWizardId(mergedRun);
  const readiness = getReadiness(mergedRun);
  const confirmations = getConfirmations(mergedRun);
  const pendingConfirmations = confirmations.filter((item) => !isConfirmationResolved(item));
  const applyResult = getApplyResult(mergedRun);
  const applied = String(applyResult.status || "") === "applied" || Boolean(lastAppliedBotId);
  const createdBotId = lastAppliedBotId || (applied ? getBotId(mergedRun) : null);
  const applyBlockedReason = actionBlockReason({ runId, finished, wizardId, pendingCount: pendingConfirmations.length, readiness, applied });
  const canPrepareApply = Boolean(runId && finished && wizardId && readiness && readiness.can_apply !== false && readiness.status !== "blocked" && pendingConfirmations.length === 0 && !applied && !busy);
  const canApply = Boolean(runId && finished && wizardId && readiness && readiness.can_apply !== false && readiness.status !== "blocked" && pendingConfirmations.length === 0 && !applied && !busy);
  const canPrepareCanary = Boolean(runId && applied && !busy);

  const refreshRun = useCallback(async (targetRunId = runId, options?: { allowDuringBusy?: boolean }) => {
    if (!targetRunId || refreshInFlightRef.current || (Boolean(busy) && !options?.allowDuringBusy)) return;
    refreshInFlightRef.current = true;
    setBusy("refresh");
    try {
      const data = await readJson<AiWorkflowRunEnvelope>(await fetch(`/api/ai/workflows/${encodeURIComponent(targetRunId)}`, { cache: "no-store" }));
      setRun(data);
      setMessage({ tone: "success", title: "Estado actualizado", detail: `Run ${targetRunId} recuperado correctamente.` });
    } catch (error) {
      setMessage({ tone: "danger", title: "No se pudo actualizar el run", detail: error instanceof Error ? error.message : "Error desconocido" });
    } finally {
      refreshInFlightRef.current = false;
      setBusy("");
    }
  }, [busy, runId]);

  const start = useCallback(async () => {
    if (startInFlightRef.current || Boolean(busy)) return;
    const blockingReason = getStartBlockingReason(payload);
    if (blockingReason) {
      setMessage({ tone: "warning", title: "Falta informacion para generar el bot", detail: blockingReason });
      return;
    }
    startInFlightRef.current = true;
    setBusy("start");
    setMessage(null);
    setConfirmationValues({});
    setLastAppliedBotId(null);
    try {
      const safePayload: AiCommandPayload = {
        ...payload,
        organization_id: cleanOptionalString(payload.organization_id) || "",
        bot_id: cleanOptionalString(payload.bot_id),
        vertical_id: cleanOptionalString(payload.vertical_id),
        subvertical: cleanOptionalString(payload.subvertical),
        primary_objective: cleanOptionalString(payload.primary_objective),
        intensity: payload.intensity === "godmode" && !GODMODE_ENABLED ? "savage" : payload.intensity,
        auto_apply: false,
        client_request_id: stableClientRequestId("autopilot", { ...payload, auto_apply: false }),
      };
      const started = await readJson<BotAutopilotStartResponse>(await fetch("/api/ai/bot-autopilot?async_mode=true", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(safePayload),
      }));
      if (!started.run_id) throw new Error("El backend no devolvio run_id.");
      setRunId(started.run_id);
      setRun({ run: started as Record<string, unknown>, events: [{ event_type: "workflow.started", message: "Run creado; esperando eventos SSE reales", progress: started.progress || 1 }] });
      const safetyDetail = started.safety_warnings?.length ? ` · Ajustes seguros: ${started.safety_warnings.join(", ")}` : "";
      setMessage({ tone: "success", title: "Autopilot iniciado", detail: `Run ${started.run_id}${safetyDetail}` });
    } catch (error) {
      setMessage({ tone: "danger", title: "No se pudo iniciar el Autopilot", detail: error instanceof Error ? error.message : "Error desconocido" });
    } finally {
      startInFlightRef.current = false;
      setBusy("");
    }
  }, [busy, payload]);

  const confirmHumanItem = useCallback(async (item: AiHumanConfirmation, value: string, index: number) => {
    if (!runId || confirmInFlightRef.current || Boolean(busy)) return;
    const fieldKey = confirmationFieldKey(item, index);
    confirmInFlightRef.current = true;
    setBusy("confirm");
    try {
      await readJson<Record<string, unknown>>(await fetch(`/api/ai/workflows/${encodeURIComponent(runId)}/human-confirmations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field_key: fieldKey, label: item.label, reason: item.reason, status: "confirmed", confirmed_value: value.trim() }),
      }));
      await readJson<Record<string, unknown>>(await fetch(`/api/ai/workflows/${encodeURIComponent(runId)}/go-live-readiness`, { method: "POST" }));
      setMessage({ tone: "success", title: "Confirmacion guardada", detail: "Readiness fue recalculado; revisa si Apply ya quedó desbloqueado." });
      await refreshRun(runId, { allowDuringBusy: true });
    } catch (error) {
      setMessage({ tone: "danger", title: "No se pudo guardar la confirmacion", detail: error instanceof Error ? error.message : "Error desconocido" });
    } finally {
      confirmInFlightRef.current = false;
      setBusy("");
    }
  }, [busy, refreshRun, runId]);

  const postRunAction = useCallback(async (action: "prepare-apply" | "apply" | "prepare-canary") => {
    if (!runId || actionInFlightRef.current || Boolean(busy)) return;
    const currentBlockReason = actionBlockReason({ runId, finished, wizardId, pendingCount: pendingConfirmations.length, readiness, applied });
    if ((action === "prepare-apply" || action === "apply") && currentBlockReason) {
      setMessage({ tone: "warning", title: "Accion bloqueada por readiness", detail: currentBlockReason });
      return;
    }
    if (action === "prepare-canary" && !applied) {
      setMessage({ tone: "warning", title: "Canary bloqueado", detail: "Aplica el bot antes de preparar canary." });
      return;
    }
    const busyKey: BusyKey = action === "prepare-apply" ? "prepare" : action === "prepare-canary" ? "canary" : "apply";
    actionInFlightRef.current = true;
    setBusy(busyKey);
    try {
      let body: string | undefined;
      if (action === "apply") {
        const plan = await readJson<Record<string, unknown>>(await fetch(`/api/ai/workflows/${encodeURIComponent(runId)}/prepare-apply`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ idempotency_key: stableClientRequestId("prepare_apply", { runId, wizardId }) }),
        }));
        const confirmationToken = cleanOptionalString(plan.confirmation_token);
        if (!confirmationToken) throw new Error("El backend no devolvió confirmation_token para aplicar.");
        body = JSON.stringify({
          confirm: true,
          confirmation_token: confirmationToken,
          idempotency_key: stableClientRequestId("apply", { runId, wizardId, confirmationToken }),
        });
      }
      const data = await readJson<Record<string, unknown>>(await fetch(`/api/ai/workflows/${encodeURIComponent(runId)}/${action}`, {
        method: "POST",
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body,
      }));
      const botId = action === "apply" ? cleanOptionalString(data.bot_id) : null;
      if (botId) setLastAppliedBotId(botId);
      setMessage({ tone: "success", title: action === "apply" ? "Bot aplicado" : "Accion completada", detail: botId ? `Bot creado/aplicado: ${botId}` : "Actualizando estado del workflow." });
      await refreshRun(runId, { allowDuringBusy: true });
    } catch (error) {
      setMessage({ tone: "danger", title: "Accion bloqueada", detail: error instanceof Error ? error.message : "Error desconocido" });
    } finally {
      actionInFlightRef.current = false;
      setBusy("");
    }
  }, [applied, busy, finished, pendingConfirmations.length, readiness, refreshRun, runId, wizardId]);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <div className="grid gap-4">
        <AiCommandPrompt organizations={organizations} bots={bots} verticals={verticals} payload={payload} busy={Boolean(busy)} onChange={(patch) => setPayload((current) => normalizePayload(current, patch, organizations))} onSubmit={start} />
        {message ? <div className={`rounded-2xl border p-4 text-sm ${message.tone === "danger" ? "border-red-400/30 bg-red-500/10" : message.tone === "warning" ? "border-amber-400/30 bg-amber-500/10" : "border-emerald-400/30 bg-emerald-500/10"}`}><strong>{message.title}</strong>{message.detail ? <p className="mt-1 opacity-80">{message.detail}</p> : null}</div> : null}
        {createdBotId ? <div className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4 text-sm"><strong>Bot listo</strong><p className="mt-1 opacity-80">El apply devolvió el bot <span className="mono-pill">{createdBotId}</span>.</p><Link href={`/bots/${encodeURIComponent(createdBotId)}`} className="primary-btn mt-3 inline-flex">Abrir bot</Link></div> : null}
        {runId ? <HumanConfirmationsPanel confirmations={confirmations} values={confirmationValues} busy={Boolean(busy)} onValueChange={(fieldKey, value) => setConfirmationValues((current) => ({ ...current, [fieldKey]: value }))} onConfirm={confirmHumanItem} /> : null}
      </div>
      <div className="grid gap-4">
        <div className="glass-card p-5">
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className="secondary-btn" disabled={!runId || Boolean(busy)} onClick={() => refreshRun()}>Actualizar estado</button>
            <button type="button" className="secondary-btn" disabled={!canPrepareApply} title={!canPrepareApply ? applyBlockedReason : ""} onClick={() => postRunAction("prepare-apply")}>Prepare apply</button>
            <button type="button" className="primary-btn" disabled={!canApply} title={!canApply ? applyBlockedReason : ""} onClick={() => postRunAction("apply")}>Apply safely</button>
            <button type="button" className="secondary-btn" disabled={!canPrepareCanary} onClick={() => postRunAction("prepare-canary")}>Prepare canary</button>
          </div>
          <div className="mt-3 grid gap-2 text-xs text-[color:var(--text-secondary)]">
            <p>Run activo: <span className="mono-pill">{runId || "ninguno"}</span></p>
            <p>Estado: <span className="mono-pill">{runStatus || "sin snapshot"}</span> · Wizard: <span className="mono-pill">{wizardId || "pendiente"}</span></p>
            {terminalEvent ? <p>Evento terminal: <span className="mono-pill">{String(terminalEvent.event_type || "workflow.terminal")}</span></p> : null}
            {readiness ? <p>Readiness: <span className="mono-pill">{String(readiness.status || "unknown")}</span> · score <span className="mono-pill">{String(readiness.score ?? "n/a")}</span> · can_apply <span className="mono-pill">{String(readiness.can_apply)}</span></p> : null}
            {pendingConfirmations.length ? <p className="text-amber-100">Antes de aplicar: {applyBlockedReason}</p> : applyBlockedReason && runId ? <p className="text-amber-100">{applyBlockedReason}</p> : null}
          </div>
          {readiness ? <div className="mt-4 grid gap-2 text-xs text-[color:var(--text-secondary)]">
            {asStringArray(readiness.blockers).length ? <p><strong className="text-amber-100">Blockers:</strong> {asStringArray(readiness.blockers).join(", ")}</p> : null}
            {asStringArray(readiness.warnings).length ? <p><strong className="text-amber-100">Warnings:</strong> {asStringArray(readiness.warnings).join(", ")}</p> : null}
          </div> : null}
        </div>
        <AiRunTimeline run={mergedRun} events={stream.events} connected={stream.connected} error={stream.error} />
      </div>
    </div>
  );
}
