import type { QueueCount } from "./analytics";
import { normalizeCountRow } from "./analytics";
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

export type IntegrationContract = {
  id: string;
  organization_id: string;
  bot_id?: string | null;
  related_bot_id?: string | null;
  name: string;
  provider?: string;
  integration_type?: string;
  status?: string;
  health_status?: string;
  credential_status?: string;
  credential_expires_at?: string | null;
  expires_at?: string | null;
  last_error?: string | null;
  last_test_at?: string | null;
  last_provider_event_at?: string | null;
  last_provider_status_code?: number | null;
  auto_sync_enabled?: boolean;
  sync_frequency_minutes?: number | null;
  next_sync_at?: string | null;
  last_success_at?: string | null;
  updated_at?: string | null;
  config: Record<string, unknown>;
  result?: Record<string, unknown>;
};

export function normalizeIntegration(raw: unknown): IntegrationContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    id: stringValue(record.id),
    organization_id: stringValue(record.organization_id),
    bot_id: stringOrNull(record.bot_id),
    related_bot_id: stringOrNull(record.related_bot_id),
    name: pickString(record, ["name", "display_name"], "Integración"),
    provider: stringOrNull(record.provider) ?? undefined,
    integration_type: stringOrNull(record.integration_type) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    health_status: stringOrNull(record.health_status ?? record.status) ?? undefined,
    credential_status: stringOrNull(record.credential_status) ?? undefined,
    credential_expires_at: stringOrNull(record.credential_expires_at),
    expires_at: stringOrNull(record.expires_at ?? record.credential_expires_at),
    last_error: stringOrNull(record.last_error),
    last_test_at: stringOrNull(record.last_test_at),
    last_provider_event_at: stringOrNull(record.last_provider_event_at),
    last_provider_status_code: nullableNumber(record.last_provider_status_code),
    auto_sync_enabled: booleanValue(record.auto_sync_enabled ?? asRecord(record.config).auto_sync_enabled),
    sync_frequency_minutes: nullableNumber(record.sync_frequency_minutes ?? asRecord(record.config).sync_frequency_minutes),
    next_sync_at: stringOrNull(record.next_sync_at),
    last_success_at: stringOrNull(record.last_success_at),
    updated_at: pickTimestamp(record, "updated_at", "created_at"),
    config: asRecord(record.config),
    result: Object.keys(asRecord(record.result)).length ? asRecord(record.result) : undefined,
  };
}

export type SchedulerOverviewContract = {
  counts: QueueCount[];
  due_now: number;
  next_job: JsonMap | null;
  stale_locks: number;
  integration_due_now: number;
  next_integration: JsonMap | null;
  integration_retries: number;
};

export function normalizeSchedulerOverview(raw: unknown): SchedulerOverviewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    counts: asArray(record.counts).map((item) => normalizeCountRow(item, "scheduler")),
    due_now: numberValue(record.due_now),
    next_job: Object.keys(asRecord(record.next_job)).length ? asRecord(record.next_job) : null,
    stale_locks: numberValue(record.stale_locks),
    integration_due_now: numberValue(record.integration_due_now),
    next_integration: Object.keys(asRecord(record.next_integration)).length ? asRecord(record.next_integration) : null,
    integration_retries: numberValue(record.integration_retries),
  };
}

export type RuntimeCallbackContract = {
  id: string;
  kind: string;
  type: string;
  status?: string;
  health_status?: string;
  target?: string | null;
  updated_at?: string | null;
  last_run_at?: string | null;
  payload: Record<string, unknown>;
  response: Record<string, unknown>;
};

export function normalizeRuntimeCallback(raw: unknown): RuntimeCallbackContract {
  const record = asRecord(raw);
  const kind = pickString(record, ["kind", "callback_type", "type"], "callback");
  const updatedAt = pickTimestamp(record, "updated_at", "delivered_at", "created_at");
  return {
    id: stringValue(record.id),
    kind,
    type: kind,
    status: stringOrNull(record.status) ?? undefined,
    health_status: stringOrNull(record.health_status ?? record.status) ?? undefined,
    target: stringOrNull(record.target),
    updated_at: updatedAt,
    last_run_at: stringOrNull(record.last_run_at ?? updatedAt),
    payload: asRecord(record.payload),
    response: asRecord(record.response),
  };
}

export type DeadLetterItem = {
  id: string;
  kind: string;
  type: string;
  status: string;
  detail: string;
  error?: string | null;
  payload: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
  scheduled_for?: string | null;
};

export type DeadLettersContract = { jobs: DeadLetterItem[]; outbox: DeadLetterItem[] };

