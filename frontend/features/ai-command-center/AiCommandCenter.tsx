"use client";

import { useCallback, useMemo, useState } from "react";
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

function unwrap<T>(payload: unknown): T {
  const value = payload as { data?: T } | T;
  return value && typeof value === "object" && "data" in value ? (value as { data: T }).data : (value as T);
}

async function readJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  const parsed = text ? JSON.parse(text) : {};
  if (!response.ok) {
    const detail = parsed?.detail || parsed?.error || parsed;
    const message = typeof detail === "string" ? detail : detail?.message || `HTTP ${response.status}`;
    throw new Error(message);
  }
  return unwrap<T>(parsed);
}

function optionalString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function optionalNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value) && value >= 0) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
  }
  return null;
}

function initialPayload(organizations: AiCommandOrganization[]): AiCommandPayload {
  return {
    organization_id: organizations[0]?.id || "",
    bot_id: null,
    user_description: "",
    vertical_id: null,
    subvertical: null,
    primary_objective: "agendar",
    language: "es",
    timezone: "America/Mexico_City",
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

function cleanAutopilotPayload(payload: AiCommandPayload): AiCommandPayload {
  return {
    ...payload,
    organization_id: optionalString(payload.organization_id) || "",
    bot_id: optionalString(payload.bot_id),
    user_description: payload.user_description.trim(),
    vertical_id: optionalString(payload.vertical_id),
    subvertical: optionalString(payload.subvertical),
    primary_objective: optionalString(payload.primary_objective) || "agendar",
    language: optionalString(payload.language) || "es",
    timezone: optionalString(payload.timezone) || "America/Mexico_City",
    intensity: payload.intensity === "godmode" && !GODMODE_ENABLED ? "savage" : payload.intensity,
    auto_apply: false,
    max_cost_usd: optionalNumber(payload.max_cost_usd),
  };
}

export function AiCommandCenter({ organizations, bots, verticals, initialRunId }: Props) {
  const [payload, setPayload] = useState<AiCommandPayload>(() => initialPayload(organizations));
  const [runId, setRunId] = useState<string | null>(initialRunId);
  const [run, setRun] = useState<AiWorkflowRunEnvelope | null>(null);
  const [busy, setBusy] = useState<"start" | "refresh" | "prepare" | "apply" | "canary" | "">("");
  const [message, setMessage] = useState<UiMessage>(null);
  const stream = useAiWorkflowStream(runId);

  const mergedRun = useMemo(() => run, [run]);

  const refreshRun = useCallback(async (targetRunId = runId) => {
    if (!targetRunId) return;
    setBusy("refresh");
    try {
      const data = await readJson<AiWorkflowRunEnvelope>(await fetch(`/api/ai/workflows/${encodeURIComponent(targetRunId)}`, { cache: "no-store" }));
      setRun(data);
      setMessage({ tone: "success", title: "Estado actualizado", detail: `Run ${targetRunId} recuperado correctamente.` });
    } catch (error) {
      setMessage({ tone: "danger", title: "No se pudo actualizar el run", detail: error instanceof Error ? error.message : "Error desconocido" });
    } finally {
      setBusy("");
    }
  }, [runId]);

  const start = useCallback(async () => {
    const safePayload = cleanAutopilotPayload(payload);
    if (!safePayload.organization_id || safePayload.user_description.length < 20) {
      setMessage({ tone: "warning", title: "Falta información", detail: "Selecciona organización y escribe mínimo 20 caracteres del negocio." });
      return;
    }
    setBusy("start");
    setMessage(null);
    try {
      const started = await readJson<BotAutopilotStartResponse>(await fetch("/api/ai/bot-autopilot?async_mode=true", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(safePayload),
      }));
      if (!started.run_id) throw new Error("El backend no devolvió run_id.");
      setRunId(started.run_id);
      setRun({ run: started as Record<string, unknown>, events: [{ event_type: "workflow.started", message: "Run creado; esperando eventos SSE reales", progress: started.progress || 1 }] });
      const safetyDetail = started.safety_warnings?.length ? ` · Ajustes seguros: ${started.safety_warnings.join(", ")}` : "";
      setMessage({ tone: "success", title: "Autopilot iniciado", detail: `Run ${started.run_id}${safetyDetail}` });
    } catch (error) {
      setMessage({ tone: "danger", title: "No se pudo iniciar el Autopilot", detail: error instanceof Error ? error.message : "Error desconocido" });
    } finally {
      setBusy("");
    }
  }, [payload]);

  const postRunAction = useCallback(async (action: "prepare-apply" | "apply" | "prepare-canary") => {
    if (!runId) return;
    const busyKey = action === "prepare-apply" ? "prepare" : action === "prepare-canary" ? "canary" : "apply";
    setBusy(busyKey);
    try {
      const body = action === "apply" ? JSON.stringify({ confirm: true }) : undefined;
      await readJson<Record<string, unknown>>(await fetch(`/api/ai/workflows/${encodeURIComponent(runId)}/${action}`, {
        method: "POST",
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body,
      }));
      setMessage({ tone: "success", title: action === "apply" ? "Bot aplicado" : "Acción completada", detail: "Actualizando estado del workflow." });
      await refreshRun(runId);
    } catch (error) {
      setMessage({ tone: "danger", title: "Acción bloqueada", detail: error instanceof Error ? error.message : "Error desconocido" });
    } finally {
      setBusy("");
    }
  }, [refreshRun, runId]);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <div className="grid gap-4">
        <AiCommandPrompt organizations={organizations} bots={bots} verticals={verticals} payload={payload} busy={Boolean(busy)} onChange={(patch) => setPayload((current) => {
          const next = { ...current, ...patch, auto_apply: false };
          const verticalChanged = Object.prototype.hasOwnProperty.call(patch, "vertical_id") && patch.vertical_id !== current.vertical_id;
          return {
            ...next,
            subvertical: verticalChanged && !Object.prototype.hasOwnProperty.call(patch, "subvertical") ? null : next.subvertical,
            intensity: next.intensity === "godmode" && !GODMODE_ENABLED ? "savage" : next.intensity,
          };
        })} onSubmit={start} />
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
        </div>
        <AiRunTimeline run={mergedRun} events={stream.events} connected={stream.connected} error={stream.error} />
      </div>
    </div>
  );
}
