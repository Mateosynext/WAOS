"use client";

import { useEffect, useMemo, useState } from "react";
import type { AiWorkflowEvent } from "./types";

type StreamState = {
  connected: boolean;
  terminal: boolean;
  error: string | null;
  events: AiWorkflowEvent[];
  lastEvent: AiWorkflowEvent | null;
};

const TERMINAL_EVENTS = new Set([
  "workflow.completed",
  "workflow.completed_partial",
  "workflow.failed",
  "workflow.cancelled",
  "workflow.paused_cost_limit",
]);

function parseEvent(raw: string): AiWorkflowEvent {
  try {
    const parsed = JSON.parse(raw) as AiWorkflowEvent;
    return parsed && typeof parsed === "object" ? parsed : { message: raw };
  } catch {
    return { message: raw };
  }
}

function eventKey(event: AiWorkflowEvent, fallback: number) {
  return String(event.id || `${event.event_type || "event"}:${event.created_at || fallback}:${event.message || ""}`);
}

export function useAiWorkflowStream(runId: string | null) {
  const [state, setState] = useState<StreamState>({ connected: false, terminal: false, error: null, events: [], lastEvent: null });

  useEffect(() => {
    if (!runId) {
      setState({ connected: false, terminal: false, error: null, events: [], lastEvent: null });
      return;
    }
    let closed = false;
    const source = new EventSource(`/api/ai/workflows/${encodeURIComponent(runId)}/events`);
    setState((current) => ({ ...current, connected: false, terminal: false, error: null }));

    const append = (event: AiWorkflowEvent) => {
      if (closed) return;
      setState((current) => {
        const key = eventKey(event, current.events.length);
        const exists = current.events.some((item, index) => eventKey(item, index) === key);
        const events = exists ? current.events : [...current.events, event];
        const eventType = String(event.event_type || "");
        return {
          connected: true,
          terminal: current.terminal || TERMINAL_EVENTS.has(eventType),
          error: eventType === "workflow.failed" ? String(event.message || "Workflow falló") : current.error,
          events,
          lastEvent: event,
        };
      });
    };

    source.onopen = () => {
      if (!closed) setState((current) => ({ ...current, connected: true, error: null }));
    };
    source.onmessage = (message) => append(parseEvent(message.data));
    for (const type of TERMINAL_EVENTS) {
      source.addEventListener(type, (message) => append(parseEvent((message as MessageEvent).data)));
    }
    source.addEventListener("workflow.keepalive", (message) => append(parseEvent((message as MessageEvent).data)));
    source.onerror = () => {
      if (!closed) setState((current) => ({ ...current, connected: false, error: current.terminal ? current.error : "Stream SSE desconectado; usa Actualizar estado para recuperar." }));
      source.close();
    };

    return () => {
      closed = true;
      source.close();
    };
  }, [runId]);

  return useMemo(() => state, [state]);
}
