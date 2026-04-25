"use client";
import { useEffect, useMemo, useRef, useState } from "react";

export type AiWorkflowEvent = {
  id?: string;
  event_type: string;
  message?: string;
  progress?: number;
  payload_json?: Record<string, unknown>;
  created_at?: string;
};

const EVENT_NAMES = [
  "workflow.started",
  "intent.normalized",
  "vertical.detected",
  "business_profile.generated",
  "wizard.created",
  "wizard.failed_partial",
  "wizard.step_saved",
  "vertical_pack.generated",
  "policy_pack.generated",
  "specialist_agents_config.generated",
  "knowledge_plan.generated",
  "whatsapp_pack.generated",
  "tool_plan.generated",
  "dry_run.started",
  "dry_run.completed",
  "autofix.started",
  "autofix.round_completed",
  "simulation.started",
  "simulation.scenario_completed",
  "simulation.completed",
  "go_live_readiness.completed",
  "human_confirmation.required",
  "human_confirmation.updated",
  "apply.prepared",
  "apply.completed",
  "canary.prepared",
  "workflow.paused_cost_limit",
  "workflow.cancelled",
  "workflow.completed",
  "workflow.completed_partial",
  "workflow.failed",
  "workflow.keepalive",
];

const TERMINAL = new Set(["workflow.completed", "workflow.completed_partial", "workflow.failed", "workflow.cancelled", "workflow.paused_cost_limit"]);

export function useAiWorkflowStream(runId?: string | null) {
  const [events, setEvents] = useState<AiWorkflowEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) return;
    sourceRef.current?.close();
    setEvents([]);
    setError("");
    let closedByTerminal = false;
    const source = new EventSource(`/api/ai/workflows/${encodeURIComponent(runId)}/events`);
    sourceRef.current = source;
    source.onopen = () => setConnected(true);
    source.onerror = () => {
      setConnected(false);
      if (!closedByTerminal) setError("No se pudo mantener el stream SSE real; usa refresh para recuperar historial.");
    };
    const push = (raw: MessageEvent) => {
      try {
        const event = JSON.parse(raw.data) as AiWorkflowEvent;
        if (!event?.event_type || event.event_type === "workflow.keepalive") return;
        setEvents((current) => {
          if (event.id && current.some((item) => item.id === event.id)) return current;
          return [...current, event];
        });
        if (TERMINAL.has(event.event_type)) {
          closedByTerminal = true;
          setConnected(false);
          source.close();
        }
      } catch {
        // Ignore malformed SSE frames. Backend should not emit them, but UI must not crash.
      }
    };
    EVENT_NAMES.forEach((name) => source.addEventListener(name, push));
    source.onmessage = push;
    return () => {
      closedByTerminal = true;
      source.close();
    };
  }, [runId]);

  const terminalEvent = useMemo(() => [...events].reverse().find((event) => TERMINAL.has(event.event_type)) || null, [events]);
  return { events, connected, error, terminalEvent };
}
