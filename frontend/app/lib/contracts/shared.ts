export type JsonMap = Record<string, unknown>;

export type ApiEnvelope<T = unknown> = {
  ok?: boolean;
  data?: T;
  error?: { code?: string; message?: string; details?: unknown; retryable?: boolean };
  meta?: Record<string, unknown>;
  request_id?: string | null;
  correlation_id?: string | null;
};

export function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

export function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function stringOrNull(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  }
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return null;
}

export function stringValue(value: unknown, fallback = ""): string {
  return stringOrNull(value) ?? fallback;
}

export function numberValue(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

export function booleanValue(value: unknown, fallback = false): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["1", "true", "yes", "enabled", "active", "on"].includes(normalized)) return true;
    if (["0", "false", "no", "disabled", "inactive", "off"].includes(normalized)) return false;
  }
  return fallback;
}

export function nullableNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  return numberValue(value, 0);
}

export function numberOrNull(value: unknown): number | null {
  return nullableNumber(value);
}

export function booleanOrNull(value: unknown): boolean | null {
  if (value === null || value === undefined || value === "") return null;
  return booleanValue(value);
}

export function stringList(value: unknown): string[] {
  return asArray(value)
    .map((item) => stringOrNull(item))
    .filter((item): item is string => Boolean(item));
}

export function pickTimestamp(record: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const value = stringOrNull(record[key]);
    if (value) return value;
  }
  return null;
}

export function pickString(record: Record<string, unknown>, keys: string[], fallback = "") {
  for (const key of keys) {
    const value = stringOrNull(record[key]);
    if (value) return value;
  }
  return fallback;
}

export function unwrapApiEnvelope<T = unknown>(value: T | ApiEnvelope<T>): T | unknown {
  const record = asRecord(value);
  if ("data" in record && ("ok" in record || "meta" in record)) return record.data;
  return value;
}

export function normalizeCollection<T>(raw: unknown, normalizeItem: (value: unknown) => T): T[] {
  return asArray(unwrapApiEnvelope(raw)).map(normalizeItem);
}

export function normalizeRecord<T>(raw: unknown, normalizeItem: (value: unknown) => T): T {
  return normalizeItem(unwrapApiEnvelope(raw));
}