export function normalizeDeadLetter(raw: unknown, channel: string): DeadLetterItem {
  const record = asRecord(raw);
  const detail = pickString(record, ["detail", "kind", "type", "id"], channel);
  return {
    id: stringValue(record.id || detail),
    kind: channel,
    type: pickString(record, ["kind", "type"], channel),
    status: pickString(record, ["status"], "dead_letter"),
    detail,
    error: stringOrNull(record.last_error ?? record.error),
    payload: asRecord(record.payload),
    created_at: pickTimestamp(record, "created_at") ?? null,
    updated_at: pickTimestamp(record, "updated_at", "created_at") ?? null,
    scheduled_for: stringOrNull(record.scheduled_for),
  };
}

export function normalizeDeadLetters(raw: unknown): DeadLettersContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    jobs: asArray(record.jobs).map((item) => normalizeDeadLetter(item, "job")),
    outbox: asArray(record.outbox).map((item) => normalizeDeadLetter(item, "outbox")),
  };
}

export type IntegrationEventContract = {
  id: string;
  provider?: string | null;
  event_type?: string | null;
  status?: string | null;
  summary?: string | null;
  detail?: string | null;
  provider_status_code?: number | null;
  created_at?: string | null;
  error: JsonMap;
  response: JsonMap;
};

export function normalizeIntegrationEvent(raw: unknown): IntegrationEventContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    provider: stringOrNull(record.provider),
    event_type: stringOrNull(record.event_type ?? record.kind),
    status: stringOrNull(record.status),
    summary: stringOrNull(record.summary),
    detail: stringOrNull(record.detail ?? record.summary),
    provider_status_code: nullableNumber(record.provider_status_code),
    created_at: pickTimestamp(record, "created_at", "timestamp") ?? null,
    error: asRecord(record.error),
    response: asRecord(record.response),
  };
}

export type IntegrationObservabilityContract = {
  totals: JsonMap;
  latest_error: IntegrationEventContract | null;
  providers: JsonMap[];
  recent: IntegrationEventContract[];
};

export function normalizeIntegrationObservability(raw: unknown): IntegrationObservabilityContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    totals: asRecord(record.totals),
    latest_error: record.latest_error ? normalizeIntegrationEvent(record.latest_error) : null,
    providers: asArray(record.providers).map((item) => asRecord(item)),
    recent: asArray(record.recent).map(normalizeIntegrationEvent),
  };
}

export type SyncRunContract = {
  id: string;
  integration_id?: string | null;
  provider?: string | null;
  status?: string;
  summary: JsonMap;
  detail?: string;
  error: JsonMap;
  created_at?: string | null;
};

export function normalizeSyncRun(raw: unknown): SyncRunContract {
  const record = asRecord(raw);
  const summary = asRecord(record.summary);
  return {
    id: stringValue(record.id),
    integration_id: stringOrNull(record.integration_id),
    provider: stringOrNull(record.provider ?? summary.provider),
    status: stringOrNull(record.status) ?? undefined,
    summary,
    detail: stringOrNull(record.detail ?? summary.reason ?? summary.mode ?? summary.provider) ?? undefined,
    error: asRecord(record.error),
    created_at: pickTimestamp(record, "created_at", "started_at") ?? null,
  };
}

export type SecretContract = {
  id: string;
  organization_id?: string;
  bot_id?: string | null;
  scope?: string;
  key_name?: string;
  name?: string;
  updated_at?: string | null;
  last_rotated_at?: string | null;
  rotation_due?: boolean;
};

export function normalizeSecret(raw: unknown): SecretContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    bot_id: stringOrNull(record.bot_id),
    scope: stringOrNull(record.scope) ?? undefined,
    key_name: stringOrNull(record.key_name) ?? undefined,
    name: stringOrNull(record.name ?? record.key_name) ?? undefined,
    updated_at: pickTimestamp(record, "updated_at", "created_at") ?? null,
    last_rotated_at: pickTimestamp(record, "last_rotated_at", "updated_at", "created_at") ?? null,
    rotation_due: booleanValue(record.rotation_due),
  };
}

export type IntegrationCenterContract = {
  organization_id?: string;
  summary: Record<string, unknown>;
  integrations: IntegrationContract[];
  observability: Record<string, unknown>;
  recent_sync_runs: Record<string, unknown>[];
  failed_receipts: Record<string, unknown>[];
  retry_hotspots: Record<string, unknown>[];
  dependency_map: Record<string, unknown>[];
};

export function normalizeIntegrationCenter(raw: unknown): IntegrationCenterContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    summary: asRecord(record.summary),
    integrations: asArray(record.integrations).map(normalizeIntegration).filter((item) => Boolean(item.id)),
    observability: asRecord(record.observability),
    recent_sync_runs: asArray(record.recent_sync_runs).map((item) => asRecord(item)),
    failed_receipts: asArray(record.failed_receipts).map((item) => asRecord(item)),
    retry_hotspots: asArray(record.retry_hotspots).map((item) => asRecord(item)),
    dependency_map: asArray(record.dependency_map).map((item) => asRecord(item)),
  };
}
