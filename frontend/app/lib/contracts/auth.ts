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

export type SessionOrganization = {
  id: string;
  name: string;
  vertical?: string;
  subvertical?: string;
  timezone?: string;
  status?: string;
};

export type SessionUser = {
  id: string;
  email: string;
  full_name?: string;
  global_role?: string;
  organizations: SessionOrganization[];
};

export function normalizeOrganization(raw: unknown): SessionOrganization {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "organization_name"], "Organización"),
    vertical: stringOrNull(record.vertical) ?? undefined,
    subvertical: (() => { const settings = asRecord(record.settings_json); return stringOrNull(record.subvertical) ?? stringOrNull(settings.subvertical) ?? stringOrNull(settings.active_subvertical) ?? undefined; })(),
    timezone: stringOrNull(record.timezone) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
  };
}

export function normalizeSessionUser(raw: unknown): SessionUser {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    id: stringValue(record.id),
    email: stringValue(record.email),
    full_name: stringOrNull(record.full_name) ?? undefined,
    global_role: stringOrNull(record.global_role) ?? undefined,
    organizations: asArray(record.organizations).map(normalizeOrganization).filter((item) => Boolean(item.id)),
  };
}

export type SecurityPolicyContract = {
  organization_id: string | null;
  require_mfa: boolean;
  require_sso: boolean;
  session_ttl_minutes: number;
  webhook_signature_required: boolean;
  strict_idempotency: boolean;
  ip_allowlist: string[];
  allowed_origins: string[];
};

export function normalizeSecurityPolicy(raw: unknown): SecurityPolicyContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    organization_id: stringOrNull(record.organization_id),
    require_mfa: booleanValue(record.require_mfa),
    require_sso: booleanValue(record.require_sso),
    session_ttl_minutes: numberValue(record.session_ttl_minutes, 0),
    webhook_signature_required: booleanValue(record.webhook_signature_required),
    strict_idempotency: booleanValue(record.strict_idempotency),
    ip_allowlist: stringList(record.ip_allowlist),
    allowed_origins: stringList(record.allowed_origins),
  };
}

export type RateLimitPolicyContract = {
  id: string;
  organization_id?: string;
  bot_id?: string | null;
  scope?: string;
  kind?: string;
  window_seconds: number;
  window?: number;
  max_requests: number;
  limit?: number;
  is_active: boolean;
};

export function normalizeRateLimitPolicy(raw: unknown): RateLimitPolicyContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    bot_id: stringOrNull(record.bot_id),
    scope: stringOrNull(record.scope) ?? undefined,
    kind: stringOrNull(record.kind ?? record.scope) ?? undefined,
    window_seconds: numberValue(record.window_seconds ?? record.window),
    window: numberValue(record.window ?? record.window_seconds),
    max_requests: numberValue(record.max_requests ?? record.limit),
    limit: numberValue(record.limit ?? record.max_requests),
    is_active: booleanValue(record.is_active, true),
  };
}

export type SSOProviderContract = {
  id: string;
  organization_id?: string;
  name?: string;
  provider?: string;
  status?: string;
  health_status?: string;
  issuer?: string;
  client_id?: string;
  scopes: string[];
  expires_at?: string | null;
  updated_at?: string | null;
};

export function normalizeSSOProvider(raw: unknown): SSOProviderContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    name: stringOrNull(record.name ?? record.provider) ?? undefined,
    provider: stringOrNull(record.provider) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    health_status: stringOrNull(record.health_status ?? record.status) ?? undefined,
    issuer: stringOrNull(record.issuer) ?? undefined,
    client_id: stringOrNull(record.client_id) ?? undefined,
    scopes: stringList(record.scopes),
    expires_at: stringOrNull(record.expires_at ?? record.credential_expires_at),
    updated_at: pickTimestamp(record, "updated_at", "created_at"),
  };
}
