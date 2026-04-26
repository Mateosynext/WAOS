"use client";

import type { AiWorkflowEvent, AiWorkflowRunEnvelope } from "./types";

type Props = {
  run: AiWorkflowRunEnvelope | null;
  events: AiWorkflowEvent[];
  connected: boolean;
  error: string | null;
};

const TERMINAL_EVENT_TYPES = ["workflow.completed", "workflow.completed_partial", "workflow.failed", "workflow.cancelled", "workflow.paused_cost_limit"];

function labelFor(event: AiWorkflowEvent) {
  return String(event.message || event.event_type || "Evento de workflow");
}

function progressFor(event: AiWorkflowEvent) {
  const value = Number(event.progress ?? event.payload_json?.progress ?? 0);
  return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
}

function eventKey(event: AiWorkflowEvent, fallback: number) {
  return String(event.id || `${event.event_type || "event"}:${event.created_at || fallback}:${event.message || ""}`);
}

function mergeEvents(storedEvents: AiWorkflowEvent[], streamEvents: AiWorkflowEvent[]) {
  const seen = new Set<string>();
  const merged: AiWorkflowEvent[] = [];
  for (const event of [...storedEvents, ...streamEvents]) {
    if (String(event.event_type || "") === "workflow.keepalive") continue;
    const key = eventKey(event, merged.length);
    if (seen.has(key)) continue;
    seen.add(key);
    merged.push(event);
  }
  return merged.slice(-30);
}

function statusFromEvents(events: AiWorkflowEvent[]) {
  const lastTerminal = [...events].reverse().find((event) => TERMINAL_EVENT_TYPES.includes(String(event.event_type || "")));
  return lastTerminal ? String(lastTerminal.event_type).replace("workflow.", "") : "pending";
}

export function AiRunTimeline({ run, events, connected, error }: Props) {
  const storedEvents = run?.events || [];
  const merged = mergeEvents(storedEvents, events);
  const currentStatus = String(run?.run?.status || statusFromEvents(merged));
  return (
    <section className="glass-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="eyebrow">Timeline real</p>
          <h2 className="text-xl font-semibold text-[color:var(--text-primary)]">Run del agente</h2>
          <p className="mt-1 text-sm text-[color:var(--text-secondary)]">Estado: <span className="mono-pill">{currentStatus}</span> · SSE {connected ? "conectado" : "recuperacion automatica"}</p>
        </div>
      </div>
      {error ? <div className="mt-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-3 text-sm text-amber-100">{error}</div> : null}
      <ol className="mt-5 grid gap-3">
        {merged.length ? merged.map((event, index) => (
          <li key={`${eventKey(event, index)}-${index}`} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium text-[color:var(--text-primary)]">{labelFor(event)}</p>
              <span className="mono-pill">{event.event_type || "message"}</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-current text-[color:var(--accent-primary)]" style={{ width: `${progressFor(event)}%` }} />
            </div>
          </li>
        )) : <li className="rounded-2xl border border-white/10 p-4 text-sm text-[color:var(--text-secondary)]">Todavia no hay eventos. Inicia un agente o actualiza un run existente.</li>}
      </ol>
    </section>
  );
}
