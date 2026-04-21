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

export type FeedbackItemContract = {
  id: string;
  kind?: string;
  comment?: string;
  message?: string;
  detail?: string;
  created_at?: string | null;
};

export function normalizeFeedbackItem(raw: unknown): FeedbackItemContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id || record.comment || record.message),
    kind: stringOrNull(record.kind) ?? undefined,
    comment: stringOrNull(record.comment) ?? undefined,
    message: stringOrNull(record.message) ?? undefined,
    detail: stringOrNull(record.detail ?? record.comment ?? record.message) ?? undefined,
    created_at: pickTimestamp(record, "created_at") ?? null,
  };
}

export type PortalRequestContract = {
  id: string;
  kind?: string;
  detail?: string;
  message?: string;
  status?: string;
  created_at?: string | null;
};

export function normalizePortalRequest(raw: unknown): PortalRequestContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id || record.kind || record.message),
    kind: stringOrNull(record.kind) ?? undefined,
    detail: stringOrNull(record.detail ?? record.message) ?? undefined,
    message: stringOrNull(record.message) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    created_at: pickTimestamp(record, "created_at") ?? null,
  };
}


export type ClientOperationsBotContract = {
  operational_state?: string;
  current_state?: string;
  status?: string;
  temp_unavailability_message?: string;
};

export function normalizeClientOperationsBot(raw: unknown): ClientOperationsBotContract {
  const record = asRecord(raw);
  return {
    operational_state: stringOrNull(record.operational_state) ?? undefined,
    current_state: stringOrNull(record.current_state ?? record.operational_state ?? record.state) ?? undefined,
    status: stringOrNull(record.status ?? record.current_state ?? record.operational_state) ?? undefined,
    temp_unavailability_message: stringOrNull(record.temp_unavailability_message ?? record.message) ?? undefined,
  };
}

export type ClientOperationsCountsContract = {
  authorized_numbers: number;
  recent_commands: number;
  alerts_open: number;
};

export function normalizeClientOperationsCounts(raw: unknown): ClientOperationsCountsContract {
  const record = asRecord(raw);
  return {
    authorized_numbers: numberValue(record.authorized_numbers),
    recent_commands: numberValue(record.recent_commands),
    alerts_open: numberValue(record.alerts_open),
  };
}

export type AuthorizedOperationalNumberContract = {
  id: string;
  phone_e164?: string;
  role?: string;
  status?: string;
  scope_summary?: string;
  allowed_intents: string[];
  scope_branches: string[];
  scope_resource_names: string[];
  scope_service_names: string[];
};

export function normalizeAuthorizedOperationalNumber(raw: unknown): AuthorizedOperationalNumberContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id || record.phone_e164 || record.phone),
    phone_e164: stringOrNull(record.phone_e164 ?? record.phone) ?? undefined,
    role: stringOrNull(record.role) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    scope_summary: stringOrNull(record.scope_summary) ?? undefined,
    allowed_intents: stringList(record.allowed_intents),
    scope_branches: stringList(record.scope_branches),
    scope_resource_names: stringList(record.scope_resource_names),
    scope_service_names: stringList(record.scope_service_names),
  };
}

function summarizeOperationalResult(raw: unknown) {
  const record = asRecord(raw);
  const preview = asRecord(record.preview);
  const impact = asRecord(preview.impact);
  return stringOrNull(record.reply_text)
    ?? stringOrNull(record.detail)
    ?? (numberOrNull(impact.appointments_affected) !== null ? `${numberValue(impact.appointments_affected)} citas afectadas` : null)
    ?? null;
}

export type OperationalCommandContract = {
  id: string;
  detected_intent?: string;
  status?: string;
  risk_level?: string;
  requires_confirmation: boolean;
  confirmation_code?: string;
  undoable_until?: string | null;
  created_at?: string | null;
  result: JsonMap;
  result_summary?: string;
};

