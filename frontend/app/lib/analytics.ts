"use client";

import { getClientApiBase } from "./env";

const STORAGE_KEY = "waos_frontend_analytics";
const MAX_EVENTS = 120;
export type AnalyticsEvent = { type: "page_view" | "ui_click" | "form_error"; path: string; label?: string | null; ts: string };

function readStored(): AnalyticsEvent[] { try { const raw = window.localStorage.getItem(STORAGE_KEY); return raw ? JSON.parse(raw) : []; } catch { return []; } }
function persist(event: AnalyticsEvent) { try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...readStored(), event].slice(-MAX_EVENTS))); } catch {} }
function post(event: AnalyticsEvent) {
  const base = getClientApiBase();
  if (!base) return;
  const payload = JSON.stringify({ source: "frontend-analytics", kind: event.type, path: event.path, label: event.label || null, ts: event.ts });
  try {
    if (navigator.sendBeacon) {
      navigator.sendBeacon(`${base}/api/v1/observability/frontend-errors`, new Blob([payload], { type: "application/json" }));
      return;
    }
    fetch(`${base}/api/v1/observability/frontend-errors`, { method: "POST", headers: { "Content-Type": "application/json" }, body: payload, keepalive: true }).catch(() => null);
  } catch {}
}
export function trackFrontendEvent(type: AnalyticsEvent["type"], path: string, label?: string | null) {
  if (typeof window === "undefined") return;
  const event = { type, path, label: label || null, ts: new Date().toISOString() } as AnalyticsEvent;
  persist(event); post(event);
}
