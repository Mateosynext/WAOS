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

function eventSequence(event: AiWorkflowEvent): number | null {
  const raw = (event as AiWorkflowEvent & { sequence?: unknown }).sequence;
  const value = typeof raw === "number" ? raw : Number(raw);
  return Number.isFinite(value) ? value : null;
}

function eventKey(event: AiWorkflowEvent, fallback: number) {
  if (event.id) return String(event.id);
  const sequence = eventSequence(event);
  if (sequence !== null) return `sequence:${sequence}`;
  return String(`${event.event_type || "event"}:${event.created_at || fallback}:${event.message || ""}`);
}

function orderEvents(events: AiWorkflowEvent[]) {
  return [...events].sort((left, right) => {
    const leftSequence = eventSequence(left);
    const rightSequence = eventSequence(right);
    if (leftSequence !== null && rightSequence !== null && leftSequence !== rightSequence) return leftSequence - rightSequence;
    if (leftSequence !== null && rightSequence === null) return -1;
    if (leftSequence === null && rightSequence !== null) return 1;
    return String(left.created_at || "").localeCompare(String(right.created_at || ""));
  });
}

function runStatusIsTerminal(envelope: AiWorkflowRunEnvelope) {
  const run = envelope.run || {};
  const status = String(run.status || "");
  return TERMINAL_RUN_STATUSES.has(status);
}

export function useAiWorkflowStream(runId: string | null) {
  const [state, setState] = useState<StreamState>({ connected: false, terminal: false, error: null, events: [], lastEvent: null, snapshot: null });
  const lastEventIdRef = useRef<string | null>(null);
  const activeRunIdRef = useRef<string | null>(null);
  const connectedRef = useRef(false);
  const terminalRef = useRef(false);
  const lastMessageAtRef = useRef<number>(0);
  const pollingInFlightRef = useRef(false);
  const finalSnapshotFetchedRef = useRef(false);

  useEffect(() => {
    if (!runId) {
      activeRunIdRef.current = null;
      lastEventIdRef.current = null;
      connectedRef.current = false;
      terminalRef.current = false;
      pollingInFlightRef.current = false;
      finalSnapshotFetchedRef.current = false;
      lastMessageAtRef.current = 0;
      setState({ connected: false, terminal: false, error: null, events: [], lastEvent: null, snapshot: null });
      return;
    }

    if (activeRunIdRef.current !== runId) {
      activeRunIdRef.current = runId;
      lastEventIdRef.current = null;
      finalSnapshotFetchedRef.current = false;
    }

    lastMessageAtRef.current = Date.now();
    let closed = false;
    const controller = new AbortController();
    const eventUrl = () => {
      const query = lastEventIdRef.current ? `?last_event_id=${encodeURIComponent(lastEventIdRef.current)}` : "";
      return `/api/ai/workflows/${encodeURIComponent(runId)}/events${query}`;
    };
    const source = new EventSource(eventUrl());

    connectedRef.current = false;
    terminalRef.current = false;
    finalSnapshotFetchedRef.current = false;
    setState({ connected: false, terminal: false, error: null, events: [], lastEvent: null, snapshot: null });

    const recoverFromSnapshot = async (options?: { force?: boolean; allowTerminal?: boolean }) => {
      if (closed || pollingInFlightRef.current) return;
      if (terminalRef.current && !options?.allowTerminal) return;
      const hasNoEventsYet = !lastEventIdRef.current;
      if (connectedRef.current && !options?.force && !hasNoEventsYet) return;
      pollingInFlightRef.current = true;
      try {
        const response = await fetch(`/api/ai/workflows/${encodeURIComponent(runId)}`, { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const snapshot = unwrap<AiWorkflowRunEnvelope>(await response.json());
        const snapshotEvents = snapshot.events || [];
        for (const event of snapshotEvents) append(event, { fromPolling: true });
        const snapshotTerminal = runStatusIsTerminal(snapshot);
        if (snapshotTerminal) terminalRef.current = true;
        if (snapshotEvents.length) {
          lastMessageAtRef.current = Date.now();
          const lastSnapshotEvent = snapshotEvents[snapshotEvents.length - 1];
          if (lastSnapshotEvent?.id) lastEventIdRef.current = String(lastSnapshotEvent.id);
        }
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
      } finally {
        pollingInFlightRef.current = false;
      }
    };

    const append = (event: AiWorkflowEvent, options?: { fromPolling?: boolean }) => {
      if (closed) return;
      lastMessageAtRef.current = Date.now();
      if (event.id) lastEventIdRef.current = String(event.id);
      const eventType = String(event.event_type || "");
      if (eventType === "workflow.keepalive") {
        connectedRef.current = options?.fromPolling ? connectedRef.current : true;
        setState((current) => ({ ...current, connected: options?.fromPolling ? current.connected : true, error: current.terminal ? current.error : null }));
        return;
      }
      if (eventType === "workflow.cursor_not_found") {
        void recoverFromSnapshot({ force: true });
      }
      const terminalEvent = TERMINAL_EVENTS.has(eventType);
      terminalRef.current = terminalRef.current || terminalEvent;
      connectedRef.current = options?.fromPolling ? connectedRef.current : true;
      setState((current) => {
        const key = eventKey(event, current.events.length);
        const exists = current.events.some((item, index) => eventKey(item, index) === key);
        const events = exists ? current.events : orderEvents([...current.events, event]);
        const nextTerminal = current.terminal || terminalEvent;
        const lastOrderedEvent = events[events.length - 1] || event;
        return {
          ...current,
          connected: options?.fromPolling ? current.connected : true,
          terminal: nextTerminal,
          error: eventType === "workflow.failed" ? String(event.message || "Workflow fallo") : eventType === "workflow.stream_error" ? String(event.message || "Error temporal de stream; recuperando por polling.") : nextTerminal ? null : current.error,
          events,
          lastEvent: lastOrderedEvent,
        };
      });
      if (terminalEvent && !options?.fromPolling && !finalSnapshotFetchedRef.current) {
        // Fetch exactly one final server snapshot after terminal SSE events so
        // stale event-only payloads cannot hide readiness, confirmations, or bot_id.
        finalSnapshotFetchedRef.current = true;
        queueMicrotask(() => void recoverFromSnapshot({ force: true, allowTerminal: true }));
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
    source.addEventListener("workflow.stream_error", (message) => append(parseEvent((message as MessageEvent).data)));
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
      if (terminalRef.current) return;
      const idleForMs = Date.now() - (lastMessageAtRef.current || 0);
      void recoverFromSnapshot({ force: idleForMs > 3500 || !lastEventIdRef.current });
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
