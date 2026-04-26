"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { AiWorkflowEvent, AiWorkflowRunEnvelope } from "./types";

type StreamState = {
  connected: boolean;
  terminal: boolean;
  error: string | null;
  events: AiWorkflowEvent[];
  lastEvent: AiWorkflowEvent | null;
  snapshot: AiWorkflowRunEnvelope | null;
};

const TERMINAL_EVENTS = new Set([
  "workflow.completed",
  "workflow.completed_partial",
  "workflow.failed",
  "workflow.cancelled",
  "workflow.paused_cost_limit",
]);

const TERMINAL_RUN_STATUSES = new Set([
  "completed",
  "completed_partial",
  "failed",
  "cancelled",
  "paused_cost_limit",
]);

function unwrap<T>(payload: unknown): T {
  const value = payload as { data?: T } | T;
  return value && typeof value === "object" && "data" in value ? (value as { data: T }).data : (value as T);
}

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

function runStatusIsTerminal(envelope: AiWorkflowRunEnvelope) {
  const run = envelope.run || {};
  const status = String(run.status || "");
  return TERMINAL_RUN_STATUSES.has(status);
}

export function useAiWorkflowStream(runId: string | null) {
  const [state, setState] = useState<StreamState>({ connected: false, terminal: false, error: null, events: [], lastEvent: null, snapshot: null });
  const lastEventIdRef = useRef<string | null>(null);
  const connectedRef = useRef(false);
  const terminalRef = useRef(false);

  useEffect(() => {
    if (!runId) {
      lastEventIdRef.current = null;
      connectedRef.current = false;
      terminalRef.current = false;
      setState({ connected: false, terminal: false, error: null, events: [], lastEvent: null, snapshot: null });
      return;
    }

    let closed = false;
    const controller = new AbortController();
    const eventUrl = () => {
      const query = lastEventIdRef.current ? `?last_event_id=${encodeURIComponent(lastEventIdRef.current)}` : "";
      return `/api/ai/workflows/${encodeURIComponent(runId)}/events${query}`;
    };
    const source = new EventSource(eventUrl());

    connectedRef.current = false;
    terminalRef.current = false;
    setState({ connected: false, terminal: false, error: null, events: [], lastEvent: null, snapshot: null });

    const append = (event: AiWorkflowEvent, options?: { fromPolling?: boolean }) => {
      if (closed) return;
      if (event.id) lastEventIdRef.current = String(event.id);
      const eventType = String(event.event_type || "");
      const isTerminalEvent = TERMINAL_EVENTS.has(eventType);
      terminalRef.current = terminalRef.current || isTerminalEvent;
      connectedRef.current = options?.fromPolling ? connectedRef.current : true;
      setState((current) => {
        const key = eventKey(event, current.events.length);
        const exists = current.events.some((item, index) => eventKey(item, index) === key);
        const events = exists ? current.events : [...current.events, event];
        const nextTerminal = current.terminal || isTerminalEvent;
        return {
          ...current,
          connected: options?.fromPolling ? current.connected : true,
          terminal: nextTerminal,
          error: eventType === "workflow.failed" ? String(event.message || "Workflow fallo") : nextTerminal ? null : current.error,
          events,
          lastEvent: event,
        };
      });
    };

    const recoverFromSnapshot = async () => {
      if (closed || connectedRef.current || terminalRef.current) return;
      try {
        const response = await fetch(`/api/ai/workflows/${encodeURIComponent(runId)}`, { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const snapshot = unwrap<AiWorkflowRunEnvelope>(await response.json());
        for (const event of snapshot.events || []) append(event, { fromPolling: true });
        const snapshotTerminal = runStatusIsTerminal(snapshot);
        if (snapshotTerminal) terminalRef.current = true;
        setState((current) => ({
          ...current,
          snapshot,
          terminal: current.terminal || snapshotTerminal,
          error: snapshotTerminal ? null : current.connected ? null : "SSE reconectando automaticamente; estado recuperado por polling.",
        }));
      } catch (error) {
        if (closed || controller.signal.aborted) return;
        const detail = error instanceof Error ? error.message : "polling failed";
        setState((current) => ({ ...current, error: current.terminal ? current.error : `SSE reconectando automaticamente; polling pendiente (${detail}).` }));
      }
    };

    source.onopen = () => {
      if (closed) return;
      connectedRef.current = true;
      setState((current) => ({ ...current, connected: true, error: null }));
    };
    source.onmessage = (message) => append(parseEvent(message.data));
    for (const type of TERMINAL_EVENTS) {
      source.addEventListener(type, (message) => append(parseEvent((message as MessageEvent).data)));
    }
    source.addEventListener("workflow.keepalive", (message) => append(parseEvent((message as MessageEvent).data)));
    source.onerror = () => {
      if (closed) return;
      connectedRef.current = false;
      setState((current) => ({
        ...current,
        connected: false,
        error: current.terminal ? current.error : "SSE reconectando automaticamente; recuperando estado por polling.",
      }));
      void recoverFromSnapshot();
      // Do not close here. Browser EventSource performs native retry using retry:/Last-Event-ID.
    };

    const pollInterval = window.setInterval(() => {
      void recoverFromSnapshot();
    }, 2500);

    return () => {
      closed = true;
      controller.abort();
      window.clearInterval(pollInterval);
      source.close();
    };
  }, [runId]);

  return useMemo(() => state, [state]);
}
