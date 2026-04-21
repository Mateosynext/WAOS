import type { BotContract, Summary } from "./bots";
import { normalizeBot } from "./bots";
import {
  asArray,
  asRecord,
  booleanOrNull,
  booleanValue,
  JsonMap,
  nullableNumber,
  numberOrNull,
  numberValue,
  pickString,
  pickTimestamp,
  stringList,
  stringOrNull,
  stringValue,
  unwrapApiEnvelope,
} from "./shared";

export type DashboardContract = {
  summary: Summary;
  bots: BotContract[];
};

export function normalizeDashboard(raw: unknown): DashboardContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  const summary = asRecord(record.summary);
  return {
    summary: {
      active_conversations: numberValue(summary.active_conversations),
      new_leads: numberValue(summary.new_leads),
      hot_leads: numberValue(summary.hot_leads),
      appointments_scheduled: numberValue(summary.appointments_scheduled),
      human_handoffs: numberValue(summary.human_handoffs),
      messages_sent: numberValue(summary.messages_sent),
      bots_with_error: numberValue(summary.bots_with_error),
      bots_paused: numberValue(summary.bots_paused),
      avg_response_time_seconds: nullableNumber(summary.avg_response_time_seconds),
    },
    bots: asArray(record.bots).map(normalizeBot).filter((item) => Boolean(item.id)),
  };
}

export type QueueCount = { kind: string; type: string; status: string; count: number };
export type QueueOverviewContract = { automation_jobs: QueueCount[]; outbox: QueueCount[]; callbacks: QueueCount[]; integration_sync: QueueCount[] };

export function normalizeCountRow(raw: unknown, fallbackKind: string): QueueCount {
  const record = asRecord(raw);
  const status = pickString(record, ["status", "kind", "type"], fallbackKind);
  const kind = pickString(record, ["kind", "type"], status || fallbackKind);
  return { kind, type: kind, status, count: numberValue(record.count) };
}

export function normalizeQueueOverview(raw: unknown): QueueOverviewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    automation_jobs: asArray(record.automation_jobs).map((item) => normalizeCountRow(item, "automation_jobs")),
    outbox: asArray(record.outbox).map((item) => normalizeCountRow(item, "outbox")),
    callbacks: asArray(record.callbacks).map((item) => normalizeCountRow(item, "callbacks")),
    integration_sync: asArray(record.integration_sync).map((item) => normalizeCountRow(item, "integration_sync")),
  };
}

export type ObservabilityContract = {
  totals: JsonMap;
  recent_failures: JsonMap[];
  recent_logs: JsonMap[];
};

export function normalizeObservability(raw: unknown): ObservabilityContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    totals: asRecord(record.totals),
    recent_failures: asArray(record.recent_failures).map((item) => asRecord(item)),
    recent_logs: asArray(record.recent_logs).map((item) => asRecord(item)),
  };
}

export type BusinessHubOverviewContract = {
  summary: JsonMap;
  top_products: JsonMap[];
  attention: JsonMap[];
};

export function normalizeBusinessHubOverview(raw: unknown): BusinessHubOverviewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    summary: asRecord(record.summary),
    top_products: asArray(record.top_products).map((item) => asRecord(item)),
    attention: asArray(record.attention).map((item) => asRecord(item)),
  };
}

export type AnalyticsDailyContract = {
  day: string;
  metrics: Record<string, unknown>;
  window: JsonMap;
};

export function normalizeAnalyticsDaily(raw: unknown): AnalyticsDailyContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  const metrics = asRecord(record.metrics);
  if (!Object.keys(metrics).length) {
    const fallbackMetrics = {
      ...asRecord(record),
      messages: numberValue(record.messages ?? record.inbound_messages, 0) + numberValue(record.outbound_messages, 0),
      conversations: numberValue(record.conversations ?? record.runs, 0),
    };
    return {
      day: stringValue(record.day, "-"),
      metrics: fallbackMetrics,
      window: asRecord(record.window),
    };
  }
  const enrichedMetrics = {
    ...metrics,
    messages: numberValue(metrics.messages ?? metrics.inbound_messages, 0) + numberValue(metrics.outbound_messages, 0),
    conversations: numberValue(metrics.conversations ?? metrics.runs, 0),
  };
  return {
    day: stringValue(record.day || metrics.day, "-"),
    metrics: enrichedMetrics,
    window: asRecord(record.window ?? metrics.window),
  };
}


export type AuditLogContract = {
  id: string;
  kind?: string;
  event?: string;
  message?: string;
  summary?: string;
  payload: JsonMap;
  details: JsonMap;
  created_at?: string | null;
  updated_at?: string | null;
  timestamp?: string | null;
};

export function normalizeAuditLog(raw: unknown): AuditLogContract {
  const record = asRecord(raw);
  const payload = asRecord(record.payload);
  const details = asRecord(record.details);
  const message = stringOrNull(record.message ?? record.summary ?? details.message ?? payload.message) ?? undefined;
  return {
    id: stringValue(record.id || record.trace_id || record.execution_id || message || "log"),
    kind: stringOrNull(record.kind ?? record.event ?? record.level) ?? undefined,
    event: stringOrNull(record.event ?? record.kind) ?? undefined,
    message,
    summary: stringOrNull(record.summary ?? message) ?? undefined,
    payload,
    details,
    created_at: pickTimestamp(record, "created_at") ?? null,
    updated_at: pickTimestamp(record, "updated_at", "created_at") ?? null,
    timestamp: pickTimestamp(record, "timestamp", "created_at", "updated_at") ?? null,
  };
}

export type RecommendationContract = {
  id: string;
  contact_name?: string;
  reason?: string;
  next_step?: string;
};

export function normalizeRecommendation(raw: unknown): RecommendationContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id || record.contact_name || record.reason),
    contact_name: stringOrNull(record.contact_name ?? record.name) ?? undefined,
    reason: stringOrNull(record.reason) ?? undefined,
    next_step: stringOrNull(record.next_step) ?? undefined,
  };
}
