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

export type ActivationSummaryContract = {
  organization_id?: string;
  bot_id?: string | null;
  tenant_mode?: string;
  vertical?: string | null;
  counts: Record<string, number>;
  progress: Record<string, number>;
  readiness_score?: number;
  blockers: Array<Record<string, unknown>>;
  checklist: Array<Record<string, unknown>>;
  next_step: Record<string, unknown>;
  guided_wizard?: Record<string, unknown> | null;
  first_value_at?: string | null;
  created_at?: string | null;
  feature_flags: Record<string, boolean>;
};

export function normalizeActivationSummary(raw: unknown): ActivationSummaryContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    bot_id: stringOrNull(record.bot_id),
    tenant_mode: stringOrNull(record.tenant_mode) ?? undefined,
    vertical: stringOrNull(record.vertical),
    counts: asRecord(record.counts) as Record<string, number>,
    progress: asRecord(record.progress) as Record<string, number>,
    readiness_score: nullableNumber(record.readiness_score) ?? undefined,
    blockers: asArray(record.blockers).map((item) => asRecord(item)),
    checklist: asArray(record.checklist).map((item) => asRecord(item)),
    next_step: asRecord(record.next_step),
    guided_wizard: Object.keys(asRecord(record.guided_wizard)).length ? asRecord(record.guided_wizard) : null,
    first_value_at: pickTimestamp(record, "first_value_at"),
    created_at: pickTimestamp(record, "created_at"),
    feature_flags: asRecord(record.feature_flags) as Record<string, boolean>,
  };
}

export type AppointmentContract = {
  id: string;
  contact_name?: string;
  service_name?: string;
  starts_at?: string | null;
  start_at?: string | null;
  scheduled_for?: string | null;
  status?: string;
  payment_status?: string | null;
  reconciliation_status?: string | null;
};

export function normalizeAppointment(raw: unknown): AppointmentContract {
  const record = asRecord(raw);
  const startsAt = pickTimestamp(record, "starts_at", "start_at", "scheduled_for");
  return {
    id: stringValue(record.id),
    contact_name: stringOrNull(record.contact_name ?? record.customer_name) ?? undefined,
    service_name: stringOrNull(record.service_name ?? record.service) ?? undefined,
    starts_at: startsAt,
    start_at: startsAt,
    scheduled_for: startsAt,
    status: stringOrNull(record.status) ?? undefined,
    payment_status: stringOrNull(record.payment_status),
    reconciliation_status: stringOrNull(record.reconciliation_status),
  };
}

export type AgendaOverviewContract = {
  summary: JsonMap;
  upcoming: AppointmentContract[];
};

export function normalizeAgendaOverview(raw: unknown): AgendaOverviewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    summary: asRecord(record.summary),
    upcoming: asArray(record.upcoming).map(normalizeAppointment),
  };
}