export function normalizeOperationalCommand(raw: unknown): OperationalCommandContract {
  const record = asRecord(raw);
  const result = asRecord(record.result);
  return {
    id: stringValue(record.id || record.detected_intent || record.created_at),
    detected_intent: stringOrNull(record.detected_intent ?? record.intent) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    risk_level: stringOrNull(record.risk_level) ?? undefined,
    requires_confirmation: booleanValue(record.requires_confirmation),
    confirmation_code: stringOrNull(record.confirmation_code) ?? undefined,
    undoable_until: pickTimestamp(record, 'undoable_until'),
    created_at: pickTimestamp(record, 'created_at', 'updated_at'),
    result,
    result_summary: summarizeOperationalResult(result) ?? undefined,
  };
}

export type ClientOperationsSummaryContract = {
  bot: ClientOperationsBotContract;
  counts: ClientOperationsCountsContract;
  recent_commands: OperationalCommandContract[];
  authorized_numbers: AuthorizedOperationalNumberContract[];
  scheduled_actions: JsonMap[];
  upcoming_appointments: JsonMap[];
};

export function normalizeClientOperationsSummary(raw: unknown): ClientOperationsSummaryContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    bot: normalizeClientOperationsBot(record.bot),
    counts: normalizeClientOperationsCounts(record.counts),
    recent_commands: asArray(record.recent_commands).map(normalizeOperationalCommand),
    authorized_numbers: asArray(record.authorized_numbers).map(normalizeAuthorizedOperationalNumber),
    scheduled_actions: asArray(record.scheduled_actions).map((item) => asRecord(item)),
    upcoming_appointments: asArray(record.upcoming_appointments).map((item) => asRecord(item)),
  };
}

export type ClientOperationsMetricsSummaryContract = {
  total: number;
  high_risk: number;
  alerts_open: number;
};

export type ClientOperationsMetricsContract = {
  summary: ClientOperationsMetricsSummaryContract;
  intents: JsonMap[];
  statuses: JsonMap[];
};

export function normalizeClientOperationsMetrics(raw: unknown): ClientOperationsMetricsContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  const summary = asRecord(record.summary);
  return {
    summary: {
      total: numberValue(summary.total),
      high_risk: numberValue(summary.high_risk),
      alerts_open: numberValue(summary.alerts_open),
    },
    intents: asArray(record.intents).map((item) => asRecord(item)),
    statuses: asArray(record.statuses).map((item) => asRecord(item)),
  };
}

export type ClientOperationsAvailabilitySummaryContract = {
  appointments: number;
  blocked_ranges: number;
  open_exceptions: number;
};

export type ClientOperationsAvailabilityAppointmentContract = {
  id: string;
  status?: string;
  scheduled_for?: string | null;
};

export type ClientOperationsAvailabilityContract = {
  summary: ClientOperationsAvailabilitySummaryContract;
  appointments: ClientOperationsAvailabilityAppointmentContract[];
  overrides: JsonMap[];
};

export function normalizeClientOperationsAvailability(raw: unknown): ClientOperationsAvailabilityContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  const summary = asRecord(record.summary);
  return {
    summary: {
      appointments: numberValue(summary.appointments),
      blocked_ranges: numberValue(summary.blocked_ranges),
      open_exceptions: numberValue(summary.open_exceptions),
    },
    appointments: asArray(record.appointments).map((item) => {
      const appointment = asRecord(item);
      return {
        id: stringValue(appointment.id),
        status: stringOrNull(appointment.status) ?? undefined,
        scheduled_for: pickTimestamp(appointment, 'scheduled_for', 'starts_at', 'start_at'),
      };
    }),
    overrides: asArray(record.overrides).map((item) => asRecord(item)),
  };
}

export type ClientOperationsAlertContract = {
  id: string;
  severity?: string;
  alert_type?: string;
  status?: string;
  title?: string;
  body?: string;
};

export function normalizeClientOperationsAlert(raw: unknown): ClientOperationsAlertContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id || record.alert_type || record.title),
    severity: stringOrNull(record.severity) ?? undefined,
    alert_type: stringOrNull(record.alert_type ?? record.type) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    title: stringOrNull(record.title) ?? undefined,
    body: stringOrNull(record.body ?? record.message ?? record.detail) ?? undefined,
  };
}
