"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { AiCommandPrompt } from "./AiCommandPrompt";
import { AiRunTimeline } from "./AiRunTimeline";
import { useAiWorkflowStream } from "./useAiWorkflowStream";
import type { AiCommandBotOption, AiCommandOrganization, AiCommandPayload, AiCommandVerticalOption, AiWorkflowRunEnvelope, BotAutopilotStartResponse } from "./types";

type Props = {
  organizations: AiCommandOrganization[];
  bots: AiCommandBotOption[];
  verticals: AiCommandVerticalOption[];
  initialRunId: string | null;
};

type UiMessage = { tone: "success" | "warning" | "danger"; title: string; detail?: string } | null;

const GODMODE_ENABLED = process.env.NEXT_PUBLIC_AI_ENABLE_GODMODE === "true";
const TERMINAL_EVENT_TYPES = new Set(["workflow.completed", "workflow.completed_partial", "workflow.failed", "workflow.cancelled", "workflow.paused_cost_limit"]);

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

function initialPayload(organizations: AiCommandOrganization[]): AiCommandPayload {
  const firstOrg = organizations[0];
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

export function AiCommandCenter({ organizations, bots, verticals, initialRunId }: Props) {
  const [payload, setPayload] = useState<AiCommandPayload>(() => initialPayload(organizations));
  const [runId, setRunId] = useState<string | null>(initialRunId);
  const [run, setRun] = useState<AiWorkflowRunEnvelope | null>(null);
  const [busy, setBusy] = useState<"start" | "refresh" | "prepare" | "apply" | "canary" | "">("");
  const [message, setMessage] = useState<UiMessage>(null);
  const startInFlightRef = useRef(false);
  const refreshInFlightRef = useRef(false);
  const actionInFlightRef = useRef(false);
  const stream = useAiWorkflowStream(runId);

  const mergedRun = useMemo(() => stream.snapshot || run, [run, stream.snapshot]);
  const terminalEvent = useMemo(() => [...stream.events].reverse().find((event) => TERMINAL_EVENT_TYPES.has(String(event.event_type || ""))) || null, [stream.events]);

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

  const postRunAction = useCallback(async (action: "prepare-apply" | "apply" | "prepare-canary") => {
    if (!runId || actionInFlightRef.current || Boolean(busy)) return;
    const busyKey = action === "prepare-apply" ? "prepare" : action === "prepare-canary" ? "canary" : "apply";
    actionInFlightRef.current = true;
    setBusy(busyKey);
    try {
      const body = action === "apply" ? JSON.stringify({ confirm: true }) : undefined;
      await readJson<Record<string, unknown>>(await fetch(`/api/ai/workflows/${encodeURIComponent(runId)}/${action}`, {
        method: "POST",
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body,
      }));
      setMessage({ tone: "success", title: action === "apply" ? "Bot aplicado" : "Accion completada", detail: "Actualizando estado del workflow." });
      await refreshRun(runId, { allowDuringBusy: true });
    } catch (error) {
      setMessage({ tone: "danger", title: "Accion bloqueada", detail: error instanceof Error ? error.message : "Error desconocido" });
    } finally {
      actionInFlightRef.current = false;
      setBusy("");
    }
  }, [busy, refreshRun, runId]);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <div className="grid gap-4">
        <AiCommandPrompt organizations={organizations} bots={bots} verticals={verticals} payload={payload} busy={Boolean(busy)} onChange={(patch) => setPayload((current) => normalizePayload(current, patch, organizations))} onSubmit={start} />
        {message ? <div className={`rounded-2xl border p-4 text-sm ${message.tone === "danger" ? "border-red-400/30 bg-red-500/10" : message.tone === "warning" ? "border-amber-400/30 bg-amber-500/10" : "border-emerald-400/30 bg-emerald-500/10"}`}><strong>{message.title}</strong>{message.detail ? <p className="mt-1 opacity-80">{message.detail}</p> : null}</div> : null}
      </div>
      <div className="grid gap-4">
        <div className="glass-card p-5">
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className="secondary-btn" disabled={!runId || Boolean(busy)} onClick={() => refreshRun()}>Actualizar estado</button>
            <button type="button" className="secondary-btn" disabled={!runId || Boolean(busy)} onClick={() => postRunAction("prepare-apply")}>Prepare apply</button>
            <button type="button" className="primary-btn" disabled={!runId || Boolean(busy)} onClick={() => postRunAction("apply")}>Apply safely</button>
            <button type="button" className="secondary-btn" disabled={!runId || Boolean(busy)} onClick={() => postRunAction("prepare-canary")}>Prepare canary</button>
          </div>
          <p className="mt-3 text-xs text-[color:var(--text-secondary)]">Run activo: <span className="mono-pill">{runId || "ninguno"}</span></p>
          {terminalEvent ? <p className="mt-2 text-xs text-[color:var(--text-secondary)]">Evento terminal: <span className="mono-pill">{String(terminalEvent.event_type || "workflow.terminal")}</span></p> : null}
        </div>
        <AiRunTimeline run={mergedRun} events={stream.events} connected={stream.connected} error={stream.error} />
      </div>
    </div>
  );
}
